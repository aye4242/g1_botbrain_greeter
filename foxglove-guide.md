# Foxglove Studio 使用指南（已弃用）

> 建图、定位和导航现已统一使用本地 RViz2，不再启动 Foxglove Bridge。请使用 [rviz-guide.md](rviz-guide.md)。本文件仅保留用于查阅旧记录。

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
| ✅ 定位验收 | `/localization_ready` | 初始化前为 `false`，只有经验证的 `map -> odom` 可用后才为 `true` |
| 🔵 可选 | `/pcd_map` | Open3D 使用的成品 3D 地图 |
| 🔵 可选 | `/g1_robot/global_costmap/costmap` | 全局代价地图 |
| 🔵 可选 | `/g1_robot/plan` | 规划路径 |
| 🔵 诊断 | `/g1_robot/nav_odom` | Nav2 使用的统一里程计：FAST-LIO 平面位姿 + Unitree twist |
| ⚠️ 谨慎开 | `/cloud_effected_1`、`/cloud_registered_body_1` | 实时局部点云/诊断点，容易让画面看起来像地图在变 |
| ❌ 建议关 | `/g1_robot/local_costmap/costmap` | 高频闪烁，10Hz；只在排查避障时临时打开 |
| ❌ 建议关 | `/g1_robot/trajectories` | MPPI 2000条轨迹，闪烁严重 |

---

## 4. 发布位姿工具

左侧 **发布** 栏配置，右侧3D工具栏点击图标使用：

| 工具 | 配置话题 | 作用 |
|------|---------|------|
| **2D 位姿估计** | `/initialpose` | 自动全局初始化失败时的手工回退，不让机器人动 |
| **2D 位姿** | `/g1_robot/goal_pose` | 让机器人导航到目标点 |
| **2D 点** | — | 用不到 |

### 如何准确发布初始位姿（2D 位姿估计）

正常启动时先保持机器人静止，等待 FPFH/RANSAC 从当前局部点云和完整 PCD 中自动求出绝对位置。机器人不在建图起点并不代表需要立即发送 `/initialpose`。只有 localization 日志长时间无法生成有效全局候选或无法完成 `3/3` 一致确认时，才执行以下手工步骤。

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

如果 navigation 持续输出 `The /scan observation buffer has not been updated for ... seconds`，这是 costmap 没有收到可用新 scan 的安全告警，不是 Foxglove 显示问题。`expected_update_rate: 1.0` 表示最大允许 1s 的更新间隔，不能把它关闭来隐藏断流。按下列顺序分层检查：

1. `/cloud_registered_body_1` 也无新数据：查 FAST-LIO/雷达、timing、guard 和 `output latched unhealthy`。
2. body 点云有数据但 `/scan` 没有消息：查 `body -> g1_robot/base_footprint` 的同时间戳 TF、pointcloud_to_laserscan 的订阅/QoS 和 message-filter 日志。
3. `/scan` 持续发布但 ranges 几乎全是 `inf`：话题没有断流，此时再对照 body 点云检查高度/距离过滤带和环境是否真的空旷。
4. `/scan` 新鲜但 costmap 仍告警：查 scan 到 `map`/`g1_robot/odom` 的 TF、话题类型冲突和是否还在运行旧 navigation 容器。

```bash
docker exec -it g1_robot_bringup bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic list -t | grep -E "^/(cloud_registered_body_1|scan)[[:space:]]"
  timeout 5 ros2 topic hz /cloud_registered_body_1 || true
  timeout 5 ros2 topic hz /scan || true
  timeout 3 ros2 run tf2_ros tf2_echo map g1_robot/base_footprint || true
  timeout 3 ros2 run tf2_ros tf2_echo g1_robot/odom g1_robot/base_footprint || true
'
```

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

动态清理的验收方法是：先确认 `/scan` 无断流，让行人进入再离开雷达可见区域，新增黑点应在后续空闲射线再次观测到该位置后清除。如果单独显示 `/map` 时黑点仍然存在，它是 PGM 静态内容，costmap clearing 和清空 service 都不会改写地图文件。

global inflation 当前是 `inflation_radius=0.35m`、`cost_scaling_factor=15.0`。`0.35m` 覆盖机器人加 padding 后约 `0.34m` 的外接半径，而较高的 scaling factor 让外围软代价更快衰减。不要只根据颜色叠加宽度继续缩小安全半径。

