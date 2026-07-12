# FAST-LIO 转弯后不可恢复漂移第二阶段分析与解决报告

> 日期：2026-07-12  
> 项目：`D:/g1_botbrain_greeter`  
> 范围：FAST-LIO 建图状态估计、IMU 输入链路、ikd-tree 地图写入、Open3D 导航 ICP  
> 说明：本阶段代码只在本地工作区修改，**未 commit、未 push**。本机没有 ROS 2、colcon、Docker 和 G1 运行环境，因此结论已做静态审查，但必须在 G1 真机重新编译和验证。

## 1. 本阶段解决的不是 Foxglove 显示问题

上一阶段已经解决了“Foxglove 中点云话题使用 body 坐标，导致点云看起来跟机器人一起旋转”的显示问题。判断真实地图是否稳定时，应继续使用：

- Fixed Frame：`camera_init`
- Display/Follow Frame：`camera_init`
- 世界点云：`/cloud_registered_1`
- `/cloud_registered_body_1` 是 body-frame 点云，跟随机器人是其正常定义

本阶段处理的是另一类真实故障：机器人转弯后短暂停稳，再次移动时 FAST-LIO 位姿和世界点云突然发生大幅漂移；错误点一旦写进地图，后续匹配会被错误地图继续拉偏，最终只能重启服务。导航阶段则表现为快速转弯或累计误差后 Open3D ICP 突然把 `map -> odom` 拉到错误位置。

## 2. 根因定位

### 2.1 FAST-LIO 的失控链路

原实现存在下面的正反馈链：

1. FAST-LIO 的 IMU subscription depth 只有 10。
2. MID360 IMU 通常是高频数据；10 条消息只能覆盖很短时间。FAST-LIO 同一个执行线程还要做点云预处理、IMU 去畸变、scan-to-map、EKF 更新、ikd-tree 写入、发布和 PCD 累积。转弯时计算稍慢，关键角速度样本就更容易在 DDS 队列中丢失。
3. 原默认链路为 `/livox/imu -> imu_flip.py -> /livox/imu_corrected -> FAST-LIO`，额外增加 Python 调度、一次订阅/发布、序列化和第二段 DDS 队列。
4. IMU 缺样或间隔过大时，转弯期间的运动补偿和 EKF 预测质量下降。
5. 原代码对 LiDAR 更新结果没有质量门：无论有效匹配点是否太少、残差是否过大、LiDAR 对 IMU 预测的修正是否突然跳变，都直接保留更新后的 EKF 状态。
6. 随后无条件调用 `map_incremental()`，把基于错误位姿转换的点写入 ikd-tree；开启 PCD 保存时也会写入 `pcl_wait_save`。
7. 下一帧 scan-to-map 开始匹配已经被污染的地图，产生更错误的状态和更多错误地图点，形成不可逆的自强化发散。

这解释了用户观察到的现象：转弯后可能先稳定一段时间，但再次移动后突然飘飞；一旦错误点进入地图，单纯停住很难恢复，只能重启服务。

### 2.2 Open3D 导航定位问题

`open3d_loc/src/global_localization.cpp` 中还存在独立问题：

1. `loc_frequence` 名字表示频率，但旧实现把数值当成“多少秒执行一次”。配置 4.0 实际可能接近每 4 秒才做一次 ICP，而不是 4 Hz。
2. 点云队列旧逻辑先聚合历史帧，再 push 当前帧，ICP 经常看不到最新帧；10 帧窗口又进一步增加转弯后的时间拖影。
3. 旧跳变门限只在平移大于 50 m 时拒绝，且没有旋转门限。对室内机器人而言，1～10 m 的错误跳变已经足以彻底破坏定位，50 m 门限几乎等于没有保护。
4. `MultiThreadedExecutor(4)` 下，点云回调、里程计回调、初始位姿回调和定位线程同时读写多组 Eigen 位姿矩阵，原代码没有完整同步，存在数据竞争和读到半更新矩阵的风险。
5. 原析构退出线程的同步不完整，工作区中间版本还曾出现删除 `lock_exit_` 后析构继续引用它的编译风险。

## 3. 已实施的 FAST-LIO 修复

### 3.1 移除默认 Python IMU relay

修改：

- `botbrain_ws/src/g1_pkg/launch/fast_lio.launch.py`
- `botbrain_ws/src/g1_pkg/launch/livox_MID360.launch.py`
- `botbrain_ws/src/fast_lio/config/mid360.yaml`
- `botbrain_ws/src/fast_lio/src/laserMapping.cpp`

新的默认链路：

`/livox/imu -> FAST-LIO C++ imu_cbk()`

在 C++ 回调中，当 `common.imu_flip_yz: true` 时，对 FAST-LIO 实际使用的数据执行倒装 MID360 的 `R_x(pi)` 修正：

- 角速度 X 不变，Y/Z 取反
- 线加速度 X 不变，Y/Z 取反
- 不修改 orientation 字段，避免对未使用或来源不确定的姿态做重复变换

`imu_flip.py` 文件没有删除，仍可用于诊断或回退，但默认 launch 不再启动它。

**绝对禁止同时启动 `imu_flip.py` 和设置 `imu_flip_yz: true`。** 两次 Y/Z 翻转会互相抵消，重新变成错误轴向。

### 3.2 增大输入 QoS 队列

新增参数：

- `common.imu_queue_depth: 2000`
- `common.lidar_queue_depth: 100`

MID360 CustomMsg 与 IMU subscription 使用 Reliable KeepLast。目的不是用更大的历史数据掩盖故障，而是在单线程 scan-to-map 计算期间保住转弯所需的连续 IMU 样本，并通过后述 timing 日志判断系统是否实际积压。

