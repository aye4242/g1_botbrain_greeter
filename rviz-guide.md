# RViz2 建图与导航使用指南（G1）

> 本项目建图、定位和导航统一使用 **workstation 本地 RViz2**，通过 Zenoh 直接订阅机器人的 ROS 2 图；不使用 Foxglove WebSocket。

## 1. 开始前检查

机器人端启动基础服务和 Zenoh：

```bash
cd /data/unitree/botbrain_ws
# 一次性清理旧版本遗留的 Foxglove 容器；当前 Compose 已不再定义该服务。
docker rm -f g1_robot_foxglove 2>/dev/null || true
docker compose up -d zenoh bringup state_machine
docker compose ps zenoh
```

`zenoh` 必须为运行状态。工作站需要安装：

```bash
sudo apt install ros-humble-rmw-zenoh-cpp ros-humble-rviz2
```

工作站与机器人需要处于可通信的局域网，且能访问 G1 的 TCP `7448`。RViz2 在工作站本地渲染，不经过浏览器和 Foxglove WebSocket；网络短暂波动时，先检查 Zenoh 连接和话题新鲜度。

## 2. 工作站连接机器人

每次新开终端、切换机器人或 RViz2 无数据时，在 **workstation** 执行：

```bash
project_dir=/home/aitech/Workspace/g1_botbrain_greeter  # 改为实际项目目录
g1_ip=192.168.100.30                                  # 改为当前机器人 IP

source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_CONFIG_OVERRIDE="mode=\"client\";connect/endpoints=[\"tcp://${g1_ip}:7448\"]"

ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
sleep 3
ros2 topic info /Odometry_loc | grep "Publisher count"
```

`Publisher count` 必须大于 `0`。为 `0` 时，不要先调 RViz2：先核对 `g1_ip`、机器人端 `docker compose ps zenoh` 和局域网连接，再重做 daemon 刷新。

## 3. 建图：使用建图预设

先按 `建图导航指令.md` 启动 `zenoh + bringup + state_machine + fast_lio`，并在日志出现 `IMU Initial Done` 后再移动机器人。

```bash
rviz2 -d "$project_dir/configs/g1_mapping_rviz2.rviz"
```

预设已经加载下列图层，无需手动 Add：

| 图层 | 话题 | 用途 |
|---|---|---|
| accumulated_grid | `/accumulated_grid` | 建图中的 2D 累计栅格 |
| registered_world_map | `/cloud_registered_1` | FAST-LIO 世界点云，判断建图是否漂移 |
| Path | `/path_1` | FAST-LIO 轨迹 |
| Odometry | `/Odometry_loc` | FAST-LIO 里程计 |
| TF | `/tf`、`/tf_static` | 查看 `camera_init -> body` 坐标关系 |

建图时确认左侧 `Global Options -> Fixed Frame` 为 `camera_init`。使用 `Move Camera` 旋转、平移和缩放视角；要看平面地图可在 `Views` 面板选择 TopDownOrtho 或从上方俯视。

验收标准：

- `/cloud_registered_1` 中的墙体随环境固定，不应随机器人转身而整体旋转。
- `/accumulated_grid` 会随着移动逐渐形成连续的墙体和自由区域。
- `/cloud_registered_body_1` 是随机器人移动的 body 坐标点云，仅用于诊断，不能用来判断地图漂移。

如有 `No transform` 或数据不刷新，先在同一终端检查：

```bash
ros2 topic hz /cloud_registered_1
ros2 topic hz /Odometry_loc
```

这两个话题应持续有频率；没有数据时排查 FAST-LIO，而不是调整 RViz2 视角。

## 4. 定位与导航：使用导航预设

先完成场景选择器和 Nav2 就绪检查。定位未 ready 时，继续打开建图预设并使用 Fixed Frame=`camera_init` 检查 FAST-LIO；不要在此时发导航目标。

```bash
rviz2 -d "$project_dir/configs/g1_nav_loc_rviz2.rviz"
```

导航预设的 Fixed Frame 默认是 `map`，包含：

| 图层 | 话题 | 正常现象 |
|---|---|---|
| Map | `/map_2d` | 保存的 2D PGM 地图，静态不变 |
| map (scans.pcd) | `/pcd_map` | Open3D 成品 3D PCD，静态不变 |
| LaserScan | `/scan` | 机器人附近实时障碍扫描 |
| Path | `/plan` | Nav2 规划路径；发目标后才出现 |
| registered cloud (FAST-LIO) | `/cloud_registered_1` | 实时世界点云，应与成品地图重合 |
| TF | `/tf`、`/tf_static` | 应具备 `map -> odom -> g1_robot/base_footprint` 链 |

定位成功后，`/pcd_map`、`/cloud_registered_1` 与 `/map_2d` 的墙体轮廓应重合。若手动添加 `/cloud_registered_body_1`，它随机器人倾斜或移动属于正常定义，判断地图对齐时请关闭它。

## 5. 在 RViz2 发初始位姿与导航目标

只有在 Fixed Frame=`map` 时才能发布这两个工具消息。

### 手工初始位姿（仅自动定位失败时）

正常情况下，保持机器人静止，等待 FPFH/RANSAC 自动初始化和日志 `Localization ready`。只有长期无法形成 `3/3` 一致候选时才操作：

1. 在 RViz2 工具栏选择 `2D Pose Estimate`。
2. 在 `/map_2d` 上机器人实际位置处按下左键并拖动。
3. 拖动箭头方向必须与机器人当前朝向一致；长度不重要。
4. 确认定位日志出现 `Manual relocalization applied`，并继续等待 `Localization ready` 和连续 `ICP: accepted=true`。

该工具发布 `/initialpose`。若日志提示 `ignoring /initialpose in frame 'camera_init'`，说明 Fixed Frame 错误，改回 `map` 后重发。

### 发送导航目标

仅当 `Localization ready`、场景选择器成功且 Nav2 lifecycle 全部 active 后操作：

1. 在工具栏选择 `2D Goal Pose`。
2. 在地图上点击目标位置并拖动，箭头表示期望到达朝向。
3. 松开鼠标后，预设向 `/goal_pose` 发布目标；`/plan` 出现路径后，机器人开始导航。
4. 若要改目标，重新发送一个 `2D Goal Pose`；先确认机器人周边安全。

## 6. 常见问题

| 现象 | 先做什么 |
|---|---|
| RViz2 没有话题或 `Publisher count: 0` | 检查 `g1_ip`、`docker compose ps zenoh`，重新执行第 2 节 daemon 刷新命令 |
| `No transform from ...` | 建图用 `camera_init`，定位/导航用 `map`；再检查 `/Odometry_loc` 是否持续发布 |
| 建图时墙体跟着机器人旋转 | 只看 `/cloud_registered_1`，检查 FAST-LIO `imu_flip_yz` 与 `IMU Initial Done`，不要用 body 点云判断 |
| `map` 下没有实时点云 | `/localization_ready=false` 时没有 `map -> odom` 是预期保护；回到建图预设等待定位 ready |
| 发初始位姿后被拒绝 | Fixed Frame 设为 `map`，用 `2D Pose Estimate` 重新发送 |
| 发目标后没有路径 | 先确认 `Localization ready`、Nav2 lifecycle active，以及 `/scan`、TF、定位置信度均通过 preflight |
| 点云或 scan 同时停止 | 查 FAST-LIO 日志中的 `FAST_LIO_TIMING`、`FAST_LIO_GUARD` 和 `output latched unhealthy` |

现场完整命令见 [建图导航指令.md](建图导航指令.md)，完整验收、切图和故障分析见 [机器人项目run.md](机器人项目run.md)。
