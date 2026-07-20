# Foxglove Studio 使用指南（botbrain G1机器人）

## 1. 连接方式

项目 `foxglove_bridge` 监听 `0.0.0.0:8765`，支持两种方式：

| 方式 | 说明 |
|------|------|
| **浏览器** | 直接打开 [app.foxglove.dev](https://app.foxglove.dev)，无需安装 |
| **桌面应用** | [foxglove.dev/download](https://foxglove.dev/download) |

连接步骤：`Open Connection` → `Foxglove WebSocket` → `ws://<机器人IP>:8765`

---

## 2. 参考系配置

左侧设置 → **参考系** 展开：

| 字段 | 说明 |
|------|------|
| **固定参考系** | 所有数据渲染的基准坐标系，决定"什么东西静止不动" |
| **显示参考系** | 相机跟随的坐标系，决定"镜头看哪里" |

### 各组合效果对比

| 固定参考系 | 显示参考系 | 效果 |
|-----------|-----------|------|
| `map` | `map` | 地图静止，镜头固定，机器人自己移动 |
| `map` | `g1_robot/base_footprint` | 地图静止，镜头跟随机器人地面投影移动 ← **推荐** |
| `base_link` | `base_link` | 机器人居中，ICP校正时整个地图会抖动 ← 避免 |

### 推荐设置

| 字段 | 推荐值 | 说明 |
|------|--------|------|
| 固定参考系 | `map` | 地图固定不动 |
| 显示参考系 | `g1_robot/base_footprint` | 镜头跟随机器人地面投影 |
| 跟踪模式 | 位姿（位置+姿态） | 相机跟随机器人姿态 |

### 建图/导航时参考系选择

| 场景 | 固定参考系 | 显示参考系 | 主要看什么 |
|------|------------|------------|------------|
| 建图检查 | `camera_init` 或 `map` | `camera_init` / `map` | FAST-LIO 世界点云、累计栅格是否正常生成 |
| 定位检查 | `map` | `g1_robot/base_footprint` | `/pcd_map`、`/cloud_registered_1`、`/localization_3d` 是否对齐 |
| 导航执行 | `map` | `g1_robot/base_footprint` | `/map`、机器人 footprint、`/g1_robot/plan`、局部避障 |

注意：建图时看到的实时累计栅格/点云会继续变化；导航时 `/map` 是静态地图，动态黑点通常来自 costmap 或点云叠加，不代表地图文件被改写。

---

## 3. 推荐话题配置

| 优先级 | 话题 | 说明 |
|--------|------|------|
| ✅ 必看 | `/map` | 静态地图（需 localization 服务运行） |
| ✅ 必看 | `/cloud_registered_1` | FAST-LIO 世界点云；导航对齐检查时 Decay 设为 `0` |
| ✅ 必看 | `/tf` | 坐标系树 |
| 🔵 可选 | `/pcd_map` | Open3D 使用的成品 3D 地图 |
| 🔵 可选 | `/g1_robot/global_costmap/costmap` | 全局代价地图 |
| 🔵 可选 | `/g1_robot/plan` | 规划路径 |
| ⚠️ 谨慎开 | `/cloud_effected_1`、`/cloud_registered_body_1` | 实时局部点云/诊断点，容易让画面看起来像地图在变 |
| ❌ 建议关 | `/g1_robot/local_costmap/costmap` | 高频闪烁，10Hz；只在排查避障时临时打开 |
| ❌ 建议关 | `/g1_robot/trajectories` | MPPI 2000条轨迹，闪烁严重 |

---

## 4. 发布位姿工具

左侧 **发布** 栏配置，右侧3D工具栏点击图标使用：

| 工具 | 配置话题 | 作用 |
|------|---------|------|
| **2D 位姿估计** | `/initialpose` | 校正定位，不让机器人动 |
| **2D 位姿** | `/g1_robot/goal_pose` | 让机器人导航到目标点 |
| **2D 点** | — | 用不到 |

### 如何准确发布初始位姿（2D 位姿估计）

**第一步：切换俯视图**

右侧工具栏 → 相机图标 → 选 **Top**（或按 `T`）→ 切到正上方俯视，和 RViz 默认视角一致。

**第二步：找到机器人在地图上的位置**

对比点云轮廓和地图轮廓，用墙角、房间边缘等特征点做参照，定位机器人大概在哪。

**第三步：点击并拖动**

- **点击位置** = 机器人在地图上的实际位置
- **拖动方向** = 机器人当前朝向（**箭头必须对准机器人目前面朝的方向**）
- 拖动距离不重要，方向才是关键

> ⚠️ 如果方向发反了，定位会偏转180°，需重新发布。

---

## 5. 常见问题

### TF 标签名字挡住视线
左侧 **变换(48)** → 关闭**显示标签** / **显示连线**

### 背景白色刺眼
左侧 **场景** → **背景**颜色 → 改为 `#1a1a1a`

### 点云一直闪烁
导航对齐检查使用 `/cloud_registered_1`，**点衰减时间**设为 `0`。`/cloud_registered_body_1` 只用于查看机器人当前局部扫描，不能判断世界地图是否漂移。

### 点云看起来倾斜
先确认打开的是哪个点云：

| 话题 | 坐标系 | 是否会随机器人身体倾斜 | 用途 |
|------|--------|------------------------|------|
| `/cloud_registered_body_1` | `body` | 会 | 诊断当前雷达帧、局部避障输入来源 |
| `/cloud_registered_1` | `camera_init` / 世界系 | 不应持续倾斜 | 判断 FAST-LIO 世界点云是否漂移 |
| `/pcd_map` | `map` | 不应倾斜 | 判断成品 3D 地图和定位是否对齐 |

G1 走路时机身会有 roll/pitch，`/cloud_registered_body_1` 在 `map` 固定参考系下显示会看起来一边高一边低，这是 body frame 诊断点云的正常现象。判断地图是否真的倾斜，应关闭 `/cloud_registered_body_1`，只看 `/cloud_registered_1`、`/pcd_map` 和 `/map`。

导航用的 `/scan` 会从 `/cloud_registered_body_1` 转到 `g1_robot/base_footprint` 平面坐标后再做高度过滤，避免 body 倾斜时把地面误当成障碍。

### 黑点/障碍物越来越多
先判断黑点来自哪一层：

| 现象 | 常见来源 | 说明 |
|------|----------|------|
| 只开 `/map` 也在变黑 | 静态地图源异常 | 需要检查 map server 加载的 `.yaml/.pgm` |
| 关掉 costmap/点云后不再变 | 动态层叠加 | 这是 `/g1_robot/*costmap*`、`/cloud_*`、`/scan*` 的显示效果 |
| 黑块围着障碍扩大 | `inflation_layer` | costmap 会把障碍膨胀，方便导航避障 |
| 机器人附近整片发黑 | 近身点/地面点被当障碍 | 检查 `/scan` 的 `range_min`、高度带，以及 local costmap 的 `obstacle_min_range` |
| 人走过后残留黑点 | obstacle clearing 不完整 | 检查 `/scan` 是否有空方向、costmap 的 `inf_is_valid` 是否为 `true`，以及 TF 时间是否丢帧 |

`/scan` 必须只保留 `sensor_msgs/msg/LaserScan`。Open3D 定位节点的调试点云应发布到 `/scan_loc`；如果 `ros2 topic list -t` 显示 `/scan` 同时存在 `PointCloud2` 和 `LaserScan`，说明定位节点的重映射未生效，需要先修复话题冲突。

如果 `/Odometry_loc`、`/cloud_registered_1` 和 `/scan` 同时停止，并且 FAST-LIO 日志出现 `output latched unhealthy`，这是连续匹配失败后的安全停发，不是 Foxglove 显示故障。此时不要继续导航，应检查 timing/effective points 后重启 `fast_lio`。

导航时推荐先只显示：

```text
/map
/g1_robot/global_costmap/published_footprint
/g1_robot/local_costmap/published_footprint
/g1_robot/plan
/g1_robot/transformed_global_plan
```

如果要看避障，再临时打开 `/scan` 和 `/g1_robot/local_costmap/costmap`。不要把 costmap 的黑点当成静态地图被改写。

当前导航配置里 `global_costmap` 包含：

```text
static_layer + obstacle_layer(/scan) + denoise_layer + inflation_layer
```

也就是说，全局代价地图仍参与规划，也会看到附近动态行人，但动态层只接过滤后的 `/scan`，并启用 raytrace clearing、denoise 和较小 inflation。已经写进 `ug.pgm` 的行人/噪点属于静态地图内容，必须修图擦除；运行时新出现的行人应由 global/local costmap 的 `/scan` 清除机制处理。局部避障主要由 `local_costmap` 的 rolling window 负责。

如果黑点已经影响导航，可清理动态 costmap：

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 service call /g1_robot/global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap {}
  ros2 service call /g1_robot/local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap {}
'
```

### `/map` 不显示
1. 确认 `localization` 服务在运行：`docker compose up fast_lio localization`
2. 固定参考系改为 `map`

### 有路径但机器人提前停止

先区分 Nav2 是“成功到达”还是“中途取消/失败”：

- `Goal reached` / `SUCCEEDED`：检查 planner `tolerance` 和 `xy_goal_tolerance`，两者的停车误差可叠加。
- `Goal was canceled` / `ABORTED`：检查 `compute_path_to_pose` timeout、`/scan` 新鲜度和 TF，这不是到点容差问题。
- 有 `cmd_vel_nav` 但机器人不动：检查高优先级 `manipulation_vel`、`cmd_vel_joy` 或 dead-man lock 是否覆盖 twist mux。
- `/scan` 持续断流或 FAST-LIO 出现 `output latched unhealthy`：导航必须停止，不要通过放大 timeout 强行继续。

Foxglove 发布 `/g1_robot/goal_pose` 和 `waypoint_navigator.py` 最终都进入同一个 NavigateToPose BT。Waypoint 工具不应自行在目标附近取消 action 并当作成功。

`/g1_robot/bt_navigator` 已原生订阅 `/g1_robot/goal_pose`。不要再启动自定义 `goal_pose_bridge.py`，否则同一个 Foxglove 目标可能被重复发送。

### 机器人显示在地图下方
先确认 Fixed Frame 是 `map`，不是 `camera_init`。成品 PCD 的地面已经校正到 `map z≈0`，定位节点会固定 `map -> odom.z≈+1.247m`，并将 `map -> odom` 的 roll/pitch 约束为零，只允许 ICP 修正平面 `x/y/yaw`。

不要再手工给 `/map` 设置 `-1.247` 的显示偏移。应检查：

```bash
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic echo --once /odom2map --field pose.pose.position
  timeout 3 ros2 run tf2_ros tf2_echo map camera_init || true
  timeout 3 ros2 run tf2_ros tf2_echo map g1_robot/base_footprint || true
'
```

`/odom2map` 和 `map -> camera_init` 的 Z 都应约为 `+1.247`；`map -> g1_robot/base_footprint` 的 Z 和 Roll/Pitch 应接近零。定位日志应持续显示 `map_odom_rp=0.00/0.00 deg`。若数值正确但在 `camera_init` Fixed Frame 下红色 `/pcd_map` 仍偏高，这是其启动时旧时间戳造成的显示现象，切换到 `map` 即可。

高度检查时只显示 `/pcd_map`、`/cloud_registered_1` 和 `/map`，且 PointCloud Decay 设为 `0`。`/cloud_registered_body_1`、`/cloud_effected_1` 和 FAST-LIO `/path_1` 分别是当前局部扫描、诊断点和位于 IMU 高度的轨迹，不用来判定地面高度。

### Schema 不匹配警告（`/scan`、`/livox/lidar`）
不影响功能，忽略即可。如需消除，从 `foxglove_bridge_params.yaml` 白名单删掉 `/scan`。

---

## 6. ⚠️ 发送 `/initialpose` 的 z 值问题（重要）

Foxglove 2D 工具会在当前 Fixed Frame 中发布位姿，因此发送前必须先把 Fixed Frame 设置为 `map`。

`initialpose_z_fix` 会把 2D 工具给出的 `z=0` 自动改为 `1.247`。定位链路只接受 `frame_id=map`，若收到 `camera_init`，relay 会先输出 `ignoring /initialpose...`；若绕过 relay 直接发到校正话题，C++ 节点会输出 `Rejecting initial pose...`。两者都会防止把错误参考系静默当作地图坐标。

### 命令行发送方式

```bash
docker exec -it g1_robot_bringup bash
source install/setup.bash

# x y 改为机器人在地图中的实际坐标；z=0 会由 relay 校正为 1.247
ros2 topic pub --once /initialpose \
  geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}}}}"