标准 `PointCloud2` 路径仍保留原 `SensorDataQoS`，避免改变非 Livox 数据源的兼容性。

### 3.3 增加时序诊断

每约 2 秒输出一次：

`[FAST_LIO_TIMING]`

字段包括：

- 当前 LiDAR scan duration
- 此 scan 使用的 IMU 数量
- 第一条/最后一条 IMU 时间戳
- 最大 IMU gap
- LiDAR 结束时间与最后 IMU 的差
- 当前 IMU/LiDAR buffer 大小

当前警告条件：

- `imu_count < 5`
- `max_imu_gap > 0.02 s`
- scan duration 不在约 `0.05～0.15 s`

同时把错误日志 `lidar loop back, clear buffer` 修正为 `IMU timestamp loop back, clear buffer`，避免把 IMU 时间戳回退误判成 LiDAR 回退。

### 3.4 增加坏 LiDAR 更新 guard 与 EKF 回滚

在每次 `kf.update_iterated_dyn_share_modified()` 前保存：

- IMU 预测状态 `predicted_state`
- IMU 预测协方差 `predicted_cov`

更新后读取：

- `updated_state`
- `updated_cov`
- `effct_feat_num`
- `feats_down_size`
- `res_mean_last`
- LiDAR 更新相对 IMU 预测的平移修正量
- LiDAR 更新相对 IMU 预测的旋转修正量

新增参数：

| 参数 | 当前值 | 含义 |
|---|---:|---|
| `mapping.guard_enable` | true | 启用质量门 |
| `guard_min_effective_points` | 50 | 最少有效平面匹配点 |
| `guard_min_effective_ratio` | 0.05 | 有效点/降采样点最小比例 |
| `guard_max_residual` | 0.30 m | 平均点到平面残差上限 |
| `guard_max_translation_correction` | 0.50 m | 单帧 LiDAR 相对 IMU 预测的最大平移修正 |
| `guard_max_rotation_correction_deg` | 20° | 单帧最大旋转修正 |

无论 `guard_enable` 是否关闭，只要状态或协方差出现 NaN/Inf，都无条件拒绝。

拒绝时执行：

1. `kf.change_x(predicted_state)`
2. `kf.change_P(predicted_cov)`
3. 恢复全局发布状态为 IMU 预测值
4. 发布预测 odometry、world cloud 和 body cloud，尽量保持下游数据连续
5. **立即 return，不调用 `map_incremental()`**
6. 因此被拒帧不会写入 ikd-tree，也不会通过 `map_incremental()` 写入 `pcl_wait_save`
7. 不发布 rejected frame 的 effect cloud
8. 输出 `[FAST_LIO_GUARD] rejected=...`

后续帧质量恢复并被接受时输出：

`[FAST_LIO_GUARD] recovered after N rejected frame(s)`

这项修改的核心不是保证每一帧都能定位，而是把“单帧坏匹配”从“不可恢复的地图污染”降级为“这一帧只使用 IMU 预测、等待下一帧恢复”。

## 4. 已实施的 Open3D ICP 修复

修改：

- `botbrain_ws/src/open3d_loc/src/global_localization.cpp`
- `botbrain_ws/src/g1_pkg/launch/localization_3d.launch.py`
- `botbrain_ws/src/open3d_loc/launch/open3d_loc_g1.launch.py`

主要修改：

1. `loc_frequence` 明确按 Hz 使用；4.0 表示约每 250 ms 尝试一次 ICP。
2. 使用 `steady_clock` 调度；单次 ICP 超时后重置下一调度点，避免 busy loop。
3. 点云回调先放入最新帧、再裁剪旧帧，并在同一互斥锁内生成聚合点云，确保 ICP 包含当前帧。
4. 队列由 10 帧缩短为 5 帧，降低转弯时陈旧点云拖影。
5. 新增最少 source/target 点数保护：100/1000。
6. 新增 ICP correction 跳变门：单次修正大于 1.0 m 或 15° 时拒绝，不覆盖当前 `map -> odom`。
7. 对 ICP 变换做 finite、旋转正交、det(R)、齐次底行检查。
8. 对来自 FAST-LIO 的 odometry 变换、初始位姿四元数和发布 TF 四元数做合法性检查与归一化。
9. 用 mutex 保护点云、时间戳和共享位姿矩阵；ICP 重计算期间使用锁内快照，不长时间持锁。
10. `loc_initialized`、`loc_fitness` 和退出标志改为 atomic。
11. 析构时设置退出标志并正确 join 定位线程。
12. 保存调试 scan 时只保存已通过 fitness 与跳变门的结果。

## 5. 参数调整：哪些是根因修复，哪些只是 A/B 初始值

### 5.1 根因修复

下列项目直接阻断已确认的故障链：

- IMU 队列从 10 增大并增加 timing 诊断
- 移除默认 Python relay，在 C++ 内翻转 IMU
- 坏 LiDAR 更新前保存 EKF 状态，失败时回滚
- rejected frame 不进入 `map_incremental()`、ikd-tree 和 PCD
- ICP 频率单位修正
- ICP 使用包含最新帧的短窗口
- ICP 平移/旋转跳变门
- Open3D 多线程共享状态同步

### 5.2 保守 A/B 参数

`mid360.yaml` 当前还设置：

- `max_iteration: 5`
- `filter_size_surf: 0.3`
- `filter_size_map: 0.3`
- `mapping.det_range: 30.0`