如果黑点已经影响导航，可清理动态 costmap：

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 service call /g1_robot/global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap {}
  ros2 service call /g1_robot/local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap {}
'
```

### local costmap 看起来没有以机器人为中心

local costmap 是 `g1_robot/odom` 坐标系下 `8m x 8m` 的 rolling window。先检查 Foxglove 左侧 `/g1_robot/local_costmap/costmap` 的眼睛图标：图层为灰色且眼睛带删除线时，它实际处于隐藏状态，该截图不能证明 costmap 偏移。

打开图层后，用 costmap 消息自身的时间戳查 TF，比凭透视截图更可靠：

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 run bot_navigation costmap_center_check.py
'
```

默认允许两个 `0.05m` 栅格，即 `error<=0.10m`。失败时查 `g1_robot/odom -> g1_robot/base_footprint` 的同时间戳 TF，不要手工修改 costmap origin。

### 里程计位姿和 TF 看起来不一致

Nav2 应使用 `/g1_robot/nav_odom`，它把 FAST-LIO `/Odometry_loc` 的平面 pose/yaw 与 Unitree `/g1_robot/odom` 的 twist 组合到同一消息，从而让 pose 与 `odom -> base_footprint` TF 共享同一个 FAST-LIO 状态。原 `/g1_robot/odom` 的 pose 不用于判定导航 TF 对齐，也不能作为 `/initialpose`。

```bash
docker exec -it g1_robot_navigation bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic info -v /g1_robot/nav_odom
  timeout 5 ros2 topic hz /g1_robot/nav_odom || true
'
docker compose logs --tail 120 navigation | \
  grep -E "Nav odom relay|coherent planar nav odometry|Unitree odometry twist.*stale"
```

`/g1_robot/nav_odom` 应只有一个 relay publisher。如果 Unitree twist 超时，relay 会发布零速并输出 stale 告警，应先修复 odom 断流再导航。

### `/map` 不显示
1. 确认 `localization` 已用机器人所在楼层启动，例如：`MAP_SCENE=floor4 docker compose --profile navigation up -d --force-recreate localization`
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
如果这只是 Foxglove bridge 对不受支持 schema 的显示警告，且 `ros2 topic list -t` 已确认 `/scan` 只有 `sensor_msgs/msg/LaserScan`、真实数据持续到达，则不影响 Nav2。这与 costmap 的 `observation buffer has not been updated` 是两类问题；后者不能忽略。

### 定位启动后直接报地图场景不匹配

导航使用的 PCD、YAML 和 PGM 必须来自同一次建图，标准命名是 `<scene>_scans.pcd`、`<scene>.yaml`、`<scene>.pgm`，YAML 的 `image` 必须指向该 PGM。定位服务通过唯一变量 `MAP_SCENE` 直接选择整套地图，不再依赖 `scans.pcd`、`accumulated.yaml` 软链接。启动代码会硬性校验三文件，不一致时 localization 将直接退出，不会带着错地图进入 Foxglove/Nav2。

```bash
cd /data/unitree/botbrain_ws
export MAP_SCENE=floor4  # 或 ug、floor1 等实际场景名
maps=botbrain_ws/src/g1_pkg/maps

pcd="$maps/${MAP_SCENE}_scans.pcd"
yaml="$maps/${MAP_SCENE}.yaml"
pgm="$maps/${MAP_SCENE}.pgm"
test -s "$pcd" && test -s "$yaml" && test -s "$pgm"
image=$(sed -n 's/^[[:space:]]*image:[[:space:]]*//p' "$yaml" | head -n 1)
image=${image#\"}; image=${image%\"}; image=${image#\'}; image=${image%\'}
case "$image" in
  /*) image_path=$image ;;
  *)  image_path="$(dirname "$yaml")/$image" ;;
esac
test "$(realpath -e "$image_path")" = "$(realpath -e "$pgm")"

# 到达目标楼层、机器人停稳并取消活动目标后，先确认 source/install
# 的 mid360.yaml 均为 pcd_save_en: false，再重建 FAST-LIO 高度基准
docker compose stop navigation localization fast_lio
docker compose rm -f localization fast_lio
docker compose up -d --force-recreate fast_lio
docker compose logs -f fast_lio | \
  grep -E "IMU Initial Done|FAST_LIO_TIMING|FAST_LIO_GUARD"

# 看到 IMU Initial Done 且点云稳定后 Ctrl+C，再用新场景重建 localization
docker compose --profile navigation up -d --force-recreate localization

# 查看容器要求的场景
docker inspect g1_robot_localization \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^MAP_SCENE='

# 等待 launch 选择结果、ready 和 accepted 后 Ctrl+C
docker compose logs -f localization | \
  grep -E "Map selection:|Global localization initialization succeeded|Localization ready|ICP: accepted|ERROR|FATAL"

# 再查看节点最终加载的文件
docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 param get /global_localization_node path_map
  ros2 param get /map_server yaml_filename
'
```

