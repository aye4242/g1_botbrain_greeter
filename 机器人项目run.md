## 位置校正

### 配置启动

```bash
# 校正程序终端
cd /data/Location_Correction
./docker/run.sh 
# 相机终端
docker start lidar_cam_drive
docker exec -it lidar_cam_drive bash
cd /root/g1_workspace/
source install/setup.bash
ros2 launch realsense2_camera rs_launch.py     enable_depth:=false     enable_infra1:=false     enable_infra2:=false     enable_color:=true     enable_sync:=true     rgb_camera.color_profile:=640x480x30     initial_reset:=true
```

### AT码位置校正(xy二维)

```bash
# 终端1 AT码检测节点
python src/apriltag_correction/apriltag_correction/apriltag_detector.py --ros-args -r image_rect:=/camera/camera/color/image_raw -r camera_info:=/camera/camera/color/camera_info -p size:=0.075
# 终端2 校正计算节点
python src/apriltag_correction/apriltag_correction/correction_node.py \
  --ros-args --params-file /workspace/src/apriltag_correction/config/params.yaml -p network_interface:=enP8p1s0
# 使能计算
ros2 service call /enable_correction std_srvs/srv/SetBool "{data: true}"
# 停止计算
ros2 service call /enable_correction std_srvs/srv/SetBool "{data: false}"
```

### IMU控制机器人旋转

```bash
# 参数 angle_deg 选择旋转角度 tolerance_deg 设置角度容差（默认2度）
# 测试机器人连接情况和单步旋转控制测试
ros2 run gyro_rotation test_rotation enP8p1s0 90.0
# 向右旋转 90 度
ros2 run gyro_rotation rotate_node --ros-args -p angle_deg:=-90.0 -p network_interface:=enP8p1s0
# 向左旋转 90 度
ros2 run gyro_rotation rotate_node --ros-args -p angle_deg:=90.0 -p network_interface:=enP8p1s0
# max_speed 最大角速度 slow_speed 最小角速度 slow_threshold_deg 达到最小角速度时的误差角度
ros2 run gyro_rotation rotate_node --ros-args \
    -p angle_deg:=-90.0 \
    -p tolerance_deg:=2.0 \
    -p max_speed:=0.5 \
    -p slow_speed:=0.3 \
    -p slow_threshold_deg:=20.0 \
    -p network_interface:=enP8p1s0
```

## FAST_LIVO2 

```bash
# 硬件驱动终端1
docker start lidar_cam_drive
docker exec -it lidar_cam_drive bash
cd /root/g1_workspace/
source install/setup.bash
ros2 launch realsense2_camera rs_launch.py     enable_depth:=false     enable_infra1:=false     enable_infra2:=false     enable_color:=true     enable_sync:=true     rgb_camera.color_profile:=640x480x30     initial_reset:=true
# 硬件驱动终端2
docker exec -it lidar_cam_drive bash
cd /root/g1_workspace/
source install/setup.bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py 
# 程序终端
cd /data/livo2_ws
docker start fast_livo2
docker exec -it fast_livo2 bash
source install/setup.bash
ros2 launch fast_livo g1_d435i.launch.py use_rviz:=false
```

## 模仿学习

```bash
# 图像服务
cd ~/Desktop/xr_teleoperate/teleop/teleimager
conda activate unitree_lerobot
run.sh
# 策略
cd /data/unitree_lerobot
conda activate unitree_lerobot
export PYTHONNOUSERSITE=1
# 单步执行
python unitree_lerobot/eval_robot/eval_g1_chain.py --policy.path=/data/unitree_lerobot/train/zaji_left_only_go/checkpoints/160000/pretrained_model \
      --repo_id=/data/unitree_lerobot/train/local/zaji_left_only_go \
      --policy2_path=/data/unitree_lerobot/train/zaji_left_only_back/checkpoints/160000/pretrained_model \
      --repo_id2=/data/unitree_lerobot/train/local/zaji_left_only_back \
      --switch_steps=0 \
      --move_duration1=3.0 --move_duration2=0.0 \
      --arm=G1_29 --frequency=30 \
      --step_mode=true
# 自动执行
python unitree_lerobot/eval_robot/eval_g1_chain.py --policy.path=/data/unitree_lerobot/train/zaji_left_only_go/checkpoints/160000/pretrained_model \
      --repo_id=/data/unitree_lerobot/train/local/zaji_left_only_go \
      --policy2_path=/data/unitree_lerobot/train/zaji_left_only_back/checkpoints/160000/pretrained_model \
      --repo_id2=/data/unitree_lerobot/train/local/zaji_left_only_back \
      --switch_steps=200 \
      --move_duration1=3.0 --move_duration2=0.0 \
      --arm=G1_29 --frequency=30
```

## Botbrain

### 动作记录和回放