这些值是为室内走廊提供更多匹配点、限制无关远距离点并提高迭代收敛机会的保守起点，**不是已经通过真机证明的根因**。它们可能增加 CPU 开销，必须结合 `[FAST_LIO_TIMING]` 做 A/B 测试。

建议一次只调整一组：

1. 先保持本报告默认值测试。
2. 如果 timing 正常但有效点过少，可优先比较 `filter_size 0.3` 与 `0.4/0.5`。
3. 如果 timing 显示处理明显积压，可先把 `max_iteration` 从 5 降到 4，而不要关闭 guard。
4. 如果室外或大空间有效结构距离超过 30 m，再逐级提高 `det_range`。

## 6. 修改文件清单

1. `botbrain_ws/src/fast_lio/src/laserMapping.cpp`
2. `botbrain_ws/src/fast_lio/config/mid360.yaml`
3. `botbrain_ws/src/g1_pkg/launch/fast_lio.launch.py`
4. `botbrain_ws/src/g1_pkg/launch/livox_MID360.launch.py`
5. `botbrain_ws/src/g1_pkg/launch/localization_3d.launch.py`
6. `botbrain_ws/src/open3d_loc/launch/open3d_loc_g1.launch.py`
7. `botbrain_ws/src/open3d_loc/src/global_localization.cpp`
8. `机器人项目run.md`
9. 本报告

## 7. G1 真机编译与部署

在 G1 项目目录执行项目现有 builder 流程，例如：

`docker compose run --rm builder_base bash -lc "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select fast_lio g1_pkg open3d_loc --cmake-args -DCMAKE_BUILD_TYPE=Release -DOpen3D_DIR=/opt/open3d/lib/cmake/Open3D"`

编译成功后不要只 restart，必须让容器和 install 结果完整刷新：

`docker compose stop fast_lio localization navigation`

`docker compose rm -f fast_lio localization navigation`

然后按项目正常顺序重新 `up`。

## 8. 真机验收步骤

### 8.1 建图 FAST-LIO

1. 机器人完全静止，等待 `IMU Initial Done`。
2. 再静止约 30 秒，检查 `[FAST_LIO_TIMING]`。
3. 确认启动日志为：`imu=/livox/imu flip_yz=true imu_q=2000 lidar_q=100 guard=true`。
4. 左转 20～30°，停 3 秒，再前进约 1 m。
5. 右转 20～30°，停 3 秒，再前进约 1 m。
6. 做一次 90° 走廊转弯，逐级提高速度。
7. 在 Foxglove 中只用 `camera_init` 观察 `/cloud_registered_1`。
8. 如果出现 guard rejected，确认随后是否 recovered，并检查旧墙是否没有被新错误点覆盖。
9. 保存 PCD 后检查被拒阶段是否没有出现大面积重影或飞点带。

### 8.2 导航 Open3D

1. 日志必须显示：`ICP 4.00 Hz (250.0 ms)`。
2. 观察正常转弯 correction 是否显著低于 1 m/15°。
3. 快速转弯时若 ICP 给出大跳变，应看到 `Rejecting ICP jump`，同时 map→odom 不应被覆盖。
4. 轻微转弯后继续前进，定位应能在后续好帧继续更新，而不是一次跳变后只能重启。

## 9. 关键日志解释

### `[FAST_LIO_TIMING]`

- `imu_count` 长期低于 5：订阅 QoS、驱动发布频率、CPU 调度或时间同步仍有问题。
- `max_gap > 0.02 s`：转弯去畸变风险高，应优先解决 IMU 丢样，而不是继续放宽匹配门限。
- `imu_buffer/lidar_buffer` 持续增长：计算吞吐低于传感器输入，需降低点数/迭代或检查 CPU。
- `end_minus_last_imu` 应接近 0；明显偏大表示 scan 末端缺少 IMU 覆盖。

### `[FAST_LIO_GUARD]`

- 偶发 rejected 后很快 recovered：保护机制按预期工作。
- 连续大量 rejected 且 effective 很低：环境几何退化、点云过稀或地图已经在开启保护前受损。
- residual 高：点到平面匹配不一致，检查运动补偿、时间同步、动态障碍和外参。
- correction 突然很大：IMU 预测或 LiDAR 匹配跳变；不要简单放宽到数米，否则会重新允许地图污染。

## 10. 风险与回退方式

1. Reliable QoS 必须与 Livox publisher 兼容。真机运行 `ros2 topic info -v /livox/imu` 和 `/livox/lidar` 检查。如果 publisher 只提供 Best Effort 而 ROS 2 报 QoS incompatible，应按实际 publisher profile 调整订阅 reliability，但保留较深 KeepLast。
2. guard 门限过严会造成连续拒帧，但地图不会被坏帧继续污染。应根据日志逐项调整，不要一次性全部放宽。
3. 连续拒帧期间使用纯 IMU 预测，短时间可维持，长时间仍会漂移；该 guard 是安全隔离，不是回环优化。
4. FAST-LIO 仍没有全局回环/位姿图优化。长直走廊的长期累计误差不能仅靠本次保护完全消除。
5. 若必须回退到 Python relay：把 FAST-LIO topic 改回 `/livox/imu_corrected`，启动 `imu_flip.py`，并把 `imu_flip_yz` 设置为 false。三个条件必须同时执行。
6. 可回退 A/B 参数到原值，但建议保留 timing、finite 检查、EKF 回滚、地图写入隔离和 ICP 跳变门。

## 11. 静态检查边界

本地已完成以下静态检查：

