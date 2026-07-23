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
cd ~/Workspace/g1_botbrain_greeter
bash tools/host_side/mapping_rviz2.sh 192.168.37.204

# 定位/导航界面
bash tools/host_side/g1_nav_loc_rviz2.sh 192.168.37.204
```

两个脚本会自动加载 ROS、设置 Zenoh、刷新 ROS 2 daemon 并打开正确预设。正常使用不需要再手动执行 `source`、`export`、`ros2 daemon` 或 `rviz2 -d`。

建图脚本会先在工作站实际收到世界点云和 Body 点云，导航脚本会先实际收到
`/pcd_map`，然后才打开 RViz2。因此“脚本成功但打开空白预设”不再属于正常
结果：前置数据不存在时脚本会直接给出具体错误。

脚本会在终端打印实际加载的 `.rviz` 文件和已经预置的话题；所有图层均不需要手动 Add。修改或更新预设后，必须关闭旧 RViz2 窗口再重新运行脚本，因为已经打开的窗口不会自动重载磁盘配置。当前导航预设不包含 RobotModel；若仍看到 `RobotModel (G1)`，看到的是旧窗口。

预设把实时 `/cloud_registered_1` 配成 `Best Effort + Depth 1`：弱网络时宁可跳过旧显示帧，也不积压成数秒延迟。静态 `/map`、`/pcd_map` 和累计栅格仍使用可靠 QoS，因此短暂少几帧实时点云不代表机器人端建图丢失。

## 3. 建图：使用建图预设

先按 `建图导航指令.md` 启动 `zenoh + bringup + state_machine + fast_lio`，并在日志出现 `IMU Initial Done` 后再移动机器人。

预设已经加载下列图层，无需手动 Add：

| 图层 | 话题 | 用途 |
|---|---|---|
| accumulated_grid | `/accumulated_grid` | 建图中的 2D 累计栅格 |
| world scan (live) | `/cloud_registered_1` | 明亮当前世界扫描，启动后立即确认数据 |
| world history (5 min) | `/cloud_registered_1` | 工作站保留最近 300 秒，观察已走区域和重影 |
| body cloud (robot live scan) | `/cloud_registered_body_1` | 橙色当前扫描，确认雷达实时回波 |
| Path | `/path_1` | FAST-LIO 轨迹 |
| Odometry | `/Odometry_loc` | FAST-LIO 里程计 |
| TF | `/tf`、`/tf_static` | 查看 `camera_init -> body` 坐标关系 |

建图时左侧 `Global Options -> Fixed Frame` 应为 `camera_init`，不需要手动改话题。

RViz2 视角操作：

- 俯视栅格：右侧 `Views -> Current View -> Type` 选择 `TopDownOrtho`。
- 检查点云高度、倾斜和重影：`Type` 选择 `Orbit`。
- `Orbit` 下左键拖动旋转视角，中键拖动平移，滚轮缩放。
- 左侧 Displays 的勾选框用于显示/隐藏图层；绿色状态表示正常，红色状态展开后可查看错误。
- 建图预设默认打开明亮的世界当前帧、较细的 5 分钟世界历史和橙色 Body 点云；判断地图是否漂移只看两个世界层。画面太密时可临时取消 Body 或历史层，不需要删除或重新 Add。
- 不要手工覆盖保存项目预设；界面调乱后关闭 RViz2，重新执行启动脚本即可恢复预设。

验收标准：

- `/cloud_registered_1` 中的墙体随环境固定，不应随机器人转身而整体旋转。
- `/accumulated_grid` 会随着移动逐渐形成连续的墙体和自由区域。
- `/cloud_registered_body_1` 是随机器人移动的 body 坐标点云，仅用于诊断，不能用来判断地图漂移。

如有 `No transform` 或数据不刷新，在 **新的 workstation 终端** 执行下面的诊断命令：

```bash
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
g1_ip=192.168.37.204  # 改为当前 G1 IP
export ZENOH_CONFIG_OVERRIDE="mode=\"client\";connect/endpoints=[\"tcp/${g1_ip}:7448\"]"
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
ros2 topic hz /cloud_registered_1
ros2 topic hz /Odometry_loc
```

注意 Zenoh 端点格式必须是 `tcp/192.168.37.204:7448`，不是 `tcp://192.168.37.204:7448`。后者会报 `Unicast not supported for tcp: protocol`，随后 RViz2 可能连带出现 `std::bad_alloc`；这不是 RViz2 内存不足。

如果 Intel/Mesa 日志出现
`active samplers with a different type refer to the same texture image unit`，
这是本机 OpenGL 驱动的 RViz Map shader 问题，不是 ROS 点云丢失。只在此错误出现时
用软件渲染回退：

```bash
RVIZ_RENDERING=software \
bash tools/host_side/mapping_rviz2.sh 192.168.37.204
# 定位/导航则将最后一行换成 g1_nav_loc_rviz2.sh
```

### 切换 Wi‑Fi 后更换机器人 IP