```bash
cd ~/botbrain_ws/botbrain_project-main/
docker compose up -d manipulation bringup state_machine
docker compose exec -it manipulation bash
# 或者直接使用docker compose run --rm manipulation bash
source install/setup.bash
#程序进行前以上步骤都要有
# 手臂控制权获取
python src/g1_manipulation_pkg/g1_manipulation_pkg/scripts/arm_limp.py
ros2 run g1_manipulation_pkg arm_limp
# 保存当前手臂姿态 src/g1_pkg/config/arm_poses.txt
ros2 service call /g1_robot/arm_cmd bot_custom_interfaces/srv/ArmCmd "{command: 1, name: 'pose_now'}"
#保存后退出控制权
# 查看姿态库名字
ros2 topic echo /g1_robot/pose/names
# 单动作回放
ros2 service call /g1_robot/arm_cmd bot_custom_interfaces/srv/ArmCmd "{command: 2, name: 'pose_now'}";
# 多动作线性回放
ros2 service call /g1_robot/arm_cmd bot_custom_interfaces/srv/ArmCmd \
    "{command: 6, name: '', names: ['left_go_1','left_go_2','left_go_3','left_go_4','left_go_5','left_go_6','left_go_7']}"
# 动作完成需要手动归还上身控制权
ros2 service call /g1_robot/arm_cmd bot_custom_interfaces/srv/ArmCmd "{command: 3, name: ''}"
# 刷卡预设动作,需要等动作播放完毕,程序自动退出,显示'Arm joint position released'
#需要录制新的动作是两个的多动作线性回放,具体看/home/unitree/botbrain_ws/botbrain_project-main/botbrain_ws/src/g1_pkg/scripts/
./src/g1_pkg/scripts/replay_sequence.sh
```

### 手臂控制（笛卡尔坐标）

```bash
cd ~/botbrain_ws/botbrain_project-main/
docker compose up -d manipulation
docker compose exec -it manipulation bash
source /botbrain_ws/install/setup.bash
# 启用手臂控制
ros2 topic pub --once /g1_robot/manipulation/enabled std_msgs/msg/Bool "{data: true}"
# 回到零位
ros2 topic pub --once /g1_robot/manipulation/home std_msgs/msg/Bool "{data: true}"
# 启动键盘控制
ros2 run g1_manipulation_pkg arm_teleop_keyboard --ros-args -r __ns:=/g1_robot
# 通过话题发送目标（右臂前伸）
ros2 topic pub --once /g1_robot/manipulation/hand_goal/right \
  geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'pelvis'}, pose: {position: {x: 0.35, y: -0.20, z: 0.15}, orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}}}"
# 灵巧手 开 关
ros2 topic pub --once /g1_robot/manipulation/dx3/hand_action/right std_msgs/msg/String "{data: 'close'}"
ros2 topic pub --once /g1_robot/manipulation/dx3/hand_action/right std_msgs/msg/String "{data: 'open'}"
# 获取灵巧手当前关节状态
ros2 topic echo /g1_robot/manipulation/dx3/right/motor_state
# 添加灵巧手动作
# 在src/g1_manipulation_pkg/g1_manipulation_pkg/manipulation/dx3_hand.py 35行左右添加预设值：A = [...]
# 再将预设值添加到对应的字典上： "B" = A,
ros2 topic pub --once /g1_robot/manipulation/dx3/hand_action/right std_msgs/msg/String "{data: 'B'}"
# 手动开启服务和可视化方式 launch_markers 是否开启rviz的marker位置标注
docker compose down manipulation
docker compose run --rm manipulation bash
ros2 launch g1_manipulation_pkg manipulation_launcher.launch.py interface:=enP8p1s0 launch_markers:=true 

```

### 建图导航

---

## 一、建图流程（快速参考）

> 每套完整地图由 **3 个文件**组成：
> - `<场景名>_scans.pcd`  → 3D 点云（供 localization 做 ICP 匹配）
> - `<场景名>.pgm`        → 2D 栅格图像
> - `<场景名>.yaml`       → 2D 栅格配置（记录分辨率和原点）
>
> **地图统一存放：**`/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/`

### 步骤 0：建图前准备

⚠️ **必须停止定位/导航服务，否则会两图交织、严重漂移！**

```bash
cd /data/unitree/botbrain_ws
docker compose stop localization navigation
```

### 步骤 1：配置地图保存名称与关键外参

修改 `mid360.yaml`（每次建图前建议先备份旧地图）：

```yaml
# 宿主机：/data/unitree/botbrain_ws/botbrain_ws/src/fast_lio/config/mid360.yaml
/**:
  ros__parameters:
    map_file_path: "/botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd"

    common:
      # MID360 倒装 180°，FAST-LIO 必须使用 imu_flip.py 修正后的 IMU。
      imu_topic: "/livox/imu_corrected"

    mapping:
      extrinsic_est_en: false
      # LiDAR 相对 MID360 内置 IMU 的刚性外参，单位 m，只有厘米级。
      extrinsic_T: [-0.011, -0.02329, 0.04412]

    pcd_save:
      pcd_save_en: true
```