- `git diff --check`：无空白错误；仅有 Git 的 LF/CRLF 提示。
- 参数名与 C++ `declare_parameter/get_parameter`、YAML、两个 Open3D launch 参数逐项对照。
- 搜索默认启动链路，确认没有同时启动 `imu_flip.py` 和 C++ `imu_flip_yz`。
- 检查 rejected 分支，确认在 `map_incremental()` 前立即返回，不会写 ikd-tree 或 `pcl_wait_save`。
- 搜索 `lock_exit_`、`std::clamp`：均无遗留引用。
- 对两个 C++ 文件和四个 Python launch 文件执行注释/字符串感知的括号平衡检查，结构均闭合。
- 检查 FAST-LIO 使用的 `toRotationMatrix()`、`Log()`、`PI_M`、`change_x()`、`change_P()` 在项目现有头文件或既有代码中均有对应定义/用法。

由于本机缺少 ROS 2、Open3D、PCL、livox_ros_driver2 和项目 Docker 环境，无法完成真实 C++ 编译链接、ROS 2 launch 加载与传感器数据回放。因此本报告不能把静态修复描述成已经真机验证成功；最终结论必须以 G1 编译结果、上述日志和转弯路线测试为准。


---

## 12. 第三轮根因闭环与新增修正（2026-07-12）

### 12.1 根因一：FAST-LIO 严格 guard 可能进入“安全但永久锁死”

第二阶段的 rejected 分支正确阻止了坏帧写入 ikd-tree/PCD，但连续拒绝期间只有 IMU propagation。随着纯 IMU 误差积累，真实 LiDAR 匹配所需 correction 会逐渐超过普通 0.50 m/20° 门限，于是即使几何重新变好，也可能继续被 guard 拒绝。

本轮增加 `state-only recovery`：连续拒绝达到 `guard_recovery_min_rejections=5` 后，只允许同时满足更高有效点比例（0.10）、更低 residual（0.15 m）和有限恢复 correction（1.50 m/45°）的候选修复 EKF 状态。恢复候选立即 return，绝不执行 `map_incremental()`；下一帧必须重新通过严格门才恢复地图写入。

同时把 `guard_recovery_max_residual` 限制为不大于普通 `guard_max_residual`，避免所谓恢复条件反而比普通几何质量门更松。

### 12.2 根因二：IMU propagation 本身异常会绕过 LiDAR guard

LiDAR guard 只能保护 scan-to-map update。如果 IMU propagation 已经产生非有限状态或 covariance，后续 ICP、点云变换和地图写入都可能继承污染。本轮在 propagation 前保存状态/协方差，并在传播前、传播后分别做 finite 检查；传播后异常时恢复旧状态并跳过该帧全部地图写入。

### 12.3 根因三：旧点云被重复 ICP，制造“两帧一致”的伪证据

原定位循环受 odometry timestamp 驱动。FAST-LIO odometry 比点云更新更频繁或点云短暂停顿时，同一聚合点云可能被多次 ICP。中等 correction 需要两次确认的逻辑因此可能由同一数据连续触发，不能证明时间一致性；初始化的连续成功也有相同风险。

新增 `scan_generation_` 后，每个聚合窗口只处理一次。正常定位与初始化分别保存 `last_processed_scan_generation`，两次确认必须来自不同 incoming cloud window。无新点云时正常定位置信度清零，不再拿旧 fitness 冒充当前可信度。

### 12.4 根因四：Open3D 没有验证 `cloud_registered_1` 的坐标系

Open3D 当前算法按“输入 source 已在 FAST-LIO 世界坐标”设计：source crop 使用 odom/world 中的 base pose，ICP 初值使用 map→odom。若 topic 被误 remap 到 `cloud_registered_body_1`，或消息 header 仍是 body，算法会把随机器人旋转的点当成世界点，再通过 ICP 修改 map→odom，表现就是转弯后整片点云和定位一起失控。

新增 `registered_cloud_world_frame=camera_init`。frame 不匹配时直接拒绝点云、置信度置 0，并明确提示不得把 body 点云接入。该检查把之前只依赖 Foxglove 人工选择 topic 的约定变成运行时代码约束。

### 12.5 根因五：`/initialpose` 变换方向错误

Foxglove/RViz 发送的是机器人在地图中的 pose，即 `map_T_base`。旧代码直接写入 `mat_odom2map_`，相当于把 map_T_base 当 map_T_odom；只在 odometry 接近单位阵时偶然正确。机器人已经移动后重定位会引入额外的 odom_T_base，产生大跳变。

正确关系已改为：

`map_T_odom = map_T_base * inverse(odom_T_base)`

并同步更新 map→odom、base→map、Kalman 基准和 confidence。

### 12.6 根因六：人工重定位可能被计算中的旧 ICP 覆盖

ICP 计算不持有 pose mutex，这是正确的性能设计，但意味着 `/initialpose` 可能在 ICP 运算期间更新 map→odom。若计算完成后无版本检查，旧 snapshot 的结果会覆盖用户刚设置的新 pose。

新增 `manual_pose_generation_`。人工 pose 更新和 generation 增加在同一 pose lock 内完成；初始化与正常 ICP 在计算前记录 generation，在写入前重新比较。发现变化即丢弃 stale ICP，并清除 pending correction、submap cache 和 last_loc。

### 12.7 根因七：初始化低质量 correction 会逐轮把 seed 带走

旧初始化允许 fitness 仅达到较低 `min_initialization_fitness` 就更新 map→odom，即使尚未达到真正的 `threshold_fitness_init`。在重复结构走廊中，这会让低质量 candidate 一轮轮改变下一轮初值，最后离开正确收敛盆地。