```

成功时 localization 日志必须出现 `Manual relocalization applied`。若没有该日志，先检查 `/initialpose -> /initialpose_corrected` 的 publisher/subscriber 链路。

启动定位服务后，节点会使用当前 `/cloud_registered_1` 与完整 `/pcd_map` 做 FPFH/RANSAC 全局粗配准，再用 ICP 精配准。它不读取上一次位姿，也不要求机器人位于建图起点。

只有连续两帧得到一致的地图位置，并同时通过 fitness 和 RMSE 门限，才会提交新的 `map -> odom`。日志出现 `Global localization initialization succeeded` 表示自动初始化完成；持续出现 `Global initialization did not produce...` 时，再使用 `/initialpose` 作为人工兜底。

---

## 7. ICP 定位漂移说明

| 参数 | 值 | 影响 |
|------|-----|------|
| `loc_frequence` | 4.0 Hz | 约每0.25s尝试一次新点云 ICP |
| `filter_odom2map` | false | 无卡尔曼平滑，校正时位姿跳变 |
| `threshold_fitness` | 0.5 | 还必须同时通过 RMSE、步长和多帧一致性门限 |
| `lock_map_odom_z` | true | 对校正后平层 PCD 固定 `map -> odom.z=1.247` |

**操作建议**：
- 机器人慢速移动
- 避免快速原地旋转
- 移动时监控 fitness，低于 0.7 停下等待收敛

```bash
# 实时查看 fitness
docker compose logs -f localization | grep fitness
```