> ⚠️ **不要把 `1.247` 写进 `extrinsic_T.z`。** `1.247 m` 是机器人站立时 MID360/IMU 到地面的高度，只用于实时栅格显示高度和建图后 PCD 地面平移；`extrinsic_T` 表示 LiDAR 相对 MID360 **内置 IMU** 的刚性外参。
>
> ⚠️ MID360 在 `MID360_config.json` 和 URDF 中均为绕 X 轴倒装 180°。点云已按该安装姿态旋转，而当前驱动发布的原始 `/livox/imu` 仍需做 `R_x(π)` 修正，即 **X 不变、Y/Z 取反**。因此 FAST-LIO 必须订阅 `/livox/imu_corrected`。

> 命名规范：`floor1`、`office_A`、`corridor_2F`。yaml 或 Python/C++ 改完后需重新 build 才能进入 install 空间。建议本次只编译相关包：
>
> `docker compose run --rm builder_base bash -lc "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select fast_lio g1_pkg --cmake-args -DCMAKE_BUILD_TYPE=Release -DOpen3D_DIR=/opt/open3d/lib/cmake/Open3D"`


### 步骤 2：启动建图服务并确认 IMU 修正

⚠️ **用 `stop` + `rm` + `up`，不要只用 `restart`**，确保旧容器进程和旧 install 结果不再运行。

```bash
# 终端 1：等待雷达和基础服务就绪
docker compose up bringup state_machine foxglove

# 终端 2：彻底停止旧建图进程，再启动新版本
docker compose stop localization navigation
docker compose stop fast_lio
docker compose rm -f fast_lio
docker compose up fast_lio

# 机器人保持完全静止，必须看到初始化完成后才能移动
docker logs g1_robot_fast_lio 2>&1 | grep "IMU Initial"
```

在另一个终端确认原始 IMU、修正 IMU和世界点云都在持续发布（每条 `hz` 命令单独运行，观察后按 Ctrl+C）：

```bash
docker exec -it g1_robot_fast_lio bash
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash

ros2 topic hz /livox/imu
ros2 topic hz /livox/imu_corrected
ros2 topic hz /cloud_registered_1

ros2 topic echo /livox/imu --once
ros2 topic echo /livox/imu_corrected --once
exit
```

诊断标准：

- `/livox/imu` 与 `/livox/imu_corrected` 都必须有稳定频率，不能只有其中一个有数据。
- corrected 相对 raw：`angular_velocity.x`、`linear_acceleration.x` 不变；Y/Z 分量符号相反。
- 静止时 corrected 平均加速度模长应接近重力加速度，日志会打印前 200 个样本的均值与 `|a|`。
- 必须等待 FAST-LIO 打印 **`IMU Initial Done`** 后再移动。
- 开启 PCD 保存时，`[MAP] frame=100, 200, 300...` 应递增，`pcl_wait_save` 应持续增长；不应一直显示 `frame=0`。


### 步骤 3：查看建图 + 驱动行走

**方式一：Foxglove（G1 端，推荐）**

在 3D 面板中使用以下配置：

- **Fixed Frame：`camera_init`**
- **Display/Follow Frame：`camera_init`**
- 点云只观察 **`/cloud_registered_1`**（其 `frame_id` 是 `camera_init`）
- 暂时关闭 **`/cloud_registered_body_1`**，该话题本来就在机器人 body 坐标系中，随机器人转动是正常定义

> 你当前把 Fixed Frame 和 Display/Follow Frame 都设成 `camera_init` 是正确的。若这种设置下 `/cloud_registered_1` 中的走廊、墙体仍随机器人一起旋转，说明 FAST-LIO 输出的姿态/位移估计错误，不是 Foxglove 视角跟随造成的。

**方式二：RViz2（workstation 端，备用）**

```bash
# workstation 端，前提：G1 上建图服务已启动（zenoh + bringup + fast_lio）
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/192.168.100.30:7448"]'
# 香港 G1：export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/192.168.37.204:7448"]'
ros2 daemon stop  >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
sleep 3
ros2 topic info /Odometry_loc | grep "Publisher count"
# Publisher count: 1 → 可以开 RViz2
rviz2 -d /home/aitech/Workspace/botbrain_project/configs/g1_mapping_rviz2.rviz
```

> Foxglove 与 RViz2 可以同时使用。两边都应以 `camera_init` 为 Fixed Frame，并优先观察世界点云 `/cloud_registered_1`。

**先做转弯小范围验收，再正式建图：**

1. 机器人静止至 `IMU Initial Done`。
2. 原地非常慢地左转 20–30°，停住，再回正。
3. 原地非常慢地右转 20–30°，停住，再回正。
4. 正常表现应是：机器人模型/`body` TF 转动，走廊和墙体仍固定在 `camera_init` 中。

**正式建图行走要点：**

- 速度慢（≤ 0.3 m/s）、转弯慢（≤ 0.2 rad/s），避免急转、急停和大幅摆动。
- 走遍所有未来要标 waypoint 的位置，每个门/走廊尽量从两个方向采集。
- 在关键位置停 3–5 秒，让局部 scan-to-map 匹配稳定后再转弯。
- 可以返回起点检查闭合误差，但**当前 FAST-LIO 没有全局回环/位姿图优化**；返回起点或走两遍不会自动改正已经写入的历史点云。
- 走廊几何退化时，尽量让扫描同时看到侧墙、门框、拐角等非平行结构，不要只在长直走廊中心快速旋转。


