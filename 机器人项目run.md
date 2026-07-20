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
cd /data/unitree/botbrain_ws/
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
#需要录制新的动作是两个的多动作线性回放,具体看/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/scripts/
./src/g1_pkg/scripts/replay_sequence.sh
```

### 手臂控制（笛卡尔坐标）

```bash
cd /data/unitree/botbrain_ws/
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

## 一、建图、保存与 PCD 校正

> 每套用于导航的地图至少包含以下 3 个文件，并且必须来自同一次建图：
>
> - `<场景名>_scans.pcd`：Open3D ICP 使用的 3D 地图。
> - `<场景名>.pgm`：Nav2 使用的 2D 占据栅格。
> - `<场景名>.yaml`：PGM 的分辨率、原点和阈值配置。
>
> 地图目录：`/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/`。以下以 `floor1` 为例。

### 步骤 0：停止旧服务并保护已有地图

```bash
cd /data/unitree/botbrain_ws
docker compose stop navigation localization fast_lio

if docker compose ps --services --filter status=running | \
     grep -Eq '^(localization|navigation)$'; then
  echo "ERROR: 建图时 localization/navigation 必须停止"
  exit 1
fi

# 可选：建图前备份当前活动地图
stamp=$(date +%Y%m%d_%H%M%S)
cp -a botbrain_ws/src/g1_pkg/maps \
      "botbrain_ws/src/g1_pkg/maps_backup_$stamp"

# 后续用此时间标记排除误把旧 PCD 当成本次保存结果
touch botbrain_ws/src/g1_pkg/maps/.floor1_mapping_started
```

建图期间不得启动 `localization` 和 `navigation`。它们分别运行 Open3D ICP、地图服务、Nav2 和全局 TF；同时建图会争抢 CPU，并把旧地图的 `/scan`、`/submap`、`/pcd_map` 和 TF 叠加到新地图上，视觉上很像 FAST-LIO 再次漂移。Compose 已把这两个服务放入 `navigation` profile，普通 `docker compose up -d` 不会自动启动它们；文档中的显式服务启动命令仍然有效。

### 步骤 1：配置 PCD 输出并开启保存

修改机器人宿主机上的：

`/data/unitree/botbrain_ws/botbrain_ws/src/fast_lio/config/mid360.yaml`

下面只列出需要修改或确认的键，不能用这段内容覆盖整个文件；未展示的已调优参数必须保持不变。

```yaml
/**:
  ros__parameters:
    map_file_path: "/botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd"

    common:
      imu_topic: "/livox/imu"
      imu_flip_yz: true
      imu_queue_depth: 2000
      lidar_queue_depth: 100

    mapping:
      extrinsic_est_en: false
      extrinsic_T: [-0.011, -0.02329, 0.04412]

    publish:
      map_en: false

    pcd_save:
      pcd_save_en: true
```

`1.247 m` 是机器人站立时传感器到地面的高度，不是 LiDAR 到内置 IMU 的外参。禁止把 `1.247` 写入 `extrinsic_T`。同时禁止在 `imu_flip_yz: true` 时再启动 `imu_flip.py`，否则 IMU 会被翻转两次。

修改 YAML 后必须重新编译，因为运行时读取的是 `install/` 中的副本：

```bash
cd /data/unitree/botbrain_ws
docker compose run --rm builder_base bash -lc '
  source /opt/ros/humble/setup.bash
  cd /botbrain_ws
  colcon build --packages-select fast_lio g1_pkg \
    --cmake-args -DCMAKE_BUILD_TYPE=Release
'
```

### 步骤 2：启动并检查传感器链路

```bash
cd /data/unitree/botbrain_ws

# 后台启动基础服务；重启 foxglove 使新的话题白名单生效
docker compose stop localization navigation foxglove
docker compose up -d bringup state_machine foxglove

# 重新创建，确保使用新 install 和新参数
docker compose stop fast_lio
docker compose rm -f fast_lio
docker compose up -d fast_lio

# 机器人必须保持静止，直到 IMU 初始化完成
docker compose logs -f fast_lio | \
  grep -E "IMU Initial|FAST-LIO input|FAST_LIO_PCD|FAST_LIO_TIMING|FAST_LIO_GUARD"
```

另开终端逐项检查，每条 `hz` 命令观察后按 `Ctrl+C`：

```bash
docker exec -it g1_robot_fast_lio bash
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
ros2 topic hz /livox/imu
ros2 topic info -v /livox/imu
ros2 topic hz /cloud_registered_1
ros2 topic hz /Odometry_loc
ros2 topic info -v /cloud_registered_1
ros2 topic info -v /Odometry_loc
exit
```

必须满足：

- 启动日志包含 `imu=/livox/imu flip_yz=true imu_q=2000 lidar_q=100 guard=true`。
- 启动日志包含 `[FAST_LIO_PCD] enabled=true path=<目标 PCD> interval=-1 laser_map=false`；这里显示的是 `install/` 中实际生效的配置。
- 看到 `IMU Initial Done` 后才能移动。
- `[FAST_LIO_TIMING] ok=true` 应稳定出现；通常 `imu_count>=5`、`max_gap<=0.02s`、扫描末端 IMU 差不超过 `0.03s`。
- `/cloud_registered_1` 和 `/Odometry_loc` 必须各自只有一个 publisher；多个 FAST-LIO 实例会直接形成重影和相互冲突的 TF。
- 偶发 guard rejected 可以接受，但坏帧不得写地图；后续应能看到 recovered 或恢复正常世界点云刷新。
- 出现 `output latched unhealthy` 后，FAST-LIO 已停止发布里程计、TF 和点云。不要继续移动或导航；建图时先保留日志并按需要保存已确认数据，然后重启 `fast_lio`。
- 开启保存时 `[MAP] frame=100, 200...` 与 `pcl_wait_save` 应持续增长。

### 步骤 3：小范围验收后正式建图

Foxglove/RViz2 设置：

- Fixed Frame：`camera_init`。
- Display/Follow Frame：`camera_init`。
- 判断地图稳定性只观察 `/cloud_registered_1`，点云 Decay 设为 `0`。
- `/cloud_registered_body_1` 随机器人运动是正常定义，不能用它判断世界地图是否漂移。
- 建图时只叠加 `/cloud_registered_1` 和 `/accumulated_grid`；关闭 `/Laser_map_1`、`/pcd_map`、`/scan`、`/scan2map`、`/submap` 以及 local/global costmap 图层。

`/Laser_map_1` 已在配置中关闭。旧实现每秒追加当前扫描并重新序列化全部历史点，消息会无限增大，而且独立定时器可能显示 guard 已拒绝的帧；它不参与当前 PCD 保存或栅格生成。

先做以下小范围测试：

1. `IMU Initial Done` 后继续静止约 30 秒。
2. 慢速左转 20～30 度，停 3 秒，再前进约 1 米。
3. 慢速右转 20～30 度，停 3 秒，再前进约 1 米。
4. 慢速完成一次 90 度转弯，确认墙体仍固定在 `camera_init` 中。
5. 若 rejected 后无法自行恢复，不要继续正式建图，先保存 timing/guard 日志排查。

正式建图建议线速度不超过 `0.3 m/s`、角速度不超过 `0.2 rad/s`。门框、拐角和未来 waypoint 区域尽量从两个方向采集，并在关键位置停留 3～5 秒。当前 FAST-LIO 没有全局回环，返回起点只能检查误差，不能自动修改已经写入的历史地图。

### 步骤 4：先保存 2D 栅格，再主动保存 PCD，最后停止 FAST-LIO

保存 2D 栅格快照：

```bash
docker exec -it g1_robot_fast_lio bash
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash

# 先停止机器人并等待最后一帧 2 Hz 栅格发布完成。
sleep 1
ros2 topic info /accumulated_grid
ros2 run nav2_map_server map_saver_cli \
  -t /accumulated_grid --free 0.196 --occ 0.65 \
  -f /botbrain_ws/src/g1_pkg/maps/floor1

# 确认节点实际启用了 PCD 保存，而且目标路径与本场景一致
ros2 param get /fast_lio pcd_save.pcd_save_en
ros2 param get /fast_lio map_file_path
ros2 service list | grep '^/map_save$'

# 机器人保持静止；保存会短暂停止实时回调。成功后不要再移动，立即验证并 stop
ros2 service call /map_save std_srvs/srv/Trigger '{}'
exit
```

先在机器人宿主机验证主动保存生成的文件。主动调用 `/map_save` 是正式保存路径，不能把唯一一次保存机会押在容器退出信号上：

```bash
maps=/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps
marker="$maps/.floor1_mapping_started"
test -f "$marker"
test -s "$maps/floor1_scans.pcd"
test "$maps/floor1_scans.pcd" -nt "$marker"
head -n 11 "$maps/floor1_scans.pcd" | \
  grep -E "^(FIELDS|WIDTH|HEIGHT|POINTS|DATA)"
```

只有服务返回 `success=true`、消息包含 `saved <点数> points to <目标文件>`，并且上面的文件检查通过，才继续停止 FAST-LIO。停止信号保存现在只是异常情况下的兜底；不要只杀节点后让 `restart: always` 重新拉起一个新建图进程。

```bash
cd /data/unitree/botbrain_ws
docker compose stop -t 180 fast_lio

# 查看主动保存和停止过程；不要在停止前查退出日志
docker compose logs --since 15m --timestamps fast_lio | \
  grep -E "FAST_LIO_PCD|saving [0-9]+ points|saved [0-9]+ points|PCD save skipped|PCL writeBinary|sending signal.*SIGINT|finished cleanly|failed to terminate|SIGKILL"
```

