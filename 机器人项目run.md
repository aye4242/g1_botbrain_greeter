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

**新场景建图**

```bash
# 在配置文件中修改/home/unitree/botbrain_ws/botbrain_project-main/botbrain_ws/src/fast_lio/config/mid360.yaml 启动建图保存
pcd_save_en: true
# 重新编译
cd ~/botbrain_ws/botbrain_project-main/
docker compose up builder_base
# 终端1 启动基础服务
docker compose up bringup state_machine foxglove
# 终端2 启动建图 建议建图时跑一个回环
docker compose up fast_lio
# 终端2 预计终端日志出现
g1_robot_fast_lio  | [fastlio_mapping-2] [MAP] frame=0 feats_down=200 pcl_wait_save=1257
g1_robot_fast_lio  | [python3-3] [INFO] [1782288159.495810154] [grid_accumulator]: frames=100 ground=4775 obs=10854 grid=505x464 origin=(-11.82,-14.31)
# 在foxglove里可以实时查看2/3d建图效果 /map /cloud_registered_body_1
```

```bash
# 终端3 保存栅格图
docker exec -it g1_robot_fast_lio bash
source install/setup.bash
ros2 run nav2_map_server map_saver_cli \
     -t /accumulated_grid \
     --free 0.196 --occ 0.65 \
     -f /botbrain_ws/src/g1_pkg/maps/accumulated
# -f 最后的“accumulated”是保存下来后栅格图的名称
# 保存点云图
kill -SIGINT $(pgrep fastlio_mapping)
# 默认都保存到src/g1_pkg/maps 文件夹
# 地图保存后 将yaml文件建图保存功能关闭，并重新编译
```

```bash
# 如果保存的地图名称不同，需要在src/g1_pkg/launch/localization_3d_.launch.py 中修改名称
default_pcd_path  = os.path.join(workspace_dir, 'src', 'g1_pkg', 'maps', 'scans.pcd')
default_grid_yaml = os.path.join(workspace_dir, 'src', 'g1_pkg', 'maps', 'accumulated.yaml')
# 保存后需要重新编译
```

**启动建图定位服务**

```bash
cd ~/botbrain_ws/botbrain_project-main/
# 终端1 启动基础服务
docker compose up bringup state_machine foxglove
# 终端2 启动建图定位服务
docker compose up fast_lio localization
# 情况1 机器人初始位姿与建图时机器人所在的初始位姿基本一致
#      则不需要对发布初始位姿参数进行校正机器人在地图上的位姿
# 情况2 机器人初始位姿与建图时机器人所在位姿有较大偏差(位置超过1m或角度超过90度)
#       则需要通过可视化页面rviz/foxglove 发送/initialpose 话题去指定机器人当前在地图上的位姿
# 当localization的日志参数reg_result.fitness大于0.9即完成ICP匹配
```

**启动导航服务(想要开导航就需要开启建图定位)**

```bash
cd ~/botbrain_ws/botbrain_project-main/
# 终端3 启动导航服务
docker compose up navigation
# 可以从可视化页面发送/g1_robot/goal_pose 话题开始导航

# 记录目标点位
docker exec -it g1_robot_bringup bash
source install/setup.bash
ros2 run bot_navigation waypoint_recorder.py record office
# 目标点位信息会记录到 src/bot_navigation/nav_waypoints.yaml 文件里
# 查看已经存在的点位
ros2 run bot_navigation waypoint_recorder.py list
# 或
ros2 run bot_navigation waypoint_navigator.py --list
# 删除点位
ros2 run bot_navigation waypoint_recorder.py delete kitchen

# 单点导航
ros2 run bot_navigation waypoint_navigator.py office1
# 多点导航
ros2 run bot_navigation waypoint_navigator.py office1 office2 office3 turn office4 office5 office1 home  # 末尾添加 --loop 参数可进行循环导航，ctrl+c退出 

#foxglove话题配置文件
/home/unitree/botbrain_ws/botbrain_project-main/botbrain_ws/src/bot_bringup/config/foxglove_bridge_params.yaml
```

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