### 步骤 4：保存地图

**保存 2D 栅格图：**
```bash
docker exec -it g1_robot_fast_lio bash
source install/setup.bash
ros2 run nav2_map_server map_saver_cli \
     -t /accumulated_grid --free 0.196 --occ 0.65 \
     -f /botbrain_ws/src/g1_pkg/maps/floor1  # 与上面场景名一致
exit
```

**保存 3D 点云：**
```bash
docker exec g1_robot_fast_lio bash -c "kill -SIGINT \$(pgrep fastlio_mapping)"
# 自动保存到 mid360.yaml 指定的 map_file_path
```

**确认生成（PCD ≥ 1MB 才算正常）：**
```bash
ls -lh /data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/ | grep floor1
# 应有：floor1_scans.pcd（≥ 1MB）、floor1.pgm、floor1.yaml
```

**关闭保存开关**（防止后续误覆盖已校正的 PCD）：
```bash
# 改 mid360.yaml: pcd_save_en: false → build → 重启 fast_lio
```

### 步骤 5：PCD 地面校正（⚠️ 建图后必做！）

建图实时世界坐标 `camera_init` 的原点接近 MID360/内置 IMU 的启动位置，因此机器人站立时地面正常应在 **`z ≈ -1.247 m`**。这不是 FAST-LIO 外参；不要为了让地面变成 0 去修改 `extrinsic_T`。

保存完成后，再把 PCD 整体上移 1.247 m，使供 `open3d_loc` 使用的成品地图地面位于 `z ≈ 0`（参考项目 D-012 规范）：

```bash
docker exec -it g1_robot_fast_lio bash
source install/setup.bash
python3 /botbrain_ws/tools/mapping/shift_pcd_z.py \
    /botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd 1.247
exit
```

**验证校正效果**（脚本会输出平移前后对比）：

```text
z 1pct  -1.2470 -> +0.0000   ← 地面最低点应在 z≈0
z 5pct  -1.2400 -> +0.0070   ← 大部分地面应接近 z≈0
z med   -0.6235 -> +0.6235   ← 中位数上移是正常的，地图还包含墙壁/天花板
```


---

## 二、建图质量查看与判断 ⭐

建图是否成功不能靠肉眼看，必须用数据验证。以下是从参考项目 `g1_3d_nav_ros2` 移植过来的完整质量检查流程：

### 2.1 实时查看建图质量（建图过程中）

```bash
# G1 上实时看 grid_accumulator 地面平面估计
docker compose logs -f fast_lio | grep "ground plane"
```

**关注以下指标（这是未做 PCD 上移前的实时 `camera_init` 坐标）：**

| 指标 | 日志字段 | 正常范围 | 异常信号 |
|------|---------|---------|---------|
| **地面倾斜角** | `tilt=XX°` | **< 2°** | > 5° 说明地图严重倾斜，需先检查 IMU 轴向和初始化 |
| **地面高度** | `floor_z=X.XXXm` | 站立时稳定在约 **-1.247 m** | 持续变化或转弯时跳变 → 状态估计不稳定 |
| **帧数增长** | `frames=N` | 持续增长 | 停止增长 → 点云订阅或发布中断 |
| **地面点/障碍点** | `ground=N obs=N` | 持续增长 | 某类始终为 0 → 分类阈值或平面拟合异常 |
| **网格尺寸** | `grid=WxH` | 随行走区域扩大 | 不增长 → 世界点云没有累积到新区域 |
| **floor_z 范围** | `floor_z_range=[min,max]` | min、max 均应接近 -1.247 m，范围较窄 | 范围持续扩大 → 平面或 FAST-LIO 位姿不稳定 |

```bash
# 看完整 grid_accumulator 统计
docker compose logs -f fast_lio | grep "grid_accumulator"
# 输出示例: frames=342 ground=12045 obs=8932 grid=800x600
#          ground plane: z=+0.0001*x-0.0003*y-1.2470 tilt=0.02° floor_z_range=[-1.250, -1.242]m
```


### 2.2 ICP Fitness 验证（建图后最重要的量化指标！）

这是参考项目 `g1_3d_nav_ros2` 用来判断建图是否成功的金标准：

```bash
# 启动定位服务后用建好的地图做 ICP 匹配测试
cd /data/unitree/botbrain_ws
docker compose up fast_lio localization

# 持续监控 ICP fitness
docker compose logs -f localization | grep fitness
```

**判定标准（来自 g1_3d_nav_ros2 README）：**

| fitness 值 | 判定 | 行动 |
|-----------|------|------|
| **≥ 0.9** | ✅ 优秀 | 地图质量很好，可以放心导航 |
| **0.7 ~ 0.9** | ⚠️ 可用 | 可以导航，但建议优化（局部区域稀疏、退化或有盲区） |
| **0.5 ~ 0.7** | ⚠️ 勉强 | 部分区域匹配不良，有限区域可导航 |
| **< 0.5** | ❌ 不合格 | 建图失败，需要**重建** |