若 `/map_save` 不存在、参数显示 `false`，或者目标仍是旧的 `scans.pcd`，说明机器人运行的 `install/` 或容器还是旧版本。该次建图不能按正式流程验收；保存日志后停止旧进程，重新 build/recreate，再重新建图：

```bash
cd /data/unitree/botbrain_ws
sha256sum botbrain_ws/src/fast_lio/config/mid360.yaml \
          botbrain_ws/install/fast_lio/share/fast_lio/config/mid360.yaml
sha256sum botbrain_ws/src/g1_pkg/launch/fast_lio.launch.py \
          botbrain_ws/install/g1_pkg/share/g1_pkg/launch/fast_lio.launch.py

docker inspect g1_robot_fast_lio --format 'cmd={{json .Config.Cmd}} stop={{json .Config.StopSignal}}'
docker compose stop fast_lio
docker compose rm -f fast_lio

docker compose run --rm builder_base bash -lc '
  source /opt/ros/humble/setup.bash
  cd /botbrain_ws
  colcon build --packages-select fast_lio g1_pkg \
    --cmake-args -DCMAKE_BUILD_TYPE=Release
'
docker compose up -d --force-recreate fast_lio
```

确认三个成品文件都存在：

```bash
maps=/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps
ls -lh "$maps/floor1_scans.pcd" "$maps/floor1.pgm" "$maps/floor1.yaml"
head -n 11 "$maps/floor1_scans.pcd" | \
  grep -E "^(FIELDS|WIDTH|HEIGHT|POINTS|DATA)"
sed -n '1,10p' "$maps/floor1.yaml"
```

不要用“PCD 必须大于 1 MB”作为通过标准。小场景可能小于 1 MB，错误地图也可能很大；至少要确认 `POINTS` 非零、`DATA binary`、2D YAML 指向正确 PGM，并继续完成后面的可视化和 ICP 检查。

### 步骤 5：备份原始 PCD，并且只校正一次高度

实时 `camera_init` 原点位于启动时的 IMU 附近，因此未校正 PCD 的地面通常约为 `z=-1.247m`。Open3D 使用的成品 PCD 需要整体上移 `+1.247m`，使地面位于 `z≈0`。

校正脚本会原地覆盖文件且不是幂等操作。必须先保留原始文件，禁止对同一个成品 PCD 重复执行。

```bash
cd /data/unitree/botbrain_ws
maps=botbrain_ws/src/g1_pkg/maps

test ! -e "$maps/floor1_scans_raw.pcd" || {
  echo "floor1_scans_raw.pcd 已存在，请先确认该地图是否已经校正"
  exit 1
}
cp -a "$maps/floor1_scans.pcd" "$maps/floor1_scans_raw.pcd"

docker compose run --rm builder_base bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  python3 /botbrain_ws/install/g1_pkg/lib/g1_pkg/shift_pcd_z.py \
    /botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd 1.247
'
```

脚本输出的 `z 1pct/5pct/med` 只用于确认每个分位数都准确增加了 `1.247m`，不能单独用来识别地面。FAST-LIO 特征 PCD 中地面点占比可能低于 5%，动态物体或地下噪声也会改变分位数，因此它们不一定落在 `0m`。最终地面高度和地图质量必须结合 3D 可视化、初始位姿高度以及 Open3D ICP 判断。若平移量或可视化明显不符，恢复 `floor1_scans_raw.pcd` 后排查，不要再次叠加平移。

最后把 `mid360.yaml` 的 `pcd_save_en` 改为 `false` 并重新编译 `fast_lio g1_pkg`。定位/导航阶段保持保存关闭，既避免覆盖已校正 PCD，也不会启动建图用的 `grid_accumulator`。


---

## 二、建图质量检查

质量判断必须同时覆盖实时 LIO、2D 栅格、保存后的 PCD 和 Open3D ICP。任何单一截图、文件大小或 fitness 数值都不足以证明地图可用于导航。

### 2.1 建图过程中检查 grid_accumulator 与 FAST-LIO

```bash
cd /data/unitree/botbrain_ws
docker compose logs -f fast_lio | \
  grep -E "Validated ground plane|frames=|FAST_LIO_TIMING|FAST_LIO_GUARD"
```

当前代码的栅格统计字段包括：

- `frames/processed/classified`：应持续增长。
- `last_ground/last_obs/last_below/last_high/last_self`：表示最近一帧分类结果，不是累计点数。
- `grid=WxH free=... occ=... unknown=...`：覆盖新区域时尺寸和已观测格数量应增长。
- `floor_z`：未校正实时坐标中通常约为 `-1.247m`。
- `tilt`：正常室内地面通常小于 `2deg`；接近或超过 `5deg` 时应停止建图排查。
- `residual`：平面初始化门限当前为 `0.035m`，持续接近或超过门限说明地面拟合不稳定。
- `sync_pending/sync_dropped/invalid/plane_rejected`：少量瞬时增长可以接受，持续快速增长说明点云/里程计同步或平面质量异常。

FAST-LIO 同时应满足 `[FAST_LIO_TIMING] ok=true`。偶发 rejected 后能够恢复是保护逻辑正常工作；连续 rejected、`timing=false` 或世界点云长期停止刷新都不是合格建图状态。

### 2.2 保存后检查 PGM/YAML 和 PCD

```bash
maps=/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps

# 2D 文件和元数据
file "$maps/floor1.pgm"
sed -n '1,10p' "$maps/floor1.yaml"

# PCD 元数据
head -n 11 "$maps/floor1_scans.pcd" | \
  grep -E "^(FIELDS|SIZE|TYPE|COUNT|WIDTH|HEIGHT|POINTS|DATA)"
```

检查要点：

- YAML 的 `image` 应指向 `floor1.pgm`，`resolution` 应为 `0.05`，`origin` 必须保留 map_saver 输出值。
- `mode: trinary`、`negate: 0`、`occupied_thresh: 0.65`、`free_thresh: 0.196` 应存在。
- PCD 必须为 `DATA binary` 且 `POINTS` 非零。
- PCD 校正后的地面应约为 `z=0`；2D 地图不做任何 Z 平移。
- 在 Foxglove/Open3D 地图显示中检查墙体是否重影、倾斜或大面积缺失。

### 2.3 使用成品地图做 Open3D ICP 验收

导航前先确认 `mid360.yaml` 已设为 `pcd_save_en: false` 并完成编译。定位服务现在只需要一个场景名，并自动加载同目录中的 `<scene>_scans.pcd` 和 `<scene>.yaml`；YAML 再加载 `<scene>.pgm`。标准流程不再创建或更新 `scans.pcd`、`accumulated.yaml` 两个符号链接。

以下继续以 `floor1` 为例，在启动服务前直接检查这套三文件：

```bash
scene=floor1
maps=/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps
pcd="$maps/${scene}_scans.pcd"
yaml="$maps/${scene}.yaml"
pgm="$maps/${scene}.pgm"

# 三个文件必须存在且非空
printf 'SCENE: %s\nPCD  : %s\nYAML : %s\nPGM  : %s\n' \
  "$scene" "$pcd" "$yaml" "$pgm"
test -s "$pcd" && test -s "$yaml" && test -s "$pgm" || {
  echo "ERROR: $scene 的 PCD/YAML/PGM 缺失或为空"; exit 1;
}

# YAML 的 image 必须最终解析到同一场景的 PGM
image=$(sed -n 's/^[[:space:]]*image:[[:space:]]*//p' "$yaml" | head -n 1)
image=${image#\"}; image=${image%\"}; image=${image#\'}; image=${image%\'}
case "$image" in
  /*) image_path=$image ;;
  *)  image_path="$(dirname "$yaml")/$image" ;;
esac
test "$(realpath -e "$image_path")" = "$(realpath -e "$pgm")" || {
  echo "ERROR: $yaml 的 image=$image，不是 ${scene}.pgm"; exit 1;
}

head -n 11 "$pcd" | grep -E "^(FIELDS|WIDTH|HEIGHT|POINTS|DATA)"
echo "Map triplet check passed: $scene"
```

场景名只能包含英文字母、数字、下划线和连字符，并且第一个字符必须是字母或数字，例如 `ug`、`floor1`、`floor4`。`localization_3d.launch.py` 启动时会再次硬校验 PCD、YAML 和 PGM；任一文件不存在、YAML 无法解析、`image` 指错文件或三者场景名不一致时，localization 会直接启动失败，不得绕过校验进入导航。上面的启动前命令还会额外拦截空文件。

定位/导航阶段的 Foxglove 设置与建图阶段不同：

- Fixed Frame：`map`。
- Display/Follow Frame：`map` 或 `g1_robot/base_footprint`。
- 只用 `/pcd_map`、`/cloud_registered_1` 和 `/map` 检查对齐，点云 Decay 设为 `0`。
- 暂时关闭 `/cloud_registered_body_1`、`/cloud_effected_1`、`/scan`、`/scan2map` 和 `/submap`，避免不同用途的点云叠在一起。

`camera_init` 只用于检查 FAST-LIO 自身建图是否稳定。导航时若仍以 `camera_init` 为 Fixed Frame，Foxglove 的 2D 位姿工具会把 `/initialpose` 标成 `camera_init`，定位节点将拒绝它；而启动时一次性发布的 `/pcd_map` 也可能因旧时间戳显示在错误高度，看起来像实时点云整体位于地图下方。

然后重新创建定位服务：

```bash
cd /data/unitree/botbrain_ws
scene=floor1
docker compose up -d bringup state_machine foxglove
docker compose stop navigation localization fast_lio
docker compose rm -f localization fast_lio
docker compose up -d fast_lio
MAP_SCENE="$scene" docker compose --profile navigation \
  up -d --force-recreate localization

docker compose logs -f localization | \
  grep -E "Registered cloud|Planar base TF|Map/odom height|Map/odom roll/pitch|ICP 4.00 Hz|Global initialization|Prepared .*FPFH|Global candidate|LocalizationInitialize|localization initialization succeeded|Localization ready|ICP: accepted|Manual relocalization|ignoring /initialpose|Rejecting|Skipping ICP|Waiting for odometry history|Holding"
```