如果机器人从 `192.168.37.204` 切换到 `192.168.100.3`，不需要修改 RViz 配置文件，也不需要修改机器人内部 Unitree 网口配置。直接在 workstation 执行：

```bash
# 建图
bash tools/host_side/mapping_rviz2.sh 192.168.100.3

# 定位/导航
bash tools/host_side/g1_nav_loc_rviz2.sh 192.168.100.3
```

脚本会自动更新 Zenoh 端点、刷新 ROS 2 daemon 并打开对应 RViz2 预设。机器人端只需确认 `zenoh` 仍在运行：

```bash
cd /data/unitree/botbrain_ws
docker compose up -d zenoh bringup state_machine
```

Zenoh 路由器监听 `0.0.0.0:7448`，所以机器人 Wi‑Fi 地址变化后通常不需要重启 Zenoh。若脚本提示无法连接，先确认 workstation 与机器人在同一网段，并执行 `ping 192.168.100.3`；机器人 `enP8p1s0` 的 `192.168.123.x` 地址是 Unitree 控制链路，不能因为 Wi‑Fi 换网而改掉。

这两个话题应持续有频率；没有数据时排查 FAST-LIO，而不是调整 RViz2 视角。定位未 ready 时，导航预设中的绿色/橙色实时点云会因缺少 `map` TF 而保持 Warm，但高亮蓝色 `/pcd_map` 和紫色 `/scan2map` 必须可见。紫色层会先显示未验证的实时扫描，得到匹配候选后再更新到候选位置；它可用于辅助 `2D Pose Estimate`，但不代表导航已经可用。如果蓝色 PCD 或紫色实时预览为空，先确认场景选择器已经打印 `RVIZ POINT CLOUD READY`、localization 容器为 `Up`，并检查 FAST-LIO 世界云是否持续发布。

长走廊建图在机器人端将 `profile` 设为 `corridor`，再按服务方式重建 FAST-LIO：

```bash
scene=long_corridor
profile=corridor
FAST_LIO_START_DELAY_SEC=0 \
FAST_LIO_MAPPING_MODE=true \
FAST_LIO_MAPPING_SAVE=true \
FAST_LIO_MAP_FILE="/botbrain_ws/src/g1_pkg/maps/${scene}_scans.pcd" \
FAST_LIO_MAPPING_PROFILE="$profile" \
docker compose up -d --force-recreate fast_lio
docker compose ps fast_lio
docker compose logs -f fast_lio
```

确认输出为 `corridor`，后续连续出现 `[FAST_LIO_TIMING] ok=true`，且 `[FAST_LIO_RANGE] max=20.0m kept=.../...` 中保留点数不是长期接近零后再移动。此模式保留更多门框和房间角点，并实际过滤 20 米外的输入点，减少远处平行墙面对局部匹配的支配。对移动 Wi-Fi，建图栅格仅以 0.5 Hz 发布、每 3 帧云处理一次，避免大地图占满 Jetson 或 Zenoh 队列；FAST-LIO 主点云仍是 10 Hz。如果出现 `timing=false`、连续 guard rejected 或 `output latched unhealthy`，立即停止移动并重建 FAST-LIO，不要继续等待。

长走廊中的“特征点”必须是雷达能看到的静态三维几何，例如门框、突出墙面的箱体、斜面或不对称角结构，建议尺寸至少大于 `0.3-0.5m`，并让其中一部分表面法向沿走廊方向。只贴 AprilTag、二维码、反光贴或地面图案不会帮助当前 FAST-LIO，因为当前匹配不使用相机图像或点云 intensity。经过开门房间/三维特征时减速或短暂停留，左右转动让雷达同时看到门框、房间侧墙和角点；走廊尽头分段转向，不要原地快速完成 180 度转弯。RViz 中一旦看到同一门框或房间轮廓出现双层，应立即停止继续写图。

当前 FAST-LIO 没有位姿图回环，走完整个回程不能自动修正已经形成的历史地图；走廊模式和三维特征只能减少漂移，不能替代后续真正的回环/多传感器约束。

## 4. 定位与导航：使用导航预设

先运行场景选择器。它打印 `RVIZ POINT CLOUD READY` 后即可打开导航预设查看成品点云和定位候选，不必等 Nav2 启动；定位未 ready 时不要发送导航目标。

导航预设的 Fixed Frame 默认是 `map`，包含：

| 图层 | 话题 | 正常现象 |
|---|---|---|
| Map | `/map` | 保存的 2D PGM 地图，静态不变 |
| map (scans.pcd) | `/pcd_map` | Open3D 成品 3D PCD，静态不变 |
| live/candidate scan preview | `/scan2map` | 紫色实时扫描；先按未验证猜测显示，有候选后更新位置，不代表已完成定位验证 |
| LaserScan | `/scan` | 机器人附近实时障碍扫描 |
| Path | `/g1_robot/plan` | Nav2 规划路径；发目标后才出现 |
| registered cloud (FAST-LIO) | `/cloud_registered_1` | 实时世界点云，应与成品地图重合 |
| body cloud (robot live scan) | `/cloud_registered_body_1` | 橙色机器人实时点云，用于确认雷达当前回波 |
| TF | `/tf`、`/tf_static` | 应具备 `map -> odom -> g1_robot/base_footprint` 链 |