> ⚠️ **关键**：fitness 要**持续稳定**在阈值以上。如果 fitness 忽高忽低（如 0.3→0.8→0.2→0.7），说明地图局部有问题，某些区域匹配不到。

### 2.3 建图常见问题诊断速查表

| 现象 | 可视化表现 | 日志/话题表现 | 主要原因 | 解决方案 |
|------|-------------|---------------|---------|---------|
| **转弯时整片世界点云随机器人旋转** | Foxglove 在 `camera_init → camera_init` 下，`/cloud_registered_1` 中走廊也跟着转 | `/livox/imu_corrected` 无数据，或 FAST-LIO 配置仍订阅 `/livox/imu` | 倒装 MID360 的原始 IMU 未做 Y/Z 翻转，点云与 IMU 轴向不一致 | 启动 `imu_flip.py`，确认 `imu_topic: /livox/imu_corrected`，再按 ±20–30° 慢转验收 |
| **转弯伴随明显假平移/重影** | 机器人一转，墙体既旋转又横移 | `mid360.yaml` 中 `extrinsic_T.z=1.247` | 把传感器离地高度误当成 LiDAR–内置 IMU 外参，形成约 1.2 m 的虚假杠杆臂 | 恢复 `extrinsic_T: [-0.011, -0.02329, 0.04412]`；1.247 只用于栅格/PCD 高度处理 |
| **body 点云随机器人移动** | `/cloud_registered_body_1` 相对机器人几乎静止 | 话题 `frame_id=body` | 这是 body-frame 话题的正常定义 | 判断地图稳定性时改看 `/cloud_registered_1` |
| **地图倾斜** | 3D 点云侧看地面不水平 | `tilt > 5°` | IMU 轴向错误，或初始化时机器人未站稳 | 先核对 raw/corrected IMU 符号，再保持静止直到 `IMU Initial Done` 后重建 |
| **高度漂移** | 点云整体上下移动 | `floor_z` 持续变化 | IMU 初始化、振动、时间同步或噪声参数问题 | 先排除轴向/外参，再检查时间戳、机械固定和 IMU 数据稳定性 |
| **XY 漂移/返回起点不闭合** | 地图逐渐拉长，旧墙与新墙错开 | 无全局回环优化日志 | 当前 FAST-LIO 只有局部 scan-to-map；长直走廊会退化，累计误差不会自动回改 | 降速、增加拐角/门框等几何约束；返回起点只用于量误差，不能靠"走两遍"消除历史漂移 |
| **鬼影/重影** | 同一面墙出现多层影子 | 转弯阶段点云错位最明显 | 急转、上述 IMU/外参错误，或 LiDAR–IMU 时间偏差 | 先修正确定性配置，再慢转复测；若仍存在，记录 rosbag 检查时间同步 |
| **盲区/空洞** | 地图有大片未知区域 | `grid` 在该区域无覆盖 | 没走到或有效特征不足 | 驱动 G1 覆盖所有区域，在关键位置短暂停留 |
| **2D 栅格噪点** | 墙壁中间有随机黑白斑点 | N/A | 雷达噪点或行人经过 | 用下方 Map Editor 手动擦除 |

> **重要：当前 FAST-LIO 没有全局回环/位姿图优化。** 回到起点只能检查闭合误差，无法自动修正已经累计并写入的历史地图。导航阶段之所以看起来更"锁得住"，是因为 `open3d_loc` 会把实时点云持续对已有全局 PCD 做 ICP 重定位；这与建图阶段的局部 scan-to-map 不是同一层级的约束。


---

## 三、地图修正（Map Editor）⭐

建图后 `accumulated_grid.pgm` 经常需要手工修：擦除雷达噪点、补墙、画虚拟墙限制 nav2 路径、标记区域等。

> ⚠️ **修图流程：G1 上建图 → scp 到 workstation → 编辑修改 → scp 传回 G1。**
> Map Editor 是 ROS 1 noetic + RViz panel，只能在有显示器的 workstation 上跑，不能直接在 G1 上跑。

整套工具在 `tools/host_side/map_edit/` 中（已从 `g1_3d_nav_ros2` 移植）。

### 3.1 一次性准备（workstation 端，只做一次）

> ✅ **本机已完成**（2026-07-09）。镜像 `map_edit_rviz:latest` 已构建，容器 `map_edit_rviz` 已创建并运行中。
> 如果容器被删了需要重建，执行以下命令：

```bash
cd /home/aitech/Workspace/botbrain_project

# 构建镜像（需要 ROS 1 noetic 基础，约 15 分钟）
docker build -t map_edit_rviz:latest tools/host_side/map_edit

# 创建容器（挂载 maps 目录 + X11 转发）
docker run -d --name map_edit_rviz \
    -e DISPLAY="$DISPLAY" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "/home/aitech/Workspace/botbrain_project/botbrain_ws/src/g1_pkg/maps":/root/maps \
    map_edit_rviz:latest
```