现在有效 `min_initialization_fitness` 强制不低于 `threshold_fitness_init=0.50`；还必须满足 RMSE≤0.30、平移≤2.0 m、旋转≤45°。初始化完成需要两个不同 scan generation 连续成功。

### 12.8 accepted-only confidence

以下情况统一发布 `loc_fitness_=0`：无新点云、点数不足、pose snapshot 非法、ICP 非 finite、fitness/RMSE 不合格、jump gate 拒绝、人工 pose、stale ICP。只有真正写入 map→odom 的 accepted ICP 才发布本帧 fitness，避免下游把上一帧或被拒结果误判为当前定位健康。

### 12.9 本轮 Open3D 参数

| 参数 | 当前值 |
|---|---:|
| `registered_cloud_world_frame` | `camera_init` |
| `loc_frequence` | 4.0 Hz |
| `pcd_queue_maxsize` | 5 |
| `threshold_fitness / threshold_fitness_init` | 0.50 / 0.50 |
| `max_icp_inlier_rmse` | 0.30 m |
| `immediate_icp_translation_step` | 0.25 m |
| `immediate_icp_rotation_step_deg` | 5° |
| `max_icp_translation_step` | 1.0 m |
| `max_icp_rotation_step_deg` | 15° |
| `large_correction_confirmations` | 2 |
| candidate consistency | 0.20 m / 4° |
| initialization step | 2.0 m / 45° |
| min source/target points | 100 / 1000 |

### 12.10 真机验证与判定

1. 先运行 `ros2 topic info -v /livox/imu`、`/livox/lidar`，确认 QoS 兼容，再分别检查 hz。
2. Foxglove 固定/显示坐标都设 `camera_init`，只观察 `/cloud_registered_1`。
3. 若出现 `Rejecting cloud_registered_1 frame`，必须先修正 topic 或 header.frame_id；不能通过降低 ICP 质量门绕过。
4. 静止等待 `IMU Initial Done`，慢速左右转，做 90° 转弯后停稳，再前进约 1 m。
5. FAST-LIO 连续 rejected 后，若出现高质量恢复，应看到 `state-only recovery`；该恢复帧不应增加地图点，下一严格好帧才出现 recovered 并恢复写图。
6. Open3D 中等 correction 应先出现 `Holding ... (1/2)`，只有下一份新点云给出一致 candidate 才 accepted。
7. 快速转弯的离群结果应出现 `Rejecting ICP jump` 或 `Rejecting ICP quality`，map→odom 不应被覆盖。
8. 发送 `/initialpose` 后若旧 ICP 正在计算，应看到 stale result 被丢弃，人工 pose 不应被弹回。

### 12.11 回退建议

不建议回退 finite 检查、状态/协方差回滚、rejected 地图隔离、点云 frame 校验、generation 去重和 `/initialpose` 正确变换。若真机发现正常 correction 经常被误拒，可一次只调整一个数值门限并保留日志：优先根据真实 RMSE/fitness 调整质量门，其次调整 immediate/maximum correction；不要直接取消 guard 或把最大 correction 放宽到数米、180°。

### 12.12 验证边界

本轮仅完成代码、配置、变换关系和并发状态机的静态复查。本机没有 ROS 2、Open3D、PCL、Livox 驱动和 G1 传感器数据，未执行 C++ 编译链接、launch 加载或真机 rosbag 回放。Python launch 也未运行 `py_compile`。因此“问题已完全解决”必须以机器人端重新 build 后的日志和上述转弯路线为准。

## 13. 第四轮深层复查：转弯后再次移动的剩余根因与修正（2026-07-12）

本轮继续沿着“为什么旋转时暂时稳定、旋转后再次移动却突然不可恢复”追踪到点云缓存、初始化提交策略和 FAST-LIO 空 IMU 路径。下面几项不是 Foxglove 显示问题，而是会真实影响 ICP 输入或地图写入的数据链问题。

### 13.1 Open3D 历史世界点云混合会放大急转后的错位

`/cloud_registered_1` 虽然声明在 `camera_init` 世界系，但它的坐标来自当时的 FAST-LIO 状态。急转期间如果 FAST-LIO 的姿态已经出现短时误差，连续 5 帧世界点云并不一定互相重合。旧实现把这 5 帧直接相加成一个 ICP source：旧墙、转弯中的错墙和最新墙会同时存在。这样 ICP 看到的不是一帧刚体点云，而是一个带重影、甚至带两套走廊方向的混合体，fitness 仍可能在重复走廊中看起来较高。

修正：

- G1 配置、两个 launch 和 C++ 默认值的 `pcd_queue_maxsize` 都从 `5` 改为 `1`；
- Open3D 只使用最新的 `camera_init` 世界点云做匹配；
- 用点数下限保证单帧数据不足时拒绝 ICP，而不是重新混入可能已经错位的历史帧。

这是针对“转弯后稳定一段时间、再次移动时历史错位点云一起把 ICP 拉飞”的直接防护。代价是单次 source 点数减少，因此真机必须观察 `source=.../100`；若单帧长期不足，可尝试 `2`，不建议直接恢复为 `5`。

### 13.2 初始化阶段原来会在确认前逐帧修改 map->odom

旧逻辑虽然要求连续两次成功，但第一次看似合格的 ICP 会立即写入 `mat_odom2map_`，第二次再从已经被修改的位姿继续算。因此所谓“两次成功”并不是两个独立 scan 对同一个绝对候选的确认，低质量但每步都在门限内的结果仍可逐帧把初始位姿带走。

修正后的初始化流程：

