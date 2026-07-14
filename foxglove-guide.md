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
| ❌ 建议关 | `/g1_robot/local_costmap/costmap` | 高频闪烁，10Hz |
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

### `/map` 不显示
1. 确认 `localization` 服务在运行：`docker compose up fast_lio localization`
2. 固定参考系改为 `map`

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

若机器人在建图起始点附近，直接重启用默认值重初始化：
```bash
docker compose restart localization
```

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