**验证容器正常：**
```bash
docker ps --filter name=map_edit_rviz   # 确认 STATUS 为 Up
docker exec map_edit_rviz test -f /catkin_ws/devel/lib/libros_map_edit.so && echo "✅ 就绪"
```

> 容器跑的是 `sleep infinity`，以后每次修图只需 `start_map_edit.sh`，不用重建容器。

### 3.2 编辑流程

```
G1 出图  ──►  scp 到 workstation  ──►  RViz 编辑修改  ──►  scp 传回 G1
```

**Step 1 — 从 G1 拉地图到 workstation：**
```bash
# 在 workstation 上执行
cd /home/aitech/Workspace/botbrain_project
scp unitree@<G1_IP>:/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml} \
    botbrain_ws/src/g1_pkg/maps/

# 修正 yaml 中的 image 路径为相对路径（G1 的绝对路径 workstation 加载不到）
sed -i 's|^image:.*|image: floor1.pgm|' botbrain_ws/src/g1_pkg/maps/floor1.yaml
```

**Step 2 — 启动编辑器：**
```bash
cd /home/aitech/Workspace/botbrain_project
bash tools/host_side/map_edit/start_map_edit.sh /root/maps/floor1.yaml
```

RViz 弹出来后，左边是 **File Management** 面板（绿色 **Save All Files** 按钮），工具栏多了 4 个工具。

**Step 3 — 四种编辑工具：**

| 工具 | 用途 | 操作方式 |
|------|------|---------|
| **MapEraser** | 涂改栅格 | **左键**画黑（占据=墙壁）、**右键**画白（空闲=可通行），按住拖动连续涂 |
| **VirtualWall** | 画两点虚拟墙 | 左键点两次定两端、右键取消。限制 nav2 不进入某些区域 |
| **Region** | 圈多边形区域 | 左键点多边形顶点、双击闭合。标记房间/禁区 |
| **MapEdit** | 模式切换器 | 决定上面哪个工具激活 |

笔刷大小、墙的颜色宽度在右边 **Tool Properties** 面板调。

**常见修图操作：**
- **擦除雷达噪点**：MapEraser 右键（白色）涂掉墙壁中间的噪点
- **补缺墙**：MapEraser 左键（黑色）补上断掉的墙壁缺口
- **画虚拟墙**：VirtualWall 在不希望 G1 进入的区域画线（台阶边、玻璃墙前）
- **标禁区**：Region 圈出危险区域

**Step 4 — 保存：**

点左边绿色 **Save All Files** 按钮，在同目录写入4个文件：
- `floor1.yaml` — 配置
- `floor1.pgm` — 图像（带修改内容）
- `floor1.json` — 虚拟墙数据
- `floor1_region.json` — 区域数据

**Step 5 — 推回 G1：**

```bash
# ⚠️ 推回前必须修正 yaml！

cd /home/aitech/Workspace/botbrain_project

# 1. 编辑器保存时会丢掉 mode: trinary，必须加回来
grep -q '^mode:' botbrain_ws/src/g1_pkg/maps/floor1.yaml || \
    sed -i '2a mode: trinary' botbrain_ws/src/g1_pkg/maps/floor1.yaml

# 2. image 路径改回 G1 容器内的绝对路径
sed -i 's|^image:.*|image: /botbrain_ws/src/g1_pkg/maps/floor1.pgm|' \
    botbrain_ws/src/g1_pkg/maps/floor1.yaml

# 3. scp 传回 G1
scp botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml,json} \
    "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/
scp botbrain_ws/src/g1_pkg/maps/floor1_region.json \
    "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/ 2>/dev/null || true
```

---

## 四、多楼层建图与切换

### 4.1 多楼层建图

每个楼层独立建图，使用不同的场景名，建完后各自做 PCD 地面校正：

```bash
# === 1F 建图 ===
# mid360.yaml: map_file_path → floor1_scans.pcd
# ... 建图、保存、校正 ...
python3 /botbrain_ws/tools/mapping/shift_pcd_z.py \
    /botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd 1.247

# === 2F 建图（G1 搬到2楼后重新建） ===
# mid360.yaml: map_file_path → floor2_scans.pcd
# ... 建图、保存、校正 ...
python3 /botbrain_ws/tools/mapping/shift_pcd_z.py \
    /botbrain_ws/src/g1_pkg/maps/floor2_scans.pcd 1.247
```

> ⚠️ **每个楼层需要独立建图！** G1 没有多层激光 SLAM，不能自动识别楼层切换。到新楼层后必须重新建图。

### 4.2 切换地图（导航时用哪张）

修改 `localization_3d.launch.py` 中的默认值：

```bash
# 宿主机：/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/launch/localization_3d.launch.py
default_pcd_path  = os.path.join(workspace_dir, 'src', 'g1_pkg', 'maps', 'floor1_scans.pcd')
default_grid_yaml = os.path.join(workspace_dir, 'src', 'g1_pkg', 'maps', 'floor1.yaml')
```

```bash
cd /data/unitree/botbrain_ws
docker compose restart localization
# 确认新地图加载：看 fitness > 0.9
```

