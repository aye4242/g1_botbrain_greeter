# 地图编辑器

G1 保存建图后会生成 `<场景名>.pgm` 和 `<场景名>.yaml`。清理孤立噪点、补墙和画入安全边界需要人工 GUI 操作，所以编辑器运行在 workstation，不运行在 G1 上。

完整的机器人保存、PCD 校正、质量检查、上传和地图重载流程以仓库根目录的 `机器人项目run.md` 为准。

整个流程就是：

```
G1 出图  ──►  工作站编辑  ──►  G1 上传并重载 map server
              （仓库 maps/）
```

本目录三样东西：

- `Dockerfile` — 工作站用的镜像（noetic + RViz + 已打补丁的 `ros_map_edit`）
- `start_map_edit.sh` — 启动脚本，处理 X11 转发、插件路径、清掉外面继承来的 `ROS_MASTER_URI`
- `ros_map_edit/` — 改过的 RViz 插件源码（见文末"打过的补丁"）

**先进仓库**（下面所有命令都假设你已经 cd 进来了）：

```bash
cd /home/aitech/Workspace/botbrain_project
```

---

## 一、第一次准备（只做一次）

构建镜像：

```bash
docker build -t map_edit_rviz:latest tools/host_side/map_edit
```

创建容器，把仓库里的 `maps/` 挂进去（这样改完地图 `git diff` 就能看到改了啥）：

```bash
docker run -d --name map_edit_rviz \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$PWD/botbrain_ws/src/g1_pkg/maps":/root/maps \
  map_edit_rviz:latest
```

容器跑的是 `sleep infinity`，启动脚本用 `docker exec` 进去干活。

> 之前用过旧版本（挂 `$HOME/g1_maps` 那种）的话，先 `docker rm -f map_edit_rviz` 删掉重建。

---

## 二、从 G1 拉地图

把 G1 上同一场景的 PGM/YAML 复制到本机仓库的 `botbrain_ws/src/g1_pkg/maps/` 下。以下以 `floor1` 为例：

```bash
scp unitree@<G1_IP>:/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml} \
  botbrain_ws/src/g1_pkg/maps/
```

YAML 使用相对图像路径，workstation 和机器人容器都能按 YAML 所在目录解析：

```bash
sed -i 's|^image:.*|image: floor1.pgm|' botbrain_ws/src/g1_pkg/maps/floor1.yaml
```

---

## 三、启动编辑器

```bash
tools/host_side/map_edit/start_map_edit.sh /root/maps/floor1.yaml
```

RViz 会弹出来。左边是 **File Management** 面板（绿色 **Save All Files** 按钮 + **Open Map** 按钮），工具栏多了 4 个工具：`MapEdit`、`VirtualWall`、`Region`、`MapEraser`。

如果面板没出来，看文末"常见问题"。

---

## 四、编辑

| 工具 | 干什么 | 怎么操作 |
|---|---|---|
| **MapEraser** | 涂改栅格（占据/空闲/未知） | 左键画黑（占据）、右键画白（空闲）、按住拖动连续涂 |
| **VirtualWall** | 保存两点线段元数据到 `<图>.json` | 左键点两次定两端、右键取消当前墙 |
| **Region** | 保存多边形区域元数据到 `<图>_region.json` | 左键添加顶点、右键闭合 |
| **MapEdit** | 模式切换器，决定上面哪个工具激活 | — |

笔刷大小、墙的颜色宽度等，在右边 **Tool Properties** 面板调。

> `VirtualWall` 和 `Region` JSON 当前没有接入主工程 Nav2。需要真实限制导航时，必须用 MapEraser 左键把边界直接画成 PGM 中的黑色占据栅格。

---

## 五、保存

点左边绿色的 **Save All Files**。会在 yaml 同目录写四个文件（同名覆盖）：

- `floor1.yaml` — 配置
- `floor1.pgm` — 图像（带修改内容）
- `floor1.json` — VirtualWall 编辑器元数据
- `floor1_region.json` — Region 编辑器元数据

弹个对话框告诉你存了啥。容器里写的是 `/root/maps/`，宿主机仓库的 `maps/` 立刻能看到，`git diff` 就是这次的改动。

---

## 六、推回 G1

`mode: trinary` 在编辑器保存时会丢失，必须补回；`image:` 继续保持相对路径：

```bash
yaml=botbrain_ws/src/g1_pkg/maps/floor1.yaml
sed -i 's|^image:.*|image: floor1.pgm|' "$yaml"
grep -q '^mode:' "$yaml" || sed -i '/^image:/a mode: trinary' "$yaml"
```

PGM/YAML 是 Nav2 必需文件：

```bash
scp botbrain_ws/src/g1_pkg/maps/floor1.{pgm,yaml} \
  "unitree@<G1_IP>":/data/unitree/botbrain_ws/botbrain_ws/src/g1_pkg/maps/
```

上传后必须重启或重新加载机器人上的 map server；仅覆盖磁盘文件不会让已经运行的 `/map` 自动更新。JSON 仅在需要保留编辑器元数据时另外上传。

---