等待日志出现 `Global localization initialization succeeded`、`Localization ready`，并完成 ICP/TF 验收后，才执行 `docker compose --profile navigation up -d --force-recreate navigation`。跨楼层必须重建 FAST-LIO，使 `camera_init` 在当前层重新建立；不要通过解锁定位 Z 约束来保留跨层 odom。`docker compose restart localization` 不会切图；`MAP_SCENE` 未设置时默认回到 `ug`。禁止仅调用 `map_server/load_map`，因为它不会同步更换 Open3D PCD。更完整的首次启动、持久化选择、waypoint 楼层边界和高级显式路径覆盖见 `机器人项目run.md` 的 **四、多楼层建图与切换**。

---

## 6. 自动初始化与手工 `/initialpose` 回退

定位服务会先使用 FPFH/RANSAC 将当前局部点云与完整 PCD 做全局匹配，然后要求三个不同点云窗口给出一致候选。正常日志顺序为：

```text
Global initialization: enabled=true ... confirmations=3 scan_window=3
Prepared ... map points for FPFH global initialization
Global candidate seed=... RANSAC=... fitness=... rmse=...
LocalizationInitialize: holding consistent global candidate (.../3) ...
Global localization initialization succeeded: ...
Localization ready: verified map->odom is now available
```

启动时 `/localization_ready=false`；只有最后验证通过后才变为 `true`。在 ready 之前，系统不会发布伪装已定位的 `map -> odom`，navigation 的 preflight 也不会放行。机器人是否位于建图起点不再决定是否手工发初始位姿。

```bash
docker compose logs -f localization | \
  grep -E "Global initialization|Prepared .*FPFH|Global candidate|LocalizationInitialize|localization initialization succeeded|Localization ready|Manual relocalization"

docker exec -it g1_robot_localization bash -lc '
  source /opt/ros/humble/setup.bash
  source /botbrain_ws/install/setup.bash
  ros2 topic echo --once --qos-durability transient_local \
    --qos-reliability reliable /localization_ready
'
```

navigation 容器先延迟 30s，再由 preflight 最多等待 300s，因此从 `docker compose up -d navigation` 到 Nav2 开始启动要允许 330s 以上。日志 `Waiting for navigation inputs` 中的五项必须同时通过：`scan=true`（`/scan` 新鲜度 1s）、`twist_odom=true`（`/g1_robot/odom` 新鲜度 0.5s、child frame 正确且平面 twist 有限）、`ready=true`、`confidence>=0.55` 且新鲜度 1s、`tf=true`（有效平面 `map -> base_footprint`）。只有出现 `Navigation preflight passed` 后才会执行 Nav2 launch；300s 超时时容器退出，修复输入后必须再显式启动 navigation。

只有日志长时间反复出现 `did not produce a valid FPFH/RANSAC candidate`、`rejecting global candidate` 或候选始终无法累积到 `3/3` 时，才使用 `/initialpose` 手工回退。`/Odometry_loc`、`/g1_robot/odom`、`/localization_3d` 和现有 map TF 均不是独立的外部绝对位姿，不能自动转发到 `/initialpose`，否则会形成循环确认。

### 手工回退时的 z 值

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

成功时 localization 日志必须依次出现 `Manual relocalization applied`、`Local localization initialization succeeded` 和 `Localization ready`，且 `/localization_ready=true`。若没有第一条日志，先检查 `/initialpose -> /initialpose_corrected` 的 publisher/subscriber 链路。不要连续反复发布 initialpose，每次手工位姿都会使正在计算的旧 ICP 候选失效。

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