---

## 五、定位导航服务启动

### 5.1 启动定位

```bash
cd /data/unitree/botbrain_ws

# 终端1 启动基础服务
docker compose up bringup state_machine foxglove

# 终端2 启动定位（用已建好的地图）
docker compose up fast_lio localization
```

**初始位姿对齐：**
- 当前位置与建图起始位姿一致 → 无需操作
- 偏差 > 1m 或 > 90° → Foxglove 发送 `/initialpose` 指定机器人在地图上的位置
- localization 日志 `reg_result.fitness > 0.9` 即 ICP 匹配完成

### 5.2 启动导航

```bash
cd /data/unitree/botbrain_ws
docker compose up navigation   # 终端3

# 方式一：Foxglove 发送 /g1_robot/goal_pose 开始导航
# 方式二：Workstation RViz2（备用）
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/192.168.100.30:7448"]'
# 香港 G1：export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/192.168.37.204:7448"]'
ros2 daemon stop  >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
sleep 3
ros2 topic info /Odometry_loc | grep "Publisher count"
rviz2 -d /home/aitech/Workspace/botbrain_project/configs/g1_nav_loc_rviz2.rviz
```

### 5.3 点位记录与多点导航

```bash
docker exec -it g1_robot_bringup bash
source install/setup.bash

ros2 run bot_navigation waypoint_recorder.py record office   # 记录点位
ros2 run bot_navigation waypoint_recorder.py list            # 查看点位
ros2 run bot_navigation waypoint_navigator.py office1        # 单点导航
ros2 run bot_navigation waypoint_navigator.py kitchen office1 home --loop  # 多点循环
ros2 run bot_navigation localization_monitor.py              # 漂移监控
```

> 点位文件：`/data/unitree/botbrain_ws/botbrain_ws/src/bot_navigation/nav_waypoints.yaml`

### 5.4 服务启动延迟与就绪检查

| 服务 | 启动延迟 | 就绪标志 |
|------|---------|---------|
| `bringup`（雷达驱动） | 硬件握手 **5~10s** | `livox/lidar publish use livox custom format` |
| `fast_lio` | **sleep 25s** | `[MAP] frame=X feats_down=XX` |
| `localization` | **sleep 30s** | `reg_result.fitness > 0.9` |
| `navigation` | **sleep 30s** | Nav2 lifecycle 全部 active |

> bringup 刚起来时 fast_lio 打印 `No Effective Points!` 属正常，等雷达就绪后自动恢复。超过 30s 仍无点云再排查。

**启动就绪检查顺序（必须按序，否则必飘）：**
1. ✅ bringup 出现 `livox custom format` → 雷达就绪
2. ✅ fast_lio 出现 `[MAP] frame=X` → 里程计就绪
3. ⚠️ `target size: 0` 不会自动恢复 → Foxglove 发送 `/initialpose`
4. ✅ localization 出现 `fitness > 0.9` → ICP 收敛，定位可信
5. ✅ 再启动 navigation

**启动导航服务(想要开导航就需要开启建图定位)**
### 代码更新与重编译

#### ⚠️ 重要：必须 build 才能生效

> 本项目编译时**未使用 `--symlink-install`**，因此 `install/` 是独立副本，**不是** `src/` 的软链接。
>
> **所有对 `src/` 的修改（无论是 Python、YAML 还是 C++）都需要重新 build 才能生效。**
> 直接重启服务而不 build，运行的仍然是 `install/` 里的旧版本。

| 修改的文件类型 | 需要重编译 | 操作 |
|---|:---:|---|
| Python 脚本 (`.py`) | ✅ | **先 build 再重启** |
| Launch 文件 (`.launch.py`) | ✅ | **先 build 再重启** |
| 配置文件 (`.yaml` / `.json`) | ✅ | **先 build 再重启** |
| 地图文件 (`.pcd` / `.pgm`) | ❌ | 重启对应服务即可（直接读文件路径） |
| C++ 源码 (`.cpp` / `.hpp`) | ✅ | **先 build 再重启** |
| `CMakeLists.txt` / `package.xml` | ✅ | **先 build 再重启** |

#### 标准修改流程（所有代码改动）

> `docker compose up builder_base` 本质是执行 `colcon build --packages-select <所有包>`，
> **不是只起一个空容器**，它运行完会自动退出（`exited with code 0` = 编译成功）。
> `install/` 目录由 colcon 自动更新，**不要手动 cp**。

```bash
cd /data/unitree/botbrain_ws

# 步骤1：修改 src/ 下的源文件

# 步骤2：colcon build 更新 install/（等待 exited with code 0）
docker compose up builder_base

# 步骤3：重启受影响的服务（让进程重新加载 install/ 里的新文件）
docker compose stop fast_lio && docker compose up -d fast_lio
```

#### 只编译特定包（改动少时更快）

> `builder_base` 已包含 `fast_lio` 和 `g1_pkg`，下面命令仅编译这两个包，速度更快。

