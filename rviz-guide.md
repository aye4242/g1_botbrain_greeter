# RViz2 建图与导航使用指南（G1）

> 本项目建图、定位和导航统一使用 **workstation 本地 RViz2**，通过 Zenoh 直接订阅机器人的 ROS 2 图；不使用 Foxglove WebSocket。此迁移不改变 FAST-LIO、定位、导航或既有 ROS 话题/TF，只替换工作站可视化入口。

## 1. 一次性准备

工作站安装 RViz2 和 Zenoh RMW：

```bash
sudo apt install ros-humble-rmw-zenoh-cpp ros-humble-rviz2
```

机器人端按 `建图导航指令.md` 启动 `zenoh + bringup + state_machine`。工作站和机器人必须能互通 TCP `7448`。

RViz2 的界面在工作站本地渲染，避免了 Foxglove 浏览器/WebSocket 的额外开销，但点云仍需通过网络从机器人传到工作站。网络本身很差时仍可能延迟；现场优先使用机器人直连网线、机器人局域网或距离近且稳定的 Wi-Fi，不要依赖楼层公网。

## 2. 一条命令打开 RViz2

在 **workstation** 执行，IP 改为当前 G1：

```bash
# 建图界面
cd /home/aitech/Workspace/botbrain_project
bash tools/host_side/mapping_rviz2.sh 192.168.100.30

# 定位/导航界面
bash tools/host_side/g1_nav_loc_rviz2.sh 192.168.100.30
```

两个脚本会自动加载 ROS、设置 Zenoh、刷新 ROS 2 daemon 并打开正确预设。正常使用不需要再手动执行 `source`、`export`、`ros2 daemon` 或 `rviz2 -d`。

预设把实时 `/cloud_registered_1` 配成 `Best Effort + Depth 1`：弱网络时宁可跳过旧显示帧，也不积压成数秒延迟。静态 `/map`、`/pcd_map` 和累计栅格仍使用可靠 QoS，因此短暂少几帧实时点云不代表机器人端建图丢失。

## 3. 建图：使用建图预设

先按 `建图导航指令.md` 启动 `zenoh + bringup + state_machine + fast_lio`，并在日志出现 `IMU Initial Done` 后再移动机器人。

预设已经加载下列图层，无需手动 Add：

| 图层 | 话题 | 用途 |
|---|---|---|
| accumulated_grid | `/accumulated_grid` | 建图中的 2D 累计栅格 |
| registered_world_map | `/cloud_registered_1` | FAST-LIO 世界点云，判断建图是否漂移 |
| Path | `/path_1` | FAST-LIO 轨迹 |
| Odometry | `/Odometry_loc` | FAST-LIO 里程计 |
| TF | `/tf`、`/tf_static` | 查看 `camera_init -> body` 坐标关系 |

建图时左侧 `Global Options -> Fixed Frame` 应为 `camera_init`，不需要手动改话题。

RViz2 视角操作：

- 俯视栅格：右侧 `Views -> Current View -> Type` 选择 `TopDownOrtho`。
- 检查点云高度、倾斜和重影：`Type` 选择 `Orbit`。
- `Orbit` 下左键拖动旋转视角，中键拖动平移，滚轮缩放。
- 左侧 Displays 的勾选框用于显示/隐藏图层；绿色状态表示正常，红色状态展开后可查看错误。
- 建图只保持 `accumulated_grid`、`registered_world_map`、`Path`、`Odometry` 和 `TF` 开启；`body_scan_debug` 默认关闭。
- 不要手工覆盖保存项目预设；界面调乱后关闭 RViz2，重新执行启动脚本即可恢复预设。

验收标准：

- `/cloud_registered_1` 中的墙体随环境固定，不应随机器人转身而整体旋转。
- `/accumulated_grid` 会随着移动逐渐形成连续的墙体和自由区域。
- `/cloud_registered_body_1` 是随机器人移动的 body 坐标点云，仅用于诊断，不能用来判断地图漂移。

如有 `No transform` 或数据不刷新，在 **新的 workstation 终端** 执行下面的诊断命令：

```bash
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
g1_ip=192.168.100.30  # 改为当前 G1 IP
export ZENOH_CONFIG_OVERRIDE="mode=\"client\";connect/endpoints=[\"tcp://${g1_ip}:7448\"]"
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
ros2 topic hz /cloud_registered_1
ros2 topic hz /Odometry_loc
```

这两个话题应持续有频率；没有数据时排查 FAST-LIO，而不是调整 RViz2 视角。

长走廊建图可在机器人端执行以下命令启用模式并重建 FAST-LIO：

```bash
FAST_LIO_MAPPING_PROFILE=corridor docker compose up -d --force-recreate fast_lio
docker compose logs --tail 30 fast_lio | grep "FAST-LIO mapping profile"
```

确认输出为 `corridor`，后续连续出现 `[FAST_LIO_TIMING] ok=true`，且 `[FAST_LIO_RANGE] max=20.0m kept=.../...` 中保留点数不是长期接近零后再移动。此模式保留更多门框和房间角点，并实际过滤 20 米外的输入点，减少远处平行墙面对局部匹配的支配。如果持续出现 `timing=false` 或连续 guard rejected，立即停止移动并用默认模式重建 FAST-LIO。