定位前以高亮蓝色 `/pcd_map` 和二维 `/map` 识别机器人真实位置；紫色 `/scan2map` 应持续刷新，未得到候选时只证明实时点云链路正常，有候选后可用它判断扫描是否贴近蓝色成品 PCD。定位成功后，`/pcd_map`、绿色 `/cloud_registered_1` 与 `/map` 的墙体轮廓应重合。`/cloud_registered_body_1` 已作为橙色图层预置并默认开启，它随机器人移动属于正常定义；判断世界地图是否对齐时以绿色 `/cloud_registered_1` 为准，必要时只取消 Body 图层勾选，不需要删除或重新 Add。

`Global Costmap (optional)` 和 `Local Costmap (optional)` 也已预置但默认关闭；需要检查 Nav2 障碍层或滚动窗口时直接勾选即可，不需要 Add。

导航时推荐使用 `TopDownOrtho` 查看 2D 地图、路径和目标；检查 PCD 高度与实时点云重合时临时切回 `Orbit`。Fixed Frame 始终保持 `map`。

## 5. 在 RViz2 发初始位姿与导航目标

只有在 Fixed Frame=`map` 时才能发布这两个工具消息。

### 手工初始位姿（仅自动定位失败时）

正常情况下，保持机器人静止，等待 FPFH/RANSAC 自动初始化和日志 `Localization ready`。只有长期无法形成 `3/3` 一致候选时才操作：

1. 先确认高亮蓝色 `/pcd_map` 可见；如果它也为空，停止操作并检查 localization，而不是盲点。
2. 在 RViz2 工具栏选择 `2D Pose Estimate`。
3. 在蓝色 PCD/二维 `/map` 上机器人实际位置处按下左键并拖动。
4. 拖动箭头方向必须与机器人当前朝向一致；长度不重要。
5. 确认定位日志出现 `Manual relocalization applied`，并继续等待 `Localization ready` 和连续 `ICP: accepted=true`。

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
| 蓝色 `/pcd_map` 也完全没有 | 等场景选择器打印 `RVIZ POINT CLOUD READY`，再确认 `docker compose ps localization` 为 `Up`；静态 PCD 不依赖定位 TF |
| `map` 下只有绿色/橙色实时点云 Warm | `/localization_ready=false` 时没有经验证的 `map` TF 是预期保护；用蓝色 PCD 发初始位姿或等待自动定位 |
| 发初始位姿后被拒绝 | Fixed Frame 设为 `map`，用 `2D Pose Estimate` 重新发送 |
| 发目标后没有路径 | 先确认 `Localization ready`、Nav2 lifecycle active，以及 `/scan`、TF、定位置信度均通过 preflight |
| 点云或 scan 同时停止 | 查 FAST-LIO 日志中的 `FAST_LIO_TIMING`、`FAST_LIO_GUARD` 和 `output latched unhealthy` |
| Intel/Mesa 报 `active samplers...` | 使用 `RVIZ_RENDERING=software` 重开对应脚本；不要修改话题或 TF |

现场完整命令见 [建图导航指令.md](建图导航指令.md)，完整验收、切图和故障分析见 [机器人项目run.md](机器人项目run.md)。

## 7. 机器人端底层通信报错

如果机器人端出现：

```text
ddsi_udp_conn_write to udp/192.168.123.161 failed
G1Write locomotion Move failed: code=3104
```

这是 `bringup` 里的 Unitree SDK 与机器人本体控制器之间的底层链路故障，不是 RViz2 或 Zenoh 7448 故障。此时 `/Odometry_loc`、TF 和 `/scan` 可能不完整，不能继续判断建图质量。先在机器人宿主机检查：

```bash
ip -br addr
ip route get 192.168.123.161
ping -c 3 -W 1 192.168.123.161
```

`3104` 的 SDK 定义是 `Call api timeout error`；同时常见的 `7301` 是
`LocoState not available`。即使上述 ping 成功，若这两个码持续出现，仍表示
机器人本体 locomotion API 没有正常响应，不能发送导航目标。

确认机器人已开机、连接控制器的网线/网口存在，且 `botbrain_ws/robot_config.yaml` 中的 `network_interface` 与实际网卡一致。该项目当前 G1 配置使用 `enP8p1s0`；不要把工作站连接 Zenoh 的无线网卡误当成 Unitree 控制网卡。

另外，启动基础服务请使用后台模式：

```bash
docker compose up -d zenoh bringup state_machine
```

不加 `-d` 只会把容器日志附着到当前终端，不是 RViz2 连接方式。若提示 `g1_robot_foxglove` 是 orphan container，可以忽略；它不影响 RViz2。只有确认以后不再使用 Foxglove 时才单独删除该容器，不要随意使用 `--remove-orphans`，以免误删现场仍需要的相机容器。