1. 每个新 scan generation 计算一个绝对 `candidate_odom2map`；
2. 第一份结果只进入 pending，不写 `mat_odom2map_`；
3. 下一份独立点云必须在平移 `0.20 m`、旋转 `4 deg` 内给出一致候选；
4. 两份候选的间隔必须不超过 `icp_candidate_max_age_sec=1.0 s`；
5. 只有达到确认次数后才一次性、加锁提交 `map_T_odom`；
6. `/initialpose` 在计算中发生变化时，pending 和旧 ICP 一并作废。

这消除了初始化阶段“每一帧只错一点，但两三轮后整体已经走偏”的状态累积路径。

### 13.3 正常定位的大修正候选增加超时约束

之前两次确认虽然来自不同 scan generation，但 pending 候选没有时间寿命。点云暂停、处理阻塞或服务短时断流后，恢复后的新候选仍可能拿很久以前的候选完成第二次确认。

新增参数：

```yaml
icp_candidate_max_age_sec: 1.0
```

只有 1 秒内的两个一致候选才能确认中等修正；超时后新候选重新从 `1/2` 开始。人工重定位、无效位姿和成功提交仍会清理候选历史。

### 13.4 缩小“单帧立即接受”范围，阻止小角度连续累积

旧参数允许 `0.25 m / 5 deg` 的修正单帧直接写入。重复走廊中，一次 3～5 度的错误 ICP 可能仍有较高 overlap；如果连续发生，就会形成用户看到的“先积累，下一次轻微转弯突然完全飘走”。

G1 参数改为：

```yaml
immediate_icp_translation_step: 0.10
immediate_icp_rotation_step_deg: 2.0
```

大于该范围但仍处于总门限 `1.0 m / 15 deg` 内的修正，不会直接写入，必须经过两个新点云窗口的一致确认。总门限暂未进一步收紧，以免真实急转漂移已经较大时完全失去恢复机会。

### 13.5 FAST-LIO 空 IMU 帧会重放上一帧点云（已修正）

`feats_undistort` 是跨 scan 复用的对象。原来的 `ImuProcess::Process()` 在 `meas.imu.empty()` 或 IMU 尚在初始化时直接 `return`，但没有清空输出点云。于是 timer 后续可能继续使用上一帧已经去畸变的点云，把它当成当前 LiDAR scan 再参与匹配或写图。

这条路径非常符合偶发性故障：正常时不出现；一旦转弯时 IMU/LiDAR 边界上出现空 IMU 包，旧走廊点云会以新的状态再次进入处理，随后地图和状态可能一起被拉偏。

修正：`ImuProcess::Process()` 进入后立即清空 `cur_pcl_un_`，再处理所有 early return。这样空 IMU、初始化帧或异常帧只会得到空输出；`laserMapping.cpp` 已有的 `feats_undistort->empty()` 检查会跳过该 scan，不会重放旧云。

### 13.6 LiDAR 时间回跳时同时清理 time_buffer

原代码检测 LiDAR 时间回跳时只清 `lidar_buffer`，没有清与其逐项对应的 `time_buffer`。两者长度/索引一旦错位，后续点云会拿到旧时间戳，去畸变和 IMU 同步都可能完全错误。

标准点云回调和 Livox 回调现在同时执行：

```text
clear lidar_buffer
clear time_buffer
lidar_pushed = false
```

该修复主要覆盖驱动重连、时钟回跳和 rosbag 循环等边缘情况。

### 13.7 Open3D 变换语义复核结论

已继续核对 `RegistrationIcp()` 和 `RegistrationMultiScaleIcp()`：

- `RegistrationIcp(source, target, ..., init_matrix)` 先把 source 乘 `init_matrix`，Open3D 返回的是相对该已变换 source 的增量 correction；
- 正常定位使用 `candidate_odom2map = correction * current_odom2map`，乘法方向正确；
- `EvaluateRegistration(source, target, ..., candidate_odom2map)` 中 source 仍处于 `camera_init/odom` 数值坐标，target 在 map，candidate 是 `map_T_odom`，语义正确；
- 初始化先把 source 乘当前 `map_T_odom`，多尺度 ICP 返回 map 系增量，再左乘当前值，语义同样正确；
- 因此本轮没有改动底层 Open3D correction 乘法，问题主要在“输入混合、确认方式和提交时机”。

### 13.8 真机验收新增观察项

启动时应看到近似：

```text
ICP 4.00 Hz (250.0 ms), queue=1, ... immediate<=0.10m/2.0deg, ... confirmations=2 within 1.00s
```

初始化阶段：

```text
LocalizationInitialize: holding consistent candidate (1/2)
Localization initialization succeeded: ... consistent confirmations=2
```

正常定位中等修正：

```text
Holding large ICP correction ... (1/2)
```

如果第二帧超过 1 秒或不一致，应继续从 `1/2` 开始，不能沿用旧候选。

FAST-LIO 重点观察：

```text
[FAST_LIO_TIMING] abnormal timing
No point, skip this scan!
[FAST_LIO_GUARD] rejected=...
```

建议路线仍为：静止初始化至少 10 秒 → 直行 → 原地慢转 90 度 → 停 3 秒 → 再直行 → 同路线逐渐增加转速。必须同时录制 `/livox/imu`、`/livox/lidar`、`/Odometry_loc`、`/cloud_registered_1` 和上述日志。

### 13.9 验证边界