```bash
cd /data/unitree/botbrain_ws

docker compose run --rm builder_base bash -c \
  "source /opt/ros/humble/setup.bash && \
   cd /botbrain_ws && \
   colcon build --packages-select fast_lio g1_pkg \
   --cmake-args -DCMAKE_BUILD_TYPE=Release \
               -DOpen3D_DIR=/opt/open3d/lib/cmake/Open3D"

# 编译成功后重启服务
docker compose stop fast_lio && docker compose up -d fast_lio
```

#### 服务 → 源码包 → 完整操作流程

| 服务名 | 主要源码包 | 编译命令 | 重启命令 |
|---|---|---|---|
| `fast_lio` | `fast_lio`, `g1_pkg` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select fast_lio g1_pkg"` | `docker compose stop fast_lio && docker compose up -d fast_lio` |
| `localization` | `open3d_loc` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select open3d_loc"` | `docker compose stop localization && docker compose up -d localization` |
| `navigation` | `bot_navigation`, `g1_pkg` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select bot_navigation g1_pkg"` | `docker compose stop navigation && docker compose up -d navigation` |
| `bringup` | `bot_bringup`, `g1_pkg` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select bot_bringup g1_pkg"` | `docker compose stop bringup && docker compose up -d bringup` |
| `state_machine` | `bot_state_machine` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select bot_state_machine"` | `docker compose stop state_machine && docker compose up -d state_machine` |
| `yolo` | `bot_yolo` | `docker compose up builder_yolo` | `docker compose restart yolo` |

---

## 集成思路

对于需要集成到`botbrain`里的单模块项目可以用此思路

> 先在当前`botbrain`主机里使用已有的镜像开启容器，检查镜像里是否有适配待集成项目的运行依赖
> >* 可以先让ai在待集成的项目中编写一个环境依赖检查脚本，确定本机环境中或者未集成时的模块项目环境中，能正常运行脚本
> >
> >* 将脚本复制到在`botbrain/src` 下，确保容器里可以同步脚本，再开启`botbrain`里的容器运行脚本，查看容器镜像里是否有运行环境
> >
> >  >例如，目前机器人主机里有三个botbrain镜像:`botbotrobotics/botbrain:base` `botbotrobotics/botbrain:manipulation` `botbotrobotics/botbrain:yolo`  
> >  >
> >  >就可以开启对应镜像容器服务(在docker-compose.yaml查看服务名称) :`docker compose run --rm bringup bash` `docker compose run --rm yolo bash` `docker compose run --rm manipulation bash` 
> >  >
> >  >进入容器后运行`source install/setup.bash` 和环境检查脚本
> >
> >* 如果每个镜像都缺少大部分依赖则建议重新利用基础镜像构建新的依赖镜像,并在`docker-compose.yaml`里进行配置 ，例如`docker/Dockerfile.manipulation` 和`docker/Dockerfile.nav3d` 
>
> 一般都将单模块项目以功能包形式添加到`src`下，并在`docker-compose.yaml`里进行配置启动程序和镜像依赖

需要注意的是在集成时，是否会有话题冲突/不匹配/抢占的情况，例如后续要移植AT码校准和视觉按按键，两者都需要启动相机，可以考虑在`bot_state_machine`状态机上控制相机的开关，并且两者需要确定相同的话题名称和图像配置，这样就不会进行过多的争抢情况。还有对底盘运动的控制争抢，例如IMU控制旋转时，最后发送的话题是否与导航策略的一致，是否需要新加一个状态机控制运动优先级，或者就直接统一使用与导航一致的话题和lococlient。

```bash
请分析这个工程的各子工程内容，只分析定位建图功能，botbrain_project-main为主工程，g1_3d_nav_ros2 为副工程（包含了需要的定位建图模块功能），FAST_LIO_LOCALIZATION_HUMANOID 为副工程的原工程，现在我做了副工程的定位建图功能移植到main主工程，但是目前移植后的效果不理想，建图容易产生漂移，现在需要你来帮我重新移植，不过这次移植的是副工程的源工程，需要你把我移植的那部分全部换成源工程，但是最后的启动方式不变，还是使用docker compose启动。借于上次的移植，发现有很多问题，其一就是话题名称类，这次考虑定位建图不使用命名空间，以源工程默认即可；其二是启动的文件后，雷达数据类型等等不一致，需要改成启动bringup服务时，不启动雷达，雷达由fastlio服务启动。我需要你完整的替换，不保留原来main工程里的定位建图内容，目的是能稳定跑通代码，原先每次启动定位建图都需要启动bringup来启动雷达，而这次我需要由fastlio服务来启动雷达，或者将bringup启动的雷达数据类型和各种参数配置与FAST_LIO_LOCALIZATION_HUMANOID启动雷达时的各种配置保持一致，就可以直接使用bringup服务来启动。之前在main工程移植里修改过docker-compose.yaml、 src/fast_lio、 src/open3d_loc、 src/g1_pkg 的内容，所以现在的源工程内容与main工程里该内容是不一致的，需要你多加考虑，并且我是通过远程开发连接到G1机器人上，所以本机没有运行这些程序的环境，你只需要修改即可。
```