先确认定位节点已加载新参数：

```text
Map/odom height constraint: enabled=true z=1.247 m
Map/odom roll/pitch constraint: enabled=true
Planar base TF: enabled=true odom -> g1_robot/base_footprint height=1.247 m
ICP 4.00 Hz (250.0 ms), cloud_queue=1, odom_history=30, ... stamp_skew<=0.030s ...
```

不论机器人是否在建图起点，都先让定位节点使用当前局部点云对完整 PCD 执行 FPFH/RANSAC 全局初始化。正常顺序是：

```text
Global initialization: enabled=true ... confirmations=3 scan_window=3
Prepared ... map points for FPFH global initialization
Global candidate seed=... map->odom=(...) RANSAC=... fitness=... rmse=...
LocalizationInitialize: holding consistent global candidate (1/3 ... 3/3) ...
Global localization initialization succeeded: ...
Localization ready: verified map->odom is now available
```

只有最后的 `Localization ready` 出现后，经验证的 `map -> odom` 才对导航可用。启动时 `/localization_ready` 为 `false`，初始化通过后才以 transient-local QoS 发布 `true`：

```bash
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic echo --once --qos-durability transient_local \
    --qos-reliability reliable /localization_ready
'
```

机器人启动位置不在建图起点并不是立即手工发送 `/initialpose` 的理由。先保持机器人静止，让全局候选完成 `3/3` 确认。只有日志长时间反复出现 `did not produce a valid FPFH/RANSAC candidate`、`rejecting global candidate` 或始终无法累积到 `3/3` 时，才通过 Foxglove `/initialpose` 给出实际位置作为失败回退。发送后必须看到：

```text
Manual relocalization applied: requested map->base=(...), map->odom=(...)
```

随后必须继续看到：

```text
Local localization initialization succeeded
Localization ready: verified map->odom is now available
ICP: accepted=true fitness=... rmse=... correction=... map_odom_z=1.247 map_odom_rp=0.00/0.00 deg ...
```

`/Odometry_loc`、`/g1_robot/odom`、`/localization_3d` 和已有 `map -> odom` TF 都不是可以反馈为自动 `/initialpose` 的外部绝对位姿：前两者是相对里程计，后两者是定位结果本身，反馈会形成循环确认。自动启动位置应由上述 PCD 全局特征匹配解决。

若日志显示 `ignoring /initialpose in frame 'camera_init'` 或 `Rejecting initial pose in frame 'camera_init'`，说明 Foxglove Fixed Frame 仍设置错误，应改成 `map` 后重新发送。前者来自 `initialpose_z_fix`，消息会在到达 C++ 定位节点之前被拒绝。

成品 PCD 已上移 `+1.247m` 时，运行中的高度关系必须满足：

```bash
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic echo --once /odom2map --field pose.pose.position
  timeout 3 ros2 run tf2_ros tf2_echo map camera_init || true
  timeout 3 ros2 run tf2_ros tf2_echo map g1_robot/base_footprint || true
'
```

- `/odom2map` 的 `z` 应稳定约为 `+1.247`。
- `map -> camera_init` 的 Translation Z 应稳定约为 `+1.247`。
- `map -> g1_robot/base_footprint` 的 Z 应接近 `0`，Roll/Pitch 应接近 `0`；该 TF 由 FAST-LIO 里程计动态投影为平面帧。
- 日志中的 `map_odom_z=1.247` 应保持不变。
- 日志中的 `map_odom_rp=0.00/0.00 deg` 应保持接近零，不允许 ICP 把走廊退化转换成地图倾斜。
- 不应再持续出现接近 `0.10s` 的 cloud/odometry mismatch；代码会从短 odom 历史中按点云时间戳查找同帧位姿，30ms 门限不得放宽。

当前实际接收条件是 `fitness > 0.50`、`rmse <= 0.30m`，并同时通过点数、时间戳和 correction 门限。一般可参考：

| 现象 | 判断 |
|---|---|
| `accepted=true` 持续稳定，fitness 通常高于 0.7，RMSE 和 correction 较小 | 地图匹配质量较好，可继续转弯验收 |
| fitness 在 0.5～0.7 附近且不同区域波动明显 | 勉强可用，应检查 PCD 稀疏、动态人物和走廊退化 |
| 经常 `Rejecting ICP quality/jump` 或 stamp mismatch | 不应启动导航，先排查地图、时序或初始位姿 |
| fitness 看似较高但沿长走廊持续慢漂 | 几何弱可观测，不能靠放宽阈值解决 |

最终还要按“静止、直行、左右 90 度转弯、停 3 秒、再前进”的路线验证。只有 bad ICP 被拒绝、后续能够恢复 accepted，且机器人仍与 2D/3D 地图对齐，才算通过。

### 2.4 建图常见问题诊断速查表

| 现象 | 可视化表现 | 日志/话题表现 | 主要原因 | 解决方案 |
|------|-------------|---------------|---------|---------|
| **转弯时整片世界点云随机器人旋转** | Foxglove 在 `camera_init → camera_init` 下，`/cloud_registered_1` 中走廊也跟着转 | FAST-LIO 启动日志显示 `flip_yz=false`，或误启了 Python+C++ 双重翻转 | 倒装 MID360 的 IMU 轴向修正未生效或被执行两次 | 确认 `imu_topic: /livox/imu`、`imu_flip_yz: true`，并确保没有启动 `imu_flip.py` |
| **转弯伴随明显假平移/重影** | 机器人一转，墙体既旋转又横移 | `mid360.yaml` 中 `extrinsic_T.z=1.247` | 把传感器离地高度误当成 LiDAR–内置 IMU 外参，形成约 1.2 m 的虚假杠杆臂 | 恢复 `extrinsic_T: [-0.011, -0.02329, 0.04412]`；1.247 只用于栅格/PCD 高度处理 |
| **body 点云随机器人移动** | `/cloud_registered_body_1` 相对机器人几乎静止 | 话题 `frame_id=body` | 这是 body-frame 话题的正常定义 | 判断地图稳定性时改看 `/cloud_registered_1` |
| **地图倾斜** | 3D 点云侧看地面不水平 | `tilt > 5°` | IMU 轴向错误，或初始化时机器人未站稳 | 先核对 raw/corrected IMU 符号，再保持静止直到 `IMU Initial Done` 后重建 |
| **高度漂移** | 点云整体上下移动 | `floor_z` 持续变化 | IMU 初始化、振动、时间同步或噪声参数问题 | 先排除轴向/外参，再检查时间戳、机械固定和 IMU 数据稳定性 |
| **XY 漂移/返回起点不闭合** | 地图逐渐拉长，旧墙与新墙错开 | 无全局回环优化日志 | 当前 FAST-LIO 只有局部 scan-to-map；长直走廊会退化，累计误差不会自动回改 | 降速、增加拐角/门框等几何约束；返回起点只用于量误差，不能靠"走两遍"消除历史漂移 |
| **转弯稳定后再次移动突然不可恢复漂移** | 停住时短暂稳定，一起步地图/机器人突然跳飞 | `[FAST_LIO_TIMING]` 显示 IMU 数量少或 gap 大；`[FAST_LIO_GUARD]` 连续 rejected | 转弯期间 IMU 丢样/去畸变下降；旧版会持续发布未约束的纯 IMU 轨迹 | 检查 QoS/队列/timing；恢复阶段允许不少于 60 个高质量匹配点。超过短暂桥接帧数后停止 odom/TF，连续 30 帧仍失败则 `output latched unhealthy`，必须重启 FAST-LIO |
| **导航快速转弯后 ICP 跳飞** | map→odom 瞬间发生大平移或大旋转 | 日志出现 `Rejecting ICP jump/quality`，或旧版同一帧被重复确认 | 旧实现频率单位反了、可重复处理陈旧点云、`/initialpose` 方向错误且缺少并发版本保护 | 使用真实 4 Hz、scan generation 去重、两份不同窗口确认、1 m/15° gate、正确 `map_T_odom` 和 stale ICP 丢弃 |
| **鬼影/重影** | 同一面墙出现多层影子 | 转弯阶段点云错位最明显 | 急转、上述 IMU/外参错误，或 LiDAR–IMU 时间偏差 | 先修正确定性配置，再慢转复测；若仍存在，记录 rosbag 检查时间同步 |
| **盲区/空洞** | 地图有大片未知区域 | `grid` 在该区域无覆盖 | 没走到或有效特征不足 | 驱动 G1 覆盖所有区域，在关键位置短暂停留 |
| **2D 栅格噪点** | 墙壁中间有随机黑白斑点 | N/A | 雷达噪点或行人经过 | 用下方 Map Editor 手动擦除 |

> **重要：当前 FAST-LIO 没有全局回环/位姿图优化。** 回到起点只能检查闭合误差，无法自动修正已经累计并写入的历史地图。导航阶段之所以看起来更"锁得住"，是因为 `open3d_loc` 会把实时点云持续对已有全局 PCD 做 ICP 重定位；这与建图阶段的局部 scan-to-map 不是同一层级的约束。


---

## 三、地图修正（Map Editor）⭐

建图后的 `<场景名>.pgm` 可以手工清除孤立噪点、补墙，或直接画入不允许 Nav2 穿越的占据区域。