本机没有 ROS 2、Livox、PCL、Open3D 和 G1 真机运行环境。本轮已完成代码级语义复核和静态文本检查，但不能声称已经编译通过或真机彻底消除漂移。尤其 `imu_flip_yz`、真实外参、时间同步质量仍必须由真机日志验证；如果修正后 FAST-LIO 自身 `/Odometry_loc` 在急转时仍先跳变，Open3D 只能拒绝污染，不能替代正确的 LIO 前端。
### 13.10 新发现的 FAST-LIO 根本性未初始化状态与回滚不完整（已修正）

继续检查 `IMU_Processing.hpp` 时发现两个内部量在构造函数和 `Reset()` 中都没有显式初始化：

```text
acc_s_last
last_lidar_end_time_
```

它们却会在第一帧正式 `UndistortPcl()` 中立即参与：

- `acc_s_last` 被写入首个 IMU pose；
- `last_lidar_end_time_` 决定跳过哪些 IMU、以及第一段积分的 `dt`。

未初始化的 `double`/Eigen 向量属于未定义状态。其表现可能随进程、内存布局而变化，能够解释“有时转完还能稳定一段、有时下一次移动突然完全飘掉，而且重启后表现改变”。现在构造函数和 `Reset()` 都明确设置：

```text
acc_s_last = Zero3d
last_lidar_end_time_ = -1.0
```

此外，上一轮只在 IMU propagation 产生 NaN/Inf 时恢复 EKF `x/P`，但 `ImuProcess` 内部的 `last_imu_`、`angvel_last`、`acc_s_last`、`last_lidar_end_time_` 已经向前推进。这样下一帧会用“已回滚的 EKF + 未回滚的 IMU 时间状态”，仍可能永久错位。

本轮新增 `PropagationCheckpoint`：每次 `Process()` 前保存上述内部状态；如果 propagation 后 state/covariance 非有限，则同时恢复 EKF 和 IMU checkpoint、清空当前去畸变云，再跳过地图写入。至此 NaN/Inf 回滚不再只回滚一半。

## 14. 第五轮完成性审计：发现并修复跨 topic 帧错配与坏时序写图（2026-07-12）

### 14.1 本轮新定位到的关键根因：Open3D 可能把点云 N 与里程计 N+1 配在一起

FAST-LIO 的正常发布顺序是：

1. 先发布 `/Odometry_loc`；
2. 执行 `map_incremental()`；
3. 再发布 `/cloud_registered_1`。

旧版 Open3D 定位线程却先检查“里程计时间戳是否变化”，一旦发现新里程计就立刻把该时间戳记为已处理，然后才检查点云 generation。若 4 Hz ICP 线程恰好在上述第 1 步和第 3 步之间醒来，会发生：

- 已读取到第 N 帧新里程计；
- 点云仍是第 N-1 帧；
- 线程提前消耗了第 N 帧里程计时间戳，却没有执行 ICP；
- 第 N 帧点云随后到达时，由于里程计时间戳“不再变化”而不会被处理；
- 下一轮可能使用第 N 帧点云配第 N+1 帧机器人位姿。

直行时一帧错配不一定明显；转弯时，相邻帧姿态差快速增大，这种错配会直接表现为 ICP source crop、候选 correction 和走廊方向不一致，符合“转弯后稳定一会，再移动突然大漂移”的触发特征。

本轮修复：

- `CallbackScan()` 在 `lock_scan_` 下保存 `cloud_registered_1` 的时间戳；
- 里程计回调在 `lock_mat_odom2map_` 下同时保存位姿矩阵与对应时间戳，保证 ICP 原子地取得“同一条里程计消息”的矩阵和 stamp；
- 初始化 ICP 和正常 ICP 都改为由“新点云 generation”驱动；
- 只有当点云 stamp 与里程计 stamp 的差值不超过 `max_scan_odom_time_skew_sec` 才允许 ICP；
- G1 默认阈值为 `0.03 s`；不匹配时不消耗点云 generation，等待同帧数据到齐；
- 新日志：

```text
Skipping ICP until cloud/odometry stamps match (...)
LocalizationInitialize: waiting for matching cloud/odometry stamps (...)
```

这不是单纯“再加一个 ICP 阈值”，而是修复了跨 topic 的确定性竞态。

### 14.2 FAST-LIO 坏时序现在不能再写入首帧地图或增量地图

原实现的 `[FAST_LIO_TIMING]` 只负责打印。即使出现 IMU 丢样、scan 时长异常或 scan 末端 IMU 覆盖不足，只要计算结果仍是有限值，LiDAR 更新仍可能写入 ikd-tree。走廊中错误去畸变有时仍能得到看似不错的 residual，因此只靠几何 fitness 不足以隔离该坏帧。

现在每一帧都会计算 `timing_ok`，要求：

- 每 scan 至少 5 条 IMU；
- 包括跨 LiDAR 帧边界在内，最大 IMU 间隔不超过 `0.02 s`；
- LiDAR scan 时长在 `0.05~0.15 s`；
- scan 结束时间与最后 IMU 的差值在 `[-0.001, 0.03] s`。

若不满足：

- 仍允许 IMU propagation 前进，避免人为切断状态时间线；
- 不允许正常 LiDAR update 通过 guard；
- 不允许 state-only recovery；
- 不允许以该帧初始化 ikd-tree；
- 不写增量地图和 PCD。

日志中的 `[FAST_LIO_TIMING] ok=false` 与 `[FAST_LIO_GUARD] timing=false` 可直接确认是哪一层拒绝。

### 14.3 被拒绝或仅恢复状态的 FAST-LIO 帧不再发布世界点云

此前 rejected 分支虽然不写 ikd-tree，却仍发布按 IMU 预测位姿变换后的 `/cloud_registered_1`。这会产生两个问题：