长走廊中的“特征点”必须是雷达能看到的静态三维几何，例如门框、突出墙面的箱体、斜面或不对称角结构，建议尺寸至少大于 `0.3-0.5m`，并让其中一部分表面法向沿走廊方向。只贴 AprilTag、二维码、反光贴或地面图案不会帮助当前 FAST-LIO，因为当前匹配不使用相机图像或点云 intensity。经过开门房间/三维特征时减速或短暂停留，左右转动让雷达同时看到门框、房间侧墙和角点；走廊尽头分段转向，不要原地快速完成 180 度转弯。RViz 中一旦看到同一门框或房间轮廓出现双层，应立即停止继续写图。

当前 FAST-LIO 没有位姿图回环，走完整个回程不能自动修正已经形成的历史地图；走廊模式和三维特征只能减少漂移，不能替代后续真正的回环/多传感器约束。

## 4. 定位与导航：使用导航预设

先完成场景选择器和 Nav2 就绪检查。定位未 ready 时，继续打开建图预设并使用 Fixed Frame=`camera_init` 检查 FAST-LIO；不要在此时发导航目标。

导航预设的 Fixed Frame 默认是 `map`，包含：

| 图层 | 话题 | 正常现象 |
|---|---|---|
| Map | `/map` | 保存的 2D PGM 地图，静态不变 |
| map (scans.pcd) | `/pcd_map` | Open3D 成品 3D PCD，静态不变 |
| LaserScan | `/scan` | 机器人附近实时障碍扫描 |
| Path | `/g1_robot/plan` | Nav2 规划路径；发目标后才出现 |
| registered cloud (FAST-LIO) | `/cloud_registered_1` | 实时世界点云，应与成品地图重合 |
| TF | `/tf`、`/tf_static` | 应具备 `map -> odom -> g1_robot/base_footprint` 链 |

定位成功后，`/pcd_map`、`/cloud_registered_1` 与 `/map` 的墙体轮廓应重合。静态 `/pcd_map` 在预设中使用 `Alpha=0.10` 作为半透明参考底图；需要更醒目时可在左侧 `map (scans.pcd) -> Alpha` 临时调到 `0.20`。若手动添加 `/cloud_registered_body_1`，它随机器人倾斜或移动属于正常定义，判断地图对齐时请关闭它。

导航时推荐使用 `TopDownOrtho` 查看 2D 地图、路径和目标；检查 PCD 高度与实时点云重合时临时切回 `Orbit`。Fixed Frame 始终保持 `map`。

## 5. 在 RViz2 发初始位姿与导航目标

只有在 Fixed Frame=`map` 时才能发布这两个工具消息。

### 手工初始位姿（仅自动定位失败时）

正常情况下，保持机器人静止，等待 FPFH/RANSAC 自动初始化和日志 `Localization ready`。只有长期无法形成 `3/3` 一致候选时才操作：

1. 在 RViz2 工具栏选择 `2D Pose Estimate`。
2. 在 `/map` 上机器人实际位置处按下左键并拖动。
3. 拖动箭头方向必须与机器人当前朝向一致；长度不重要。
4. 确认定位日志出现 `Manual relocalization applied`，并继续等待 `Localization ready` 和连续 `ICP: accepted=true`。

该工具发布 `/initialpose`。若日志提示 `ignoring /initialpose in frame 'camera_init'`，说明 Fixed Frame 错误，改回 `map` 后重发。

### 发送导航目标

仅当 `Localization ready`、场景选择器成功且 Nav2 lifecycle 全部 active 后操作：

1. 在工具栏选择 `2D Goal Pose`。
2. 在地图上点击目标位置并拖动，箭头表示期望到达朝向。
3. 松开鼠标后，预设向 `/g1_robot/goal_pose` 发布目标；`/g1_robot/plan` 出现路径后，机器人开始导航。
4. 若要改目标，重新发送一个 `2D Goal Pose`；先确认机器人周边安全。

## 6. 常见问题

| 现象 | 先做什么 |
|---|---|
| RViz2 没有话题或 `Publisher count: 0` | 检查 G1 IP、机器人端 `docker compose ps zenoh` 和工作站网络，再重新执行第 2 节对应启动脚本 |
| `No transform from ...` | 建图用 `camera_init`，定位/导航用 `map`；再检查 `/Odometry_loc` 是否持续发布 |
| 建图时墙体跟着机器人旋转 | 只看 `/cloud_registered_1`，检查 FAST-LIO `imu_flip_yz` 与 `IMU Initial Done`，不要用 body 点云判断 |
| `map` 下没有实时点云 | `/localization_ready=false` 时没有 `map -> odom` 是预期保护；回到建图预设等待定位 ready |
| 发初始位姿后被拒绝 | Fixed Frame 设为 `map`，用 `2D Pose Estimate` 重新发送 |
| 发目标后没有路径 | 先确认 `Localization ready`、Nav2 lifecycle active，以及 `/scan`、TF、定位置信度均通过 preflight |
| 点云或 scan 同时停止 | 查 FAST-LIO 日志中的 `FAST_LIO_TIMING`、`FAST_LIO_GUARD` 和 `output latched unhealthy` |

现场完整命令见 [建图导航指令.md](建图导航指令.md)，完整验收、切图和故障分析见 [机器人项目run.md](机器人项目run.md)。