> ⚠️ **修图流程：G1 上建图 → scp 到 workstation → 编辑修改 → scp 传回 G1。**
> Map Editor 是 ROS 1 noetic + RViz panel，只能在有显示器的 workstation 上跑，不能直接在 G1 上跑。
>
> ⚠️ `VirtualWall` 和 `Region` 当前只保存 JSON 元数据，主工程没有 Nav2 costmap layer 读取这些 JSON。台阶、玻璃墙等安全边界必须使用 MapEraser 直接画成 PGM 中的黑色占据栅格。

整套工具在 `tools/host_side/map_edit/` 中（已从 `g1_3d_nav_ros2` 移植）。

### 3.1 一次性准备（workstation 端，只做一次）

Map Editor 源码有改动时必须重新构建镜像并重建容器；现有容器不会自动获得宿主机源码修改。

```bash
cd /home/aitech/Workspace/botbrain_project

docker build -t map_edit_rviz:latest tools/host_side/map_edit

docker rm -f map_edit_rviz 2>/dev/null || true
docker run -d --name map_edit_rviz \
    -e DISPLAY="$DISPLAY" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "/home/aitech/Workspace/botbrain_project/botbrain_ws/src/g1_pkg/maps":/root/maps \
    map_edit_rviz:latest
```

验证：

```bash
docker ps --filter name=map_edit_rviz   # 确认 STATUS 为 Up
docker exec map_edit_rviz test -f /catkin_ws/devel/lib/libros_map_edit.so && echo "ready"
```

如果 Map Editor 源码没有变化，之后每次修图只需运行 `start_map_edit.sh`，不用重建容器。

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

# 保存编辑前备份
stamp=$(date +%Y%m%d_%H%M%S)
mkdir -p "botbrain_ws/src/g1_pkg/maps/edit_backup_$stamp"
cp -a botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml} \
      "botbrain_ws/src/g1_pkg/maps/edit_backup_$stamp/"

# 统一使用可移植的相对路径。map_server 会相对 YAML 所在目录解析它。
sed -i 's|^image:.*|image: floor1.pgm|' botbrain_ws/src/g1_pkg/maps/floor1.yaml
```

**Step 2 — 启动编辑器：**
```bash
cd /home/aitech/Workspace/botbrain_project
bash tools/host_side/map_edit/start_map_edit.sh /root/maps/floor1.yaml
```

RViz 弹出来后，左边是 **File Management** 面板（绿色 **Save All Files** 按钮），工具栏多了 4 个工具。

> 启动命令会一直占用当前终端；完成修图并关闭 RViz 后，在终端按 `Ctrl-C` 结束 `roslaunch`，这是正常现象。脚本默认使用 Mesa 软件渲染，避免容器没有映射 `/dev/dri` 时 RViz 因 OpenGL 段错误闪退，并会隐藏不影响功能的 ROS Noetic 停止维护提醒；这些修复都不需要重建 Docker 镜像。

**Step 3 — 四种编辑工具：**

| 工具 | 用途 | 操作方式 |
|------|------|---------|
| **MapEraser** | 涂改栅格 | **左键**画黑（占据=墙壁）、**右键**画白（空闲=可通行），按住拖动连续涂 |
| **VirtualWall** | 保存两点线段元数据 | 左键点两次定两端、右键取消；当前不会影响 Nav2 |
| **Region** | 保存多边形区域元数据 | 左键添加顶点、**右键闭合**；当前不会影响 Nav2 |
| **MapEdit** | 模式切换器 | 决定上面哪个工具激活 |

笔刷大小、墙的颜色宽度在右边 **Tool Properties** 面板调。

**常见修图操作：**
- **擦除雷达噪点**：MapEraser 右键（白色）涂掉墙壁中间的噪点
- **补缺墙**：MapEraser 左键（黑色）补上断掉的墙壁缺口
- **增加安全边界**：使用 MapEraser 左键直接在 PGM 中画黑线；不要只保存 VirtualWall JSON
- **保留区域备注**：Region 可以保存区域元数据，但不会自动成为禁区

**Step 4 — 保存：**

点左边绿色 **Save All Files** 按钮，在同目录写入4个文件：
- `floor1.yaml` — 配置
- `floor1.pgm` — 图像（带修改内容）
- `floor1.json` — VirtualWall 元数据，仅供编辑器再次打开
- `floor1_region.json` — Region 元数据，仅供编辑器再次打开

Map Editor 会保留 `resolution` 和 `origin`，但保存的 YAML 不包含 `mode`，因此上传前必须恢复 `mode: trinary`。

**Step 5 — 修复 YAML 并重新打开验证：**

```bash
cd /home/aitech/Workspace/botbrain_project

# image 保持相对路径
sed -i 's|^image:.*|image: floor1.pgm|' \
  botbrain_ws/src/g1_pkg/maps/floor1.yaml

# 编辑器不写 mode；不存在时补回
grep -q '^mode:' botbrain_ws/src/g1_pkg/maps/floor1.yaml || \
  sed -i '/^image:/a mode: trinary' botbrain_ws/src/g1_pkg/maps/floor1.yaml

sed -n '1,10p' botbrain_ws/src/g1_pkg/maps/floor1.yaml
head -n 4 botbrain_ws/src/g1_pkg/maps/floor1.pgm

# 关闭旧 RViz 后重新打开保存后的文件，检查没有上下镜像、原点移动或编辑丢失
bash tools/host_side/map_edit/start_map_edit.sh /root/maps/floor1.yaml
```

重新打开后应检查：地图方向与修改前一致；墙体没有上下镜像；已擦除和补画区域存在；`resolution` 与 `origin` 没有改变。

**Step 6 — 推回 G1 并重载 map server：**

```bash
cd /home/aitech/Workspace/botbrain_project

# Nav2 实际只需要 PGM/YAML
scp botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml} \
    "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/

# JSON 仅在需要保留编辑器元数据时上传
scp botbrain_ws/src/g1_pkg/maps/floor1.json \
    "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/ \
    2>/dev/null || true
scp botbrain_ws/src/g1_pkg/maps/floor1_region.json \
    "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/ 2>/dev/null || true
```

PGM/YAML 是运行时直接读取的地图文件，不需要重新 build，但已经运行的 map server 不会自动检测磁盘变化。回到机器人执行：

```bash
cd /data/unitree/botbrain_ws
scene=floor1

# 先重新执行 2.3 的三文件检查。无需修改任何符号链接。
docker compose stop navigation localization
docker compose up -d fast_lio
MAP_SCENE="$scene" docker compose --profile navigation \
  up -d --force-recreate localization

# 先确认加载修后的地图和新定位参数
docker compose logs -f localization | \
  grep -E "read map|Global initialization|Global candidate|localization initialization succeeded|Localization ready|Map/odom height|ICP 4.00 Hz|ICP: accepted|Manual relocalization|ignoring /initialpose|Rejecting|Skipping ICP|Waiting for odometry history"
```

重启后将 Foxglove Fixed Frame 设为 `map`。先等待 FPFH/RANSAC 全局初始化和 `/localization_ready=true`；只有全局初始化持续失败时才发送 `/initialpose` 回退，并确认 `Manual relocalization applied`。然后重新执行 **2.3 使用成品地图做 Open3D ICP 验收** 中的 Z/TF、时间戳和连续 accepted 检查，全部通过后才能启动 navigation。

---

## 四、多楼层建图与切换

### 4.1 多楼层建图

每个楼层必须独立建图、独立保存 PCD/PGM/YAML，并分别只做一次 PCD 高度校正。场景数量没有固定上限，11 层就维护 11 套同名三文件。例如：

```text
# UG
ug_scans_raw.pcd  # 未校正备份，不参与定位选择
ug_scans.pcd      # 已校正成品
ug.pgm
ug.yaml

# 4F
floor4_scans_raw.pcd
floor4_scans.pcd
floor4.pgm
floor4.yaml
```

每个 YAML 的 `image` 必须指向同场景 PGM，例如 `ug.yaml` 写 `image: ug.pgm`，`floor4.yaml` 写 `image: floor4.pgm`。`*_scans_raw.pcd` 只是高度校正前的备份，不可作为导航地图。

每次建新楼层前，仍必须按“步骤 1”把 FAST-LIO 的 `map_file_path` 显式改成目标 `<scene>_scans.pcd`，例如 4F 使用 `/botbrain_ws/src/g1_pkg/maps/floor4_scans.pcd`。导航切图不再依赖软链接，不代表建图保存路径可以省略；禁止继续写入通用 `scans.pcd` 或覆盖 UG 的成品 PCD。

> **每个楼层需要独立建图。** G1 没有多层激光 SLAM，不能自动识别楼层切换。到新楼层后必须选择对应场景；只有该楼层还没有地图时才需要重新建图。

### 4.2 切换地图（导航时用哪张）

标准切图接口只有一个：`MAP_SCENE=<场景名>`。例如 `MAP_SCENE=ug` 自动选择 `ug_scans.pcd + ug.yaml + ug.pgm`，`MAP_SCENE=floor4` 自动选择 `floor4_scans.pcd + floor4.yaml + floor4.pgm`。不需要软链接、修改 launch 或重新 build。

首次使用 UG，或者机器人到达 4F 后切换到 `floor4`，都执行同一套流程。下面把 `floor4` 换成目标场景即可：

```bash
cd /data/unitree/botbrain_ws
export MAP_SCENE=floor4

# 导航模式严禁保存 PCD；source 和 install 都必须已恢复为 false
for cfg in \
  botbrain_ws/src/fast_lio/config/mid360.yaml \
  botbrain_ws/install/fast_lio/share/fast_lio/config/mid360.yaml; do
  grep -Eq '^[[:space:]]*pcd_save_en:[[:space:]]*false[[:space:]]*$' "$cfg" || {
    echo "ERROR: $cfg 未设置 pcd_save_en: false"; exit 1;
  }