1. Foxglove 的 decay trail 仍会显示一帧未被 LiDAR 确认的世界云，看起来像“地图又被拖着走”；
2. Open3D 会把 FAST-LIO 已拒绝的世界位姿再次拿去做 ICP，形成二级级联跳变。

现在：

- rejected 帧继续发布预测里程计和可选 body-frame 诊断云；
- state-only recovery 帧也不发布世界云；
- 只有下一帧通过严格 timing + geometry + correction guard 后，才恢复发布 `/cloud_registered_1`；
- ikd-tree/PCD 仍只接收严格通过帧。

因此真机出现短时拒帧时，Foxglove 世界云会短暂保持上一份可信结果，而不是显示一个未确认的旋转/平移；Open3D 的 scan generation 也不会前进。

### 14.4 FAST-LIO guard 收紧与初始地图保护

原门限允许普通 LiDAR correction 每帧达到 `0.50 m / 20 deg`，state-only recovery 达到 `1.50 m / 45 deg`。这里的 correction 是“LiDAR 对 IMU prediction 的误差修正”，不是机器人真实一帧转了多少度；允许 20~45 度等价于允许时间同步、IMU 轴向或错误走廊匹配直接改写状态。

G1 当前默认值已收紧为：

```yaml
guard_min_effective_points: 100
guard_min_effective_ratio: 0.10
guard_max_residual: 0.15
guard_max_translation_correction: 0.25
guard_max_rotation_correction_deg: 5.0

guard_recovery_min_rejections: 5
guard_recovery_min_effective_ratio: 0.15
guard_recovery_max_residual: 0.10
guard_recovery_max_translation_correction: 0.75
guard_recovery_max_rotation_correction_deg: 15.0
```

同时：

- 首次 ikd-tree 建立从“超过 5 个点”改为至少 `guard_min_effective_points`，且必须 `timing_ok`；
- 无有效匹配点时把 `res_mean_last` 设为 infinity，避免日志/guard 继续看到上一帧的小 residual；
- 这些值以“防止不可恢复污染”为优先。若真机长期因有效点不足拒帧，应先看点数、IMU 时间和外参日志，不能直接恢复 20/45 度大门限。

### 14.5 Open3D fitness 评估半径修正

正常定位原先用 `voxelsize_fine * 4` 评估，G1 为 `0.8 m`；初始化用过 `*3`，为 `0.6 m`。在平行走廊墙面中，这会把已经明显错位的墙仍计为 inlier，虚高 fitness。

初始化和正常定位现在统一使用与 fine ICP 相同的 `voxelsize_fine * 2`，G1 为 `0.4 m`。ICP 搜索半径与验收半径保持一致，减少“ICP 已错位但 fitness 仍高”的假阳性。

### 14.6 代码层面已经闭环的链路

当前防护链为：

```text
原始 IMU/LiDAR
  -> 内部 IMU 轴向修正，避免 relay 延迟
  -> 每帧 IMU/LiDAR 时序健康检查
  -> 非有限 propagation 完整回滚 EKF + ImuProcess 内部状态
  -> 严格 LiDAR correction guard
  -> rejected/recovery 不写图、不发世界云
  -> 仅可信 world cloud 推进 Open3D scan generation
  -> world cloud 与同 stamp Odometry_loc 原子配对
  -> ICP 同半径 fitness/RMSE + 跳变量门
  -> 大 correction 两个独立新 scan 一致确认
  -> accepted 后才提交 map->odom
```

从代码路径上，已切断已知的三条不可恢复污染通路：

1. 坏去畸变帧直接写 FAST-LIO 地图；
2. FAST-LIO 已拒绝帧继续喂给 Open3D；
3. Open3D 把点云 N 与里程计 N+1 混配后提交 correction。

### 14.7 仍不能由本机静态修改替代的根本边界

- 长而重复、没有横向结构的走廊，沿走廊方向对纯几何 ICP 本来就弱可观测；代码 gate 可以防跳飞，但不能凭空创造几何约束。
- 必须真机验证 MID360 raw IMU 经 `R_x(pi)` 后：静止重力方向正确，左右转 yaw 符号与点云一致。
- 必须用 rosbag/日志确认硬件时间偏移；若 `timing_ok=true` 但转弯 correction 仍周期性偏大，需要用 LI-Init 或等价工具标定 `time_offset_lidar_to_imu` 和厘米级 LiDAR-IMU 外参。
- 长期全局累计误差仍需要回环、姿态图优化、视觉/标志物、可靠的机器人里程计等额外约束。

本机无 ROS 2、PCL、Open3D、Livox 和 G1 真机环境，因此本轮只能声明“静态路径闭环并修复了确定性竞态”，不能声明已经编译或真机验证成功。

### 14.8 第五轮真机验收重点

启动日志应出现：

```text
ICP 4.00 Hz (250.0 ms), queue=1, ... stamp_skew<=0.030s ...
```

测试时重点观察：

- 正常 accepted 帧的 cloud/odom skew 应接近 0；不应持续出现 stamp mismatch；
- 急转或丢 IMU 时可出现 `timing=false` / rejected，但该阶段 `/cloud_registered_1` 应暂停刷新，不应生成新的错误世界云；
- 恢复后先看到严格 accepted 帧，世界云才继续刷新；
- Open3D 不应再出现“每次都错后一帧”的 correction 节奏；
- 若 stamp mismatch 持续出现，记录两个具体时间戳，检查中间是否有 remap、转发器或节点重新盖写 header.stamp。

推荐录制：

```bash
ros2 bag record /livox/imu /livox/lidar /Odometry_loc /cloud_registered_1 /cloud_registered_body_1
```