done
if docker compose ps --services --filter status=running | grep -qx fast_lio; then
  docker compose exec -T fast_lio bash -lc '
    source /opt/ros/humble/setup.bash
    source /botbrain_ws/install/setup.bash
    ros2 param get /fast_lio pcd_save.pcd_save_en
  ' | grep -qi false || {
    echo "ERROR: 当前 FAST-LIO 仍启用了 PCD 保存，禁止切层重启"; exit 1;
  }
fi

# 先执行 2.3 的三文件检查，把 scene 设为当前 MAP_SCENE
scene="$MAP_SCENE"
maps=botbrain_ws/src/g1_pkg/maps
pcd="$maps/${scene}_scans.pcd"
yaml="$maps/${scene}.yaml"
pgm="$maps/${scene}.pgm"
test -s "$pcd" && test -s "$yaml" && test -s "$pgm" || {
    echo "ERROR: $scene 的地图三文件缺失或为空"; exit 1;
  }
image=$(sed -n 's/^[[:space:]]*image:[[:space:]]*//p' "$yaml" | head -n 1)
image=${image#\"}; image=${image%\"}; image=${image#\'}; image=${image%\'}
case "$image" in
  /*) image_path=$image ;;
  *)  image_path="$(dirname "$yaml")/$image" ;;
esac
test "$(realpath -e "$image_path")" = "$(realpath -e "$pgm")" || {
  echo "ERROR: $yaml 的 image=$image，不是 ${scene}.pgm"; exit 1;
}

# 机器人必须已到达目标楼层、停稳且没有活动导航目标，禁止运动中热切图。
# 若当前仍有目标，先调用 /g1_robot/cancel_nav2_goal 并确认机器人停稳。
docker compose stop navigation localization fast_lio
docker compose rm -f localization fast_lio

# 跨层后必须重置 FAST-LIO 的 camera_init/odom 高度基准
docker compose up -d --force-recreate fast_lio
docker compose logs -f fast_lio | \
  grep -E "IMU Initial Done|FAST_LIO_TIMING|FAST_LIO_GUARD"

# 看到 IMU Initial Done 且 timing/点云稳定后 Ctrl+C，再确认两路数据持续发布
docker exec -it g1_robot_fast_lio bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  timeout 5 ros2 topic hz /Odometry_loc || true
  timeout 5 ros2 topic hz /cloud_registered_1 || true
'

# --force-recreate 很重要：restart 不会用新场景重建容器命令
docker compose --profile navigation up -d --force-recreate localization

# 查看容器创建时实际固化的场景
docker inspect g1_robot_localization \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^MAP_SCENE='

# localization 先 sleep 30s；等待场景文件、ready 和 accepted 均通过后 Ctrl+C
docker compose logs -f localization | \
  grep -E "Map selection:|Global localization initialization succeeded|Localization ready|ICP: accepted|ERROR|FATAL"

# 再确认节点最终加载的两个入口文件
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 param get /global_localization_node path_map
  ros2 param get /map_server yaml_filename
'

# 完成 2.3 的 ICP/TF 验收后，最后启动新的 navigation
docker compose --profile navigation up -d --force-recreate navigation
```

Shell 和项目 `.env` 都没有设置 `MAP_SCENE` 时默认使用 `ug`。上面的 `export` 只对当前终端有效；换终端或机器人重启后应再次设置。若希望机器人项目长期固定某层，可在 `/data/unitree/botbrain_ws/.env` 中新增或更新唯一一条当前选择，例如 `MAP_SCENE=floor4`，同时保留该文件中的其他变量。之后 Compose 会自动读取它。无论采用哪种方式，凡是执行包含 `localization` 的 `docker compose up`，都必须保证 `MAP_SCENE` 仍是目标楼层，否则默认值可能把容器重新创建为 `ug`。

`docker compose restart localization` 只重启旧容器，不会切换地图。跨楼层必须遵守“停止 navigation/localization/fast_lio -> 在目标层重建 FAST-LIO -> 等待 IMU/点云稳定 -> 用 `MAP_SCENE` 重建 localization -> 等待定位验收 -> 重建 navigation”的顺序。

跨楼层时还必须重建 FAST-LIO。当前定位固定 `map_odom_z=1.247`，前提是 FAST-LIO 的 `camera_init` 在当前楼层重新建立；若乘电梯时让 FAST-LIO 连续运行，其 odom 会保留楼层高度差，目标层地面为 `z=0` 的 PCD 将无法可靠配准。不要通过解锁 Z 来绕过这一约束。同一楼层只替换修订后的 PGM/YAML/PCD 时，可以保留 FAST-LIO，只重建 localization。

禁止只调用 `map_server/load_map` 来切层。该服务只会更换 2D YAML/PGM，Open3D 定位仍会使用启动时加载的旧楼层 PCD，形成危险的 2D/3D 混图。

当前 `bot_navigation/nav_waypoints.yaml` 仍由所有楼层共享，`MAP_SCENE` 只选择 PCD/YAML/PGM，不会自动筛选 waypoint。在实现按场景自动分文件和硬校验前，点位名称必须带楼层前缀，例如 `ug_home`、`floor4_office`；切层后不得调用上一楼层的点位。

这套机制支持“每层独立导航 + 机器人停稳后切换场景”，不表示 Nav2 能跨 11 层生成一条连续路径，也不会自动识别机器人所在楼层。真正的跨层任务必须由上层状态机拆分为：当前层导航到电梯点 -> 执行乘梯动作 -> 到目标层后重建 FAST-LIO/定位 -> 使用目标层 waypoint 继续导航。

`localization_3d.launch.py` 仍支持显式的 `map_file`、`grid_map_file`，仅用于旧命名地图兼容或临时诊断。两个路径必须一起覆盖，且仍会执行同场景三文件硬校验。该前台命令必须在包含 ROS/Open3D 环境的 localization 容器中运行；它不是日常切层方式：

```bash
cd /data/unitree/botbrain_ws
docker compose stop navigation localization
docker compose run --rm localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  exec ros2 launch g1_pkg localization_3d.launch.py \
    map_file:=/botbrain_ws/src/g1_pkg/maps/floor1_scans.pcd \
    grid_map_file:=/botbrain_ws/src/g1_pkg/maps/floor1.yaml
'
```

不得把一个楼层的 PCD 与另一个楼层的 YAML/PGM 混用。切换后必须重新完成三文件配对检查、自动全局初始化和 ICP accepted 验收；`/initialpose` 仅用于自动初始化失败的回退。

---

## 五、定位导航服务启动

### 5.1 启动定位

```bash
cd /data/unitree/botbrain_ws
export MAP_SCENE=ug  # 改为机器人当前所在楼层，例如 floor4

# 导航前确认 mid360.yaml 中 pcd_save_en: false。本次定位、MPPI、
# waypoint 和状态机边界都有修改，必须联合 build 到 install/。
# 同时必须先完成 2.3 中的 PCD/YAML/PGM 三文件配对检查。
docker compose run --rm builder_base bash -lc '
  source /opt/ros/humble/setup.bash
  cd /botbrain_ws
  colcon build --packages-select open3d_loc g1_pkg bot_navigation bot_state_machine \
    --cmake-args -DOpen3D_DIR=/opt/open3d/lib/cmake/Open3D
'

# 终端 1：基础服务。rm 很重要：它会清除旧容器残留的 restart: always 策略。
docker compose stop state_machine navigation localization
docker compose rm -f state_machine navigation localization
docker compose up -d bringup state_machine foxglove

# 终端 2：FAST-LIO 里程计与 Open3D 定位
docker compose stop fast_lio localization
docker compose rm -f fast_lio localization
docker compose up -d fast_lio
docker compose --profile navigation up -d --force-recreate localization

# 输出必须是当前选择，例如 MAP_SCENE=ug
docker inspect g1_robot_localization \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^MAP_SCENE='

docker compose logs -f fast_lio localization | \
  grep -E "Map selection:|IMU Initial Done|FAST_LIO_TIMING|FAST_LIO_GUARD|Planar base TF|Map/odom height|Map/odom roll/pitch|ICP 4.00 Hz|Global initialization|Prepared .*FPFH|Global candidate|LocalizationInitialize|localization initialization succeeded|Localization ready|ICP: accepted|Manual relocalization|ignoring /initialpose|Rejecting|Skipping ICP|Waiting for odometry history"
```

**初始位姿对齐：**
- 启动后先保持机器人静止，等待 FPFH/RANSAC 连续三个一致候选，不需要机器人站在建图起点
- 必须看到 `Global localization initialization succeeded`、`Localization ready` 以及 `/localization_ready=true`
- 在 ready 之前不发布用于导航的猜测 `map -> odom`，Foxglove 暂时不能把点云叠到地图上属于预期保护行为
- 只有全局候选长时间无法到达 `3/3` 时，才把 Foxglove Fixed Frame 设为 `map` 后发送 `/initialpose`，并确认 `Manual relocalization applied`
- localization 日志出现 `ICP: accepted=true`，且 `fitness>0.50`、`rmse<=0.30` 并通过 correction 门，才表示该帧真正更新了 `map -> odom`
- `fitness=1.000` 也不能单独证明高度正确；必须同时确认 `map_odom_z=1.247` 和 `map_odom_rp≈0/0deg`
- 至少稳定观察约 10 秒 accepted 更新后再启动 navigation

### 5.2 启动导航

```bash
cd /data/unitree/botbrain_ws
docker compose up -d navigation   # 终端3

# 先看 preflight：容器先 sleep 30s，然后最多等待 300s。
# 看到 passed 后 Ctrl+C 退出日志跟随，再执行下方 lifecycle 检查。
docker compose logs -f navigation | \
  grep -E "Waiting for navigation inputs|Navigation preflight passed|preflight timed out|ERROR|FATAL"

# preflight 通过后再最多轮询 Nav2 lifecycle 90s。
# 从 docker compose up 到可用总等待时间要预留 330s 以上。
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  for attempt in $(seq 1 18); do
    ready=true
    for node in controller_server smoother_server planner_server behavior_server bt_navigator waypoint_follower; do
      state=$(ros2 lifecycle get "/g1_robot/$node" 2>/dev/null || true)
      printf "%s: %s\n" "$node" "$state"
      case "$state" in
        *"active [3]"*) ;;
        *) ready=false ;;
      esac
    done
    if ! ros2 action list -t | grep -q "^/g1_robot/navigate_to_pose "; then
      ready=false
    fi
    if [ "$ready" = true ]; then
      echo "Nav2 ready: all lifecycle nodes active and NavigateToPose available"
      exit 0
    fi
    sleep 5
  done
  echo "Nav2 readiness check failed after 90s" >&2
  exit 1
'

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

preflight 同时硬性检查五项输入，任一项不满足都不会启动 Nav2。日志中的字段分别是 `scan`、`twist_odom`、`ready`、`confidence` 和 `tf`：

| 日志字段 | 必须满足 | 失败时先查 |
|---|---|---|
| `scan` | `/scan` 接收时间和消息时间戳都在 1s 内 | FAST-LIO body 点云、pointcloud_to_laserscan 和 TF |
| `twist_odom` | `/g1_robot/odom` 接收时间和时间戳都在 0.5s 内，`child_frame_id=g1_robot/base_footprint`，平面 twist 为有限数 | Unitree odom publisher、frame 配置和机器人时钟 |
| `ready` | transient-local `/localization_ready=true` | FPFH/RANSAC 全局初始化或手工回退是否真正成功 |
| `confidence` | 新鲜度 1s 内且 `>=0.55` | ICP fitness/RMSE、时间戳和 PCD 质量 |
| `tf` | `map -> g1_robot/base_footprint` 存在，Z 与 roll/pitch 为合理平面值 | `map -> odom -> base_footprint` TF 链 |

如果出现 `Navigation preflight timed out after 300.0 s`，容器会退出且 Nav2 不会启动。定位或 `/scan` 修复后需要再显式执行 `docker compose up -d navigation`；不应改短检查或让容器无限自动重启。

六个 lifecycle 节点必须全部输出 `active [3]`，且 action 列表必须包含 `/g1_robot/navigate_to_pose`。否则不得发送导航点，先查看：

```bash
docker compose logs --tail 200 navigation | \
  grep -E "Controller period|ERROR|FATAL|Failed to bring up|Managed nodes are active"
```

`Found orphan containers` 只是 Compose 项目中存在旧容器标签，不是本次 Nav2 失败的原因。不要直接使用 `--remove-orphans`，先确认 `g1_robot_camera` 和 `g1_robot_cam_bridge_sender` 是否仍在使用。对旧 `g1_robot_mapping` 应检查是否仍在重复发布：

```bash
docker inspect -f '{{.State.Running}} {{json .Config.Cmd}}' g1_robot_mapping 2>/dev/null || true
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic info -v /Odometry_loc
  ros2 topic info -v /cloud_registered_1
'
```

两个话题都应只有一个 FAST-LIO publisher。

### 5.3 点位记录与多点导航

```bash
docker exec -it g1_robot_navigation bash
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash

ros2 run bot_navigation waypoint_recorder.py record ug_office   # 记录 UG 点位
ros2 run bot_navigation waypoint_recorder.py list            # 查看点位
ros2 run bot_navigation waypoint_navigator.py ug_office      # 单点导航
ros2 run bot_navigation waypoint_navigator.py ug_kitchen ug_office ug_home --loop
ros2 run bot_navigation localization_monitor.py --ros-args \
  -p auto_cancel:=true                                       # 连续低置信度时取消导航
```

> 点位文件：`/data/unitree/botbrain_ws/botbrain_ws/src/bot_navigation/nav_waypoints.yaml`
>
> 当前该文件由所有楼层共享，`MAP_SCENE` 不会自动切换或过滤点位。点名必须包含场景前缀；例如切到 `floor4` 后只记录、调用 `floor4_*`，不得调用 `ug_*`。
>
> 点位只保存平面 `x/y/yaw`：`z=0`、`qx=qy=0`。`waypoint_navigator` 不再在到点后把目标坐标硬发为 `/initialpose`；`localization_monitor` 也不再存在 `auto_anchor` 参数，不会把当前定位输出反馈为初始位姿。启动绝对位置由 FPFH/RANSAC 求解，人工 `/initialpose` 只是失败回退。

### 5.4 服务启动延迟与就绪检查

| 服务 | 启动延迟 | 就绪标志 |
|------|---------|---------|
| `bringup`（雷达驱动） | 硬件握手 **5~10s** | `livox/lidar publish use livox custom format` |
| `fast_lio` | **sleep 25s** | `/Odometry_loc` 与可信 `/cloud_registered_1` 持续发布，`FAST_LIO_TIMING ok=true` |
| `localization` | **sleep 30s** | `Global localization initialization succeeded`、`/localization_ready=true`，随后出现 `ICP: accepted=true` |
| `navigation` | **sleep 30s + preflight 最多 300s** | `Navigation preflight passed`，随后 Nav2 lifecycle 全部 active |

> bringup 刚起来时 fast_lio 打印 `No Effective Points!` 属正常，等雷达就绪后自动恢复。超过 30s 仍无点云再排查。

**启动就绪检查顺序（必须按序，否则必飘）：**
1. ✅ bringup 出现 `livox custom format` → 雷达就绪
2. ✅ fast_lio 出现 `IMU Initial Done`，且 `/Odometry_loc`、`/cloud_registered_1` 正常 → 里程计就绪
3. ✅ localization 日志确认高度、roll/pitch 和 `Planar base TF` 三个约束均为 `enabled=true`，且 `ICP 4.00 Hz (250.0 ms), cloud_queue=1, odom_history=30, ... stamp_skew<=0.030s`
4. ✅ 等待三个一致 FPFH/RANSAC 全局候选，确认 `Localization ready` 和 `/localization_ready=true`；只在自动初始化失败时手工回退
5. ✅ 连续出现可信 `ICP: accepted=true`，跳变帧能被 1m/15deg 门限拒绝
6. ✅ 启动 navigation 前确认 `/scan` 时间戳新鲜，等待 `Navigation preflight passed`
7. ✅ Nav2 启动后确认 `/g1_robot/nav_odom` 持续发布、六个 lifecycle 节点全部 `active [3]` 且 `/g1_robot/navigate_to_pose` action 存在

**启动导航必须同时保持 bringup、fast_lio、localization 正常运行。**

### 5.5 `/scan` 断流与 observation buffer 告警分类

`The /scan observation buffer has not been updated for ... seconds` 表示 costmap 没有收到可用的新观测。`expected_update_rate: 1.0` 的单位是秒，含义是两份可用 scan 的间隔不应超过 1s，不是设置为 1Hz 后可以忽略 80s 告警。不要把该参数改为 `0`来消除日志，否则只会隐藏冻结障碍物的安全故障。

先在 bringup 容器中按数据链上游到下游检查：

```bash
docker exec -it g1_robot_bringup bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic list -t | grep -E "^/(cloud_registered_body_1|scan)[[:space:]]"
  ros2 topic info -v /cloud_registered_body_1
  ros2 topic info -v /scan
  timeout 5 ros2 topic hz /cloud_registered_body_1 || true
  timeout 5 ros2 topic hz /scan || true
  timeout 5 ros2 topic echo --once /cloud_registered_body_1 --field header || true
  timeout 5 ros2 topic echo --once /scan --field header || true
  timeout 3 ros2 run tf2_ros tf2_echo g1_robot/base_footprint body || true
  timeout 3 ros2 run tf2_ros tf2_echo map g1_robot/base_footprint || true
  timeout 3 ros2 run tf2_ros tf2_echo g1_robot/odom g1_robot/base_footprint || true
'
```

| 检查结果 | 问题层级 | 处理 |
|---|---|---|
| `/scan` 没有 publisher | bringup 内 `pointcloud_to_laserscan` 未启动或 install 仍是旧版 | 查 bringup 日志，重新 build `g1_pkg` 并重建 bringup 容器 |
| `/cloud_registered_body_1` 无新数据 | FAST-LIO/雷达上游断流 | 查 `IMU Initial Done`、`FAST_LIO_TIMING`、guard 和 `output latched unhealthy`，不要继续导航 |
| body 点云有数据，`/scan` 无消息 | 点云到 `g1_robot/base_footprint` 的同时间戳 TF 不可用，或 pointcloud_to_laserscan 未收到输入 | 查点云 `frame_id`、平面 base TF、节点订阅/QoS 和 message-filter 日志 |
| `/scan` 持续发布，但 ranges 几乎全是 `inf` | 环境当前确实无回波，或高度/距离带排除了所有有限点 | 对照 body 点云检查 `min_height/max_height`、`range_min/range_max`；不要把全 `inf` 误判为话题断流 |
| `/scan` 有新数据，costmap 仍告警 | scan 到 `map`/`g1_robot/odom` 的 TF 在消息时间戳处被拒绝，或 `/scan` 存在多类型/旧容器 | 确认 `/scan` 只有 `sensor_msgs/msg/LaserScan`，再查两条 TF 和重建 navigation |
| bringup 启动时就出现 navigation 告警 | 旧 navigation/localization 容器还保留 `restart: always` | 执行 `docker compose stop navigation localization && docker compose rm -f navigation localization`，修复后再显式启动 |

查联合日志时使用：

```bash
docker compose logs --tail 250 bringup fast_lio localization navigation | \
  grep -E "pointcloud_to_laserscan|Transform|Message Filter|cloud_registered_body|output latched unhealthy|observation buffer|Navigation preflight"
```

### 5.6 动态行人、膨胀和 local costmap 居中验收

全局和局部 costmap 的 `/scan` 均已启用 `marking=true`、`clearing=true`、`observation_persistence=0`、`inf_is_valid=true`，并且 raytrace 距离大于障碍标记距离。复测时必须先确认 `/scan` 无断流，然后让行人进入并离开雷达可见区域：运行时新增的行人应先被标记，随后在空闲射线再次观测到该区域时清除。

判断前先单独显示 `/map`：如果关掉两个 costmap 和点云后黑点仍在，该行人/噪点已写入 PGM，动态 clearing 不可能修改静态地图文件，必须用 Map Editor 擦除。清空 costmap service 只用于诊断运行时动态层，不能代替正常射线清理。

global inflation 当前保留 `inflation_radius=0.35m`，因为机器人加 padding 后的外接半径约为 `0.34m`；继续缩小会削弱 footprint 碰撞保护。`cost_scaling_factor=15.0` 使软代价更快衰减，用于缩窄视觉上的膨胀带，不应根据 Foxglove 叠加颜色再随意改小安全半径。

local costmap 的配置是 `g1_robot/odom` 坐标系下 `8m x 8m` 的 `rolling_window=true`，正常时机器人应在窗口中心。Foxglove 列表中该图层是灰色且眼睛带删除线时，表示图层实际被隐藏，不能用该截图判断未居中。先打开 `/g1_robot/local_costmap/costmap`，再用同一 costmap 时间戳的 TF 做数值验证：

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 run bot_navigation costmap_center_check.py
'
```

通过时会输出 costmap `origin/center`、同时间戳的 base 位置和 `error`。在 `0.05m` 分辨率下默认允许两个栅格，即 `error<=0.10m`。若失败，先查 costmap header 时间戳和 `g1_robot/odom -> g1_robot/base_footprint` TF，不要通过手工改 costmap origin 迁就截图。

### 5.7 `/g1_robot/nav_odom` 与里程计偏移检查

原 `/g1_robot/odom` 消息的 pose/yaw 来自 Unitree，而 `odom -> base_footprint` TF 来自 FAST-LIO，两者不是同一个位姿状态。导航现在统一使用 `/g1_robot/nav_odom`：平面 `x/y/yaw` 取自 `/Odometry_loc` 并与 TF 一致，twist 取自 `/g1_robot/odom`。检查：

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic info -v /g1_robot/nav_odom
  timeout 5 ros2 topic hz /g1_robot/nav_odom || true
  timeout 5 ros2 topic echo --once /g1_robot/nav_odom --field header || true
  timeout 3 ros2 run tf2_ros tf2_echo g1_robot/odom g1_robot/base_footprint || true
'

docker compose logs --tail 120 navigation | \
  grep -E "Nav odom relay|coherent planar nav odometry|Unitree odometry twist.*stale"
```

`/g1_robot/nav_odom` 应只有一个 `nav_odom_relay` publisher，帧为 `g1_robot/odom -> g1_robot/base_footprint` 且频率稳定。出现 `Unitree odometry twist is missing or stale` 时 relay 会输出零速并提高协方差，应先修复 Unitree odom 断流再发目标。不再用 `/g1_robot/odom` 的 pose 判断导航 TF 是否正确，也不得把任何相对 odom 话题转发为 `/initialpose`。

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
| 安装到包内的配置文件 (`config/*.yaml` 等) | ✅ | **先 build 再重启** |
| 地图文件 (`.pcd` / `.pgm` / 地图 `.yaml` / 编辑器 `.json`) | ❌ | 重启或重载对应服务即可（直接读文件路径） |
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
   --cmake-args -DCMAKE_BUILD_TYPE=Release"

# 编译成功后重启服务
docker compose stop fast_lio && docker compose up -d fast_lio
```

#### 服务 → 源码包 → 完整操作流程

| 服务名 | 主要源码包 | 编译命令 | 重启命令 |
|---|---|---|---|
| `fast_lio` | `fast_lio`, `g1_pkg` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select fast_lio g1_pkg"` | `docker compose stop fast_lio && docker compose up -d fast_lio` |
| `localization` | `open3d_loc`, `g1_pkg` | `docker compose run --rm builder_base bash -c "source /opt/ros/humble/setup.bash && cd /botbrain_ws && colcon build --packages-select open3d_loc g1_pkg --cmake-args -DOpen3D_DIR=/opt/open3d/lib/cmake/Open3D"` | `docker compose stop navigation localization && MAP_SCENE=floor4 docker compose --profile navigation up -d --force-recreate localization`（将 `floor4` 换成当前场景） |
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



---

## 追加：转弯后再移动漂移的第三轮修正与验收（2026-07-12）

本轮修正针对的不是 Foxglove 显示问题，而是“旋转后短暂稳定，再次移动时状态或 map→odom 突然跳飞”的恢复链路。

### 1. FAST-LIO：连续拒帧后的 state-only recovery

严格 guard 拒绝坏 LiDAR 更新时，仍然会保留 IMU 预测，但如果连续很多帧都被拒绝，纯 IMU 状态会逐渐离开真实位置；此时后续正确的 LiDAR correction 可能因为修正量超过普通门限而继续被拒绝，形成永久锁死。

当前增加高置信恢复条件：

| 参数 | 当前值 | 含义 |
|---|---:|---|
| `mapping.guard_recovery_min_rejections` | 5 | 至少连续拒绝 5 个候选后才允许恢复 |
| `mapping.guard_recovery_min_effective_ratio` | 0.10 | 恢复帧必须有更高有效点比例 |
| `mapping.guard_recovery_max_residual` | 0.15 m | 恢复帧 residual 必须比普通 guard 更严格 |
| `mapping.guard_recovery_max_translation_correction` | 1.50 m | 只对恢复候选放宽平移修正量 |
| `mapping.guard_recovery_max_rotation_correction_deg` | 45° | 只对恢复候选放宽旋转修正量 |

满足条件时日志为：

`[FAST_LIO_GUARD] state-only recovery on guarded candidate N`

该帧只把高置信 LiDAR correction 写回 EKF 状态，**故意跳过 `map_incremental()`**，因此不会写 ikd-tree，也不会写入待保存 PCD。下一份点云仍必须重新通过普通严格 guard，地图写入才恢复。这样可以同时避免“永远拒帧锁死”和“用放宽门限的恢复帧污染地图”。

IMU propagation 前后也会检查状态与 covariance 是否 finite；传播后出现 NaN/Inf 时恢复传播前状态并跳过当前 scan/map insertion。

### 2. Open3D：每次 ICP 必须使用新的世界点云窗口

定位线程以前由里程计时间戳驱动。当里程计持续更新但 LiDAR 没有新帧时，同一个旧点云窗口可能被重复执行 ICP；原本的“两次一致确认”可能只是同一份数据算了两遍，属于伪确认。

当前通过 `scan_generation_` 修正：

- `CallbackScan()` 每收到并聚合一份新点云窗口，generation 加一；
- 初始化 ICP 和正常定位 ICP 都记录最后处理的 generation；
- generation 未变化时不重复 ICP，且正常定位置信度发布为 0；
- 中等 correction 的两次确认必须来自两个不同 incoming cloud window；
- `large_correction_confirmations: 1` 时，第一份满足质量门的新点云仍可直接接受。

### 3. Open3D：强制检查点云必须是 `camera_init` 世界坐标

新增参数：

`registered_cloud_world_frame: camera_init`

`cloud_registered_1` 的 `header.frame_id` 不等于该参数时，Open3D 会拒绝点云并输出：

`Rejecting cloud_registered_1 frame '...': Open3D requires world-frame cloud 'camera_init'`

这是防止误把 `/cloud_registered_body_1` 或其他机器人随动坐标点云接入 ICP。算法的 source crop、初值和 map→odom 计算都假定输入点已经在 FAST-LIO 世界坐标中；body-frame 点云若混入，会直接制造“点云随机器人转、ICP 又尝试把它对地图”的灾难性错误。

Foxglove 必须区分两种用途：

- 检查 FAST-LIO 自身是否漂移：Fixed/Display Frame = `camera_init`，只看 `/cloud_registered_1`。
- 检查成品地图定位和导航：Fixed Frame = `map`，Display/Follow Frame = `map` 或 `g1_robot/base_footprint`，叠加 `/pcd_map`、`/cloud_registered_1` 和 `/map`。
- `/initialpose` 只能在 Fixed Frame = `map` 时发送；非 `map` frame 会被明确拒绝。
- 不用 `/cloud_registered_body_1` 判断世界地图是否稳定。

### 4. `/initialpose` 与运行中 ICP 的并发保护

`/initialpose` 表示的是 `map_T_base`，必须转换为：

`map_T_odom = map_T_base * inverse(odom_T_base)`

不能直接把 `map_T_base` 当作 `map_T_odom`。当前回调会同时更新 map→odom、派生 base→map、Kalman 基准，并增加 `manual_pose_generation_`。

若用户发送 `/initialpose` 时 ICP 正在计算，旧 snapshot 算出的 ICP 结果会因 generation 不一致而被丢弃，日志为：

- `LocalizationInitialize: discarding stale ICP result after manual relocalization`
- `Discarding stale ICP result after manual relocalization`

这样旧 ICP 不会覆盖刚设置的人工重定位。

### 5. 初始化阶段不再允许低质量 ICP 逐轮带偏

有效最低初始化 fitness 被夹紧为不低于 `threshold_fitness_init`。当前两者均为 0.50：

- `threshold_fitness_init: 0.50`
- `min_initialization_fitness: 0.50`

只有同时通过 fitness、RMSE、单次平移/旋转门限的 candidate 才能更新 map→odom，并且初始化成功需要两个不同点云 generation 连续通过。低质量结果只记录拒绝，不再一轮轮修改初始位姿。

### 6. 真机测试时必须观察的日志

FAST-LIO：

- `[FAST_LIO_TIMING]`
- `[FAST_LIO_GUARD] rejected=...`
- `[FAST_LIO_GUARD] state-only recovery on guarded candidate ...`
- `[FAST_LIO_GUARD] recovered after ...`

Open3D：

- `ICP 4.00 Hz (250.0 ms), ...`
- `ICP: accepted=true/false fitness=... rmse=... correction=...`
- `Holding large ICP correction ... (1/2)`
- `Rejecting ICP jump`
- `Rejecting ICP quality`
- `Manual pose reset detected`
- `Discarding stale ICP result after manual relocalization`
- 不应出现世界点云 frame 拒绝；若出现，先修正 topic/frame，不要放宽 ICP 门限

推荐验收路线：静止等待 `IMU Initial Done` → 慢速左右转 → 90° 转弯后停稳 → 再前进 1 m → 逐步提高转弯速度。出现跳变时保存完整 FAST-LIO timing/guard 和 Open3D ICP 日志，不要只截 Foxglove 图片。

## 追加：转弯后再移动漂移的第四轮修正与验收（2026-07-12）

本轮继续修复了 4 条会造成“先积累、后突然跳飞”的真实数据路径：

1. **Open3D 不再聚合 5 帧世界点云**：`pcd_queue_maxsize=1`，只用最新 `/cloud_registered_1`。FAST-LIO 急转时如果连续世界云互相有误差，历史聚合会形成双墙/重影，ICP 不能再把它当成一个刚体 source。
2. **初始化不再逐帧写 map->odom**：第一份初始化 ICP 只 pending；第二个独立 scan 必须在 `0.20 m / 4 deg` 内给出相同绝对候选，且间隔不超过 `1.0 s`，确认后才一次性提交。
3. **正常 ICP 候选有 1 秒寿命**：旧候选不能跨点云断流、长阻塞或暂停后继续完成 `2/2` 确认。
4. **FAST-LIO 空 IMU 不再重放上一帧云**：`ImuProcess::Process()` 每帧先清空复用输出。空 IMU/初始化 early return 后，当前 scan 会被跳过，不会把上一帧点云按新时间再次匹配、写图。
5. **LiDAR 时间回跳同步清理两个队列**：`lidar_buffer`、`time_buffer` 和 `lidar_pushed` 一起复位，避免点云与时间戳索引错位。

G1 当前关键参数：

```yaml
pcd_queue_maxsize: 1
immediate_icp_translation_step: 0.10
immediate_icp_rotation_step_deg: 2.0
large_correction_confirmations: 2
icp_candidate_consistency_translation: 0.20
icp_candidate_consistency_rotation_deg: 4.0
icp_candidate_max_age_sec: 1.0
max_icp_translation_step: 1.0
max_icp_rotation_step_deg: 15.0
```

启动日志应包含：

```text
ICP 4.00 Hz (250.0 ms), cloud_queue=1, odom_history=30, ... immediate<=0.10m/2.0deg, ... confirmations=2 within 1.00s
```

初始化必须先看到：

```text
LocalizationInitialize: holding consistent candidate (1/2)
```

再看到：

```text
Localization initialization succeeded: ... consistent confirmations=2
```

真机测试按“静止 10 秒 → 直行 → 慢转 90 度 → 停 3 秒 → 再直行 → 逐步提高转速”执行。若单帧 source 长期少于 100 点，可把队列临时调为 2；不要直接恢复 5。若 `/Odometry_loc` 在 Open3D 修正之前已经跳变，继续检查 `[FAST_LIO_TIMING]`、`[FAST_LIO_GUARD]`、IMU 翻转、外参和硬件时间同步。

完整根因、代码路径和验证边界见：`FAST_LIO转弯后不可恢复漂移第二阶段分析与解决报告.md` 的第 13 节。
### 第四轮补充：IMU 去畸变内部状态初始化与完整回滚

进一步确认 `ImuProcess` 的 `acc_s_last`、`last_lidar_end_time_` 原来没有初始化，却在第一帧正式去畸变时直接参与 pose 和 `dt` 计算。现已在构造与 `Reset()` 中固定为 `Zero3d` 和 `-1.0`。

同时新增 `PropagationCheckpoint`。若 IMU propagation 后出现 NaN/Inf，不仅恢复 EKF state/covariance，还会恢复 `last_imu_`、上一角速度/加速度、上一 LiDAR 结束时间并清空本帧云，避免“EKF 已回滚但 IMU 内部时间线仍向前”的半回滚状态。

## 追加：第五轮转弯漂移修正与真机验收（2026-07-12）

本轮又定位到一个会在转弯时放大的确定性竞态：FAST-LIO 先发布 `/Odometry_loc`，再发布同一帧的 `/cloud_registered_1`；旧 Open3D 线程可能在两次 publish 之间醒来，提前消耗新里程计，却仍拿到旧点云，随后形成“点云 N + 里程计 N+1”的错配。直行时不明显，转弯时会直接制造错误 ICP correction。

现在 Open3D 由新点云 generation 驱动，并要求点云与里程计 stamp 一致：

```yaml
pcd_queue_maxsize: 1
max_scan_odom_time_skew_sec: 0.03
```

启动日志应包含：

```text
ICP 4.00 Hz (250.0 ms), cloud_queue=1, odom_history=30, ... stamp_skew<=0.030s ...
```

若出现以下日志，Open3D 会等待同帧数据，不会提交 ICP：

```text
Skipping ICP until cloud/odometry stamps match (...)
LocalizationInitialize: waiting for matching cloud/odometry stamps (...)
```

### FAST-LIO 当前严格写图条件

`mid360.yaml` 当前关键值：

```yaml
guard_min_effective_points: 100
guard_min_effective_ratio: 0.10
guard_max_residual: 0.15
guard_max_translation_correction: 0.25
guard_max_rotation_correction_deg: 5.0
guard_recovery_min_rejections: 5
guard_recovery_min_effective_points: 60
guard_recovery_min_effective_ratio: 0.15
guard_recovery_max_residual: 0.10
guard_recovery_max_translation_correction: 0.75
guard_recovery_max_rotation_correction_deg: 15.0
guard_max_unconfirmed_odometry_frames: 3
guard_max_consecutive_rejections: 30
guard_max_position_norm: 1000.0
guard_max_abs_z: 5.0
guard_max_velocity_norm: 20.0
```

同时每帧必须满足 timing：

- IMU 数量不少于 5；
- 最大 IMU gap 不超过 0.02 秒（包含前后 LiDAR 帧边界）；
- scan 时长 0.05~0.15 秒；
- scan 末端与最后 IMU 间隔不超过 0.03 秒。

`[FAST_LIO_TIMING] ok=false` 的帧允许 IMU 状态时间线继续前进，但不能初始化/更新 ikd-tree，也不能 state-only recovery。

### rejected/recovery 时 Foxglove 的预期表现

- rejected 或 state-only recovery 帧不再发布 `/cloud_registered_1`；
- 因此 Foxglove 世界点云会短暂停在上一份可信帧，而不是跟随错误预测旋转；
- `/Odometry_loc` 最多桥接 3 帧 IMU prediction，随后暂停 odom/TF，触发定位与 costmap 的新鲜度保护；
- `/cloud_registered_body_1` 可继续用于查看原始 body-frame 点云；
- 下一帧同时通过 timing、有效点、residual 和 correction 严格门后，世界点云恢复刷新。

若连续 30 帧仍无法恢复，会出现 `output latched unhealthy`。此时节点继续存活以保留日志和已验证的建图缓存，但不会再发布导航可用输出；必须停止机器人并重启 `fast_lio`。

不要把“拒帧期间世界云暂停刷新”误判为 topic 断流，这是有意的安全隔离。若需要确认，联合查看：

```text
[FAST_LIO_TIMING]
[FAST_LIO_GUARD]
/cloud_registered_body_1
```

### 第五轮标准测试路线

1. 启动后机器人严格静止至少 10 秒，等待 `IMU Initial Done`。
2. 直行 1~2 米，确认 `timing=true`，guard 基本 accepted。
3. 慢速左转 90 度，停止 3 秒，再直行 1 米。
4. 慢速右转 90 度，停止 3 秒，再直行 1 米。
5. 逐步提高转速，不要第一轮直接急转。
6. 同时录制：

```bash
ros2 bag record /livox/imu /livox/lidar /Odometry_loc /cloud_registered_1 /cloud_registered_body_1
```

7. 若仍发生跳飞，必须保存跳飞前后至少 10 秒的：
   - `[FAST_LIO_TIMING]`；
   - `[FAST_LIO_GUARD]`；
   - Open3D fitness/rmse/correction；
   - cloud/odom stamp mismatch 日志。

### 验收判断

- **通过**：急转坏帧被拒绝，地图/世界云不被污染；恢复后无需重启服务即可继续 accepted 和建图/导航。
- **仍是时序问题**：频繁 `timing=false` 或 stamp mismatch；先修 DDS/CPU/驱动/时间同步，不能放宽 ICP 大跳门。
- **仍是 IMU/外参问题**：timing 一直正常，但每次同方向转弯都出现相似 correction；验证 `imu_flip_yz` 的重力/yaw 符号，并标定 `time_offset_lidar_to_imu` 与 LiDAR-IMU 外参。
- **走廊不可观测**：fitness 较高但沿走廊方向缓慢累计；需要回环、视觉、标志物或机器人里程计等额外约束，纯 ICP gate 只能防突然跳飞。

完整代码根因和修复链见 `FAST_LIO转弯后不可恢复漂移第二阶段分析与解决报告.md` 第 14 节。
