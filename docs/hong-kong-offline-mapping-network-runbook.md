# 香港无网络楼层 G1 建图网络部署手册

> 适用场景：机器人和专用调试电脑都在香港；深圳可以远程控制香港调试电脑，香港调试电脑当前可以 SSH 到机器人；最终建图、Foxglove 和地图保存全部在香港完成。
>
> 目标：在 12、14、15 楼没有建筑 Wi-Fi 的情况下，建立一套不依赖互联网、重启后可恢复、能够稳定传输 ROS 2 点云的本地网络。

---

## 1. 最终目标与优先级

按以下顺序选择网络方案：

1. 验收机器人现有自带热点。如果稳定、带宽足够且重启后自动恢复，直接使用。
2. 自带热点不合格时，使用便携路由器。优先让机器人通过短网线连接路由器，香港调试电脑连接路由器 Wi-Fi。
3. 机器人没有可用外部网口时，让机器人和调试电脑同时连接便携路由器 Wi-Fi。
4. 便携路由器故障时，使用机器人 AP 模式或静态 IP 网线直连。

推荐的便携路由器拓扑：

```text
机器人 Jetson --短网线-- 便携路由器 LAN
                              ))) Wi-Fi
香港调试电脑 --------------------+

可选：香港手机 --USB 共享-- 便携路由器
      仅用于保持深圳远程桌面，不承载 ROS 点云
```

建图本身不需要互联网。互联网只用于深圳远程协助、安装软件和传回地图。

---

## 2. 固定网络规划

所有新建的建图网络统一使用以下地址，避免和 Unitree 常见的 `192.168.123.x` 内部网络混淆：

| 设备 | 地址 |
|---|---|
| 便携路由器 | `10.77.0.1/24` |
| 机器人 | `10.77.0.30/24` |
| 香港调试电脑 | DHCP，建议路由器保留为 `10.77.0.10` |
| DHCP 地址池 | `10.77.0.100-10.77.0.199` |
| Foxglove WebSocket | `10.77.0.30:8765/tcp` |
| Zenoh（机器人内部/可选诊断） | `10.77.0.30:7448/tcp` |

无线网络建议：

| 用途 | SSID | 设置 |
|---|---|---|
| 主网络 | `G1-MAP-HK-5G` | 5 GHz，信道 36，WPA2-AES |
| 备用网络 | `G1-MAP-HK-24G` | 2.4 GHz，信道 6，20 MHz，WPA2-AES |

密码使用至少 12 位 ASCII 字符，不要使用空格、中文或特殊引号。本文用 `<MAP_PSK>` 表示实际密码。

---

## 3. 需要准备的物品

建议在深圳准备并完成桌面测试：

- 双频便携路由器两台，一主一备。
- 路由器必须支持路由模式、DHCP、LAN 口、5 GHz、关闭客户端隔离、USB-C 供电。
- 如果需要深圳持续远程控制，路由器还应支持手机 USB Tethering、SIM 或其他 WAN 接入。
- Linux 兼容 USB 千兆网卡两个，优先 RTL8153 或 AX88179 芯片。
- Cat6 短网线两条，另带一条备用长网线。
- 20000mAh 充电宝和两套供电线。
- USB 键盘、便携显示器或 HDMI 线，作为完全失去网络时的救援手段。
- U 盘，保存本仓库、文档、地图备份和必要的 `.deb` 安装包。
- 标签纸，标记路由器管理地址、SSID、密码、机器人 IP 和网口用途。

普通 USB 4G 网卡只会让单台设备上网，不能替代本地路由器。普通手机热点也可能存在客户端隔离、WPA3 或信道兼容问题，不作为主方案。

---

## 4. 操作边界

### 4.1 现在可以远程完成

- 审查香港机器人和调试电脑的网络接口。
- 安装网络检查工具和 Foxglove Desktop。
- 确认机器人自带热点的来源和能力。
- 在机器人上预创建未来的有线/Wi-Fi 配置，但不激活。
- 在香港调试电脑上预创建未来路由器的 Wi-Fi 配置，但不激活。
- 检查映射程序、Foxglove Bridge 和 Zenoh 监听配置。

### 4.2 到香港后再执行

- 激活会替换当前网络的连接配置。
- 切换机器人 Wi-Fi 到 AP 模式。
- 将香港调试电脑切换到无互联网的建图 Wi-Fi。
- 插拔 USB 网卡、网线和路由器并检查 carrier。
- 断电重启和实际点云带宽验收。

远程阶段不要关闭当前连接，不要修改 Unitree/LiDAR 内部网口，不要删除当前可用的 Wi-Fi 配置。

---

## 5. 香港调试电脑安装依赖

以下命令假设调试电脑使用 Ubuntu 22.04。使用 Foxglove WebSocket 时，调试电脑不需要安装 ROS 2 或 `rmw_zenoh_cpp`；可视化全部通过 Foxglove Desktop 完成。

```bash
sudo apt update
sudo apt install -y \
  network-manager iw rfkill ethtool iproute2 iputils-ping \
  netcat-openbsd openssh-client iperf3 tmux
```

### 5.1 安装 Foxglove Desktop

无互联网楼层应使用提前安装好的 Foxglove Desktop，不要依赖现场打开 `app.foxglove.dev`。

1. 在有互联网时从 [Foxglove Download](https://foxglove.dev/download) 下载适用于 Ubuntu 的 `.deb` 安装包。
2. 将安装包保存到香港调试电脑和出行 U 盘。
3. 在安装包所在目录执行：

```bash
sudo apt install ./foxglove-studio-*.deb
```

如果实际下载文件名不同，使用其真实文件名：

```bash
sudo apt install ./CHANGE_ME_FOXGLOVE_PACKAGE.deb
```

验证网络工具和 Foxglove 安装：

```bash
nmcli --version
iperf3 --version
dpkg -l | grep -i foxglove || true
command -v foxglove-studio || true
```

浏览器版仅作为有互联网时的备用方式：打开 `https://app.foxglove.dev`，选择 `Open connection` -> `Foxglove WebSocket`。

---

## 6. 机器人安装依赖

机器人宿主机先确认当前网络管理方式：

```bash
systemctl is-active NetworkManager || true
systemctl is-active systemd-networkd || true
```

如果 `NetworkManager` 已经是 `active`，可以继续使用本文的 `nmcli` 指令。若它不是当前网络管理器，不要在远程阶段安装、启用或切换 NetworkManager，否则可能立即中断现有 SSH；相关切换只能留到现场处理。

安装不会切换网络管理器的检查工具：

```bash
sudo apt update
sudo apt install -y \
  iw rfkill ethtool iproute2 iputils-ping curl \
  netcat-openbsd openssh-server iperf3 tmux

sudo systemctl enable --now ssh
```

确认机器人或容器中已安装 Foxglove Bridge 和 Zenoh：

```bash
test -f /opt/ros/humble/setup.bash && echo "ROS 2: OK"
dpkg -l | grep ros-humble-rmw-zenoh || true
dpkg -l | grep ros-humble-foxglove-bridge || true
source /opt/ros/humble/setup.bash 2>/dev/null || true
ros2 pkg executables rmw_zenoh_cpp 2>/dev/null || true
ros2 pkg executables foxglove_bridge 2>/dev/null || true
```

如果 ROS 节点运行在容器中，还要在实际运行映射程序的容器中确认：

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
export MAPPING_CONTAINER='CHANGE_ME_MAPPING_CONTAINER'
docker exec "$MAPPING_CONTAINER" bash -lc \
  'source /opt/ros/humble/setup.bash && ros2 pkg executables rmw_zenoh_cpp'

export FOXGLOVE_CONTAINER='g1_robot_foxglove'
docker exec "$FOXGLOVE_CONTAINER" bash -lc \
  'source /opt/ros/humble/setup.bash && ros2 pkg executables foxglove_bridge'
```

容器缺少 Zenoh 时按照 [Zenoh 跨机器通信部署指南](zenoh-deploy-guide.md) 安装。缺少 Foxglove Bridge 时，需要在构建该容器镜像时安装 `ros-humble-foxglove-bridge`，不要只临时安装后就删除容器。

---

## 7. 远程审查香港调试电脑

在香港调试电脑执行：

```bash
mkdir -p ~/g1_network_audit

{
  date
  hostnamectl
  cat /etc/os-release
  ip -br link
  ip -br -4 addr
  ip route
  nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
  nmcli -f NAME,TYPE,DEVICE,AUTOCONNECT connection show
  nmcli -f NAME,TYPE,DEVICE connection show --active
  rfkill list
  iw dev
} | tee ~/g1_network_audit/workstation.txt
```

记录当前 SSH 使用的机器人地址，并检查路径：

```bash
export CURRENT_ROBOT_IP='<当前机器人IP>'

ip route get "$CURRENT_ROBOT_IP"
ping -c 10 "$CURRENT_ROBOT_IP"
nc -vz "$CURRENT_ROBOT_IP" 22
```

扫描附近热点：

```bash
nmcli -f IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY device wifi list
```

重点记录当前调试电脑的 Wi-Fi 接口名称、当前 SSID、机器人 IP，以及 SSH 走有线还是无线。

---

## 8. 远程审查机器人

从香港调试电脑 SSH 到机器人后执行：

```bash
mkdir -p ~/g1_network_audit

{
  date
  hostnamectl
  cat /etc/os-release
  ip -br link
  ip -br -4 addr
  ip route
  ip neigh
  nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
  nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
  nmcli -f NAME,TYPE,DEVICE connection show --active
  nmcli radio
  rfkill list
  iw dev
  lsusb
  ip -br link show type bridge
  bridge link 2>/dev/null || true
  ps -ef | grep -E 'hostapd|dnsmasq' | grep -v grep || true
  sudo ss -lunp | grep -E ':53 |:67 |:68 ' || true
  ss -lntp | grep -E ':7448|:8765' || true
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
} | tee ~/g1_network_audit/robot.txt
```

列出每个以太网接口的地址和物理链路状态：

```bash
for IFACE in $(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="ethernet"{print $1}'); do
  echo "===== $IFACE ====="
  ip -4 addr show dev "$IFACE"
  printf 'carrier='
  cat "/sys/class/net/$IFACE/carrier" 2>/dev/null || echo unknown
  ethtool "$IFACE" 2>/dev/null | grep -E 'Speed:|Duplex:|Link detected:' || true
done
```

安全规则：

- 带有 `192.168.123.x`、连接 Unitree 控制器或 LiDAR 的接口是内部接口，不得修改。
- `ip a` 只显示本机接口，不会显示远端机器人。
- 远端设备使用 `ping`、`ip neigh`、路由器客户端列表和已知静态 IP 查找。

---

## 9. 判断机器人是否自带热点

### 9.1 Jetson 自己开 AP 的特征

- `iw dev` 显示某个接口的 `type AP`。
- NetworkManager 存在 Wi-Fi AP 连接。
- 机器人 Wi-Fi 地址常见为 `10.42.x.1`。
- `dnsmasq` 或 NetworkManager 正在监听 DHCP `67/udp`。

查询连接详情：

```bash
nmcli -f NAME,TYPE,DEVICE connection show --active
nmcli connection show '<疑似热点连接名称>'
```

### 9.2 独立硬件路由器的特征

- 机器人系统中没有 `type AP`、`hostapd` 或本地 DHCP 服务。
- 机器人只是通过以太网/Wi-Fi 从某个网关获取地址。
- 默认网关可能有独立管理页面。

```bash
DEFAULT_GW=$(ip route | awk '/^default/{print $3; exit}')
echo "$DEFAULT_GW"
ip neigh show "$DEFAULT_GW"
curl -I --connect-timeout 2 "http://$DEFAULT_GW" 2>/dev/null || true
```

### 9.3 Unitree 原生热点

如果热点名称明显属于 Unitree，或直接使用 `192.168.123.x` 内部网段，在完成带宽、重启和 ROS 验收前，不要将其作为正式建图网络，也不要修改其内部地址。

---

## 10. 验收机器人现有热点

让香港调试电脑连接机器人热点，然后设置实际地址：

```bash
export AP_ROBOT_IP='<机器人热点网络中的IP>'
export ROBOT_USER='CHANGE_ME_ROBOT_USER'
```

基础测试：

```bash
ip route get "$AP_ROBOT_IP"
ping -c 100 "$AP_ROBOT_IP"
nc -vz "$AP_ROBOT_IP" 22
nc -vz "$AP_ROBOT_IP" 8765
nc -vz "$AP_ROBOT_IP" 7448 || true
ssh "$ROBOT_USER@$AP_ROBOT_IP"
```

带宽测试，先在机器人执行：

```bash
iperf3 -s
```

再在调试电脑执行：

```bash
iperf3 -c "$AP_ROBOT_IP" -t 30
iperf3 -c "$AP_ROBOT_IP" -R -t 30
```

合格标准：

- `100` 次 ping 丢包率为 `0%`。
- 本地平均延迟最好低于 `10 ms`。
- 双向带宽至少 `50 Mbps`，建议超过 `100 Mbps`。
- `22/tcp` 和 Foxglove `8765/tcp` 可连接。
- Zenoh `7448/tcp` 只在需要从调试电脑直接运行 ROS 2 CLI 时要求开放。
- 机器人断电重启后热点自动恢复。
- Foxglove 点云连续运行至少 30 分钟无明显断流。

满足全部条件时，可使用机器人现有热点作为主方案，便携路由器作为备用。

---

## 11. 深圳配置便携路由器

在路由器管理页面设置：

```text
工作模式：Router / 路由模式
LAN 地址：10.77.0.1
子网掩码：255.255.255.0
DHCP：开启
DHCP 范围：10.77.0.100-10.77.0.199
AP Isolation / Client Isolation：关闭
Guest Network：关闭
隐藏 SSID：关闭
WPA3-only：关闭
```

主 Wi-Fi：

```text
SSID：G1-MAP-HK-5G
安全：WPA2-PSK / AES
信道：36
带宽：40 MHz；稳定后可测试 80 MHz
```

备用 Wi-Fi：

```text
SSID：G1-MAP-HK-24G
安全：WPA2-PSK / AES
信道：6
带宽：20 MHz
```

便携路由器没有 WAN 时也必须继续提供 DHCP 和本地交换。不要选择会关闭 DHCP 的纯 AP/桥接模式。

### 11.1 深圳桌面验收

1. 一台 Linux 电脑通过 LAN 模拟机器人，设置为 `10.77.0.30/24`。
2. 第二台设备连接 `G1-MAP-HK-5G`。
3. 验证第二台设备可以 ping 和 SSH 到 `10.77.0.30`。
4. 手机通过 USB 给路由器共享网络。
5. 验证第二台设备既能访问 `10.77.0.30`，也能访问互联网。
6. 使用充电宝连续运行至少两小时。
7. 路由器断电重启三次，确认配置不丢失。

Linux 模拟机器人静态地址示例：

```bash
export TEST_ETH='<测试电脑有线接口>'

sudo nmcli connection add type ethernet ifname "$TEST_ETH" \
  con-name G1-ROUTER-TEST \
  ipv4.method manual ipv4.addresses 10.77.0.30/24 \
  ipv4.never-default yes ipv6.method disabled

sudo nmcli connection up G1-ROUTER-TEST
```

---

## 12. 远程预创建机器人有线配置

只有确认了外部管理网口后才能执行。假设真实外部接口为 `<MAP_ETH_IF>`：

```bash
export MAP_ETH_IF='<MAP_ETH_IF>'
```

先再次确认它不是 Unitree/LiDAR 内部接口：

```bash
ip -4 addr show dev "$MAP_ETH_IF"
ethtool "$MAP_ETH_IF" 2>/dev/null | grep -E 'Link detected:|Speed:' || true
```

创建配置但不主动激活：

```bash
sudo nmcli device set "$MAP_ETH_IF" managed yes
sudo nmcli connection delete G1-MAP-LAN 2>/dev/null || true

sudo nmcli connection add \
  type ethernet \
  ifname "$MAP_ETH_IF" \
  con-name G1-MAP-LAN \
  connection.autoconnect yes \
  connection.autoconnect-priority 200 \
  ipv4.method manual \
  ipv4.addresses 10.77.0.30/24 \
  ipv4.never-default yes \
  ipv6.method disabled

nmcli connection show G1-MAP-LAN
```

远程阶段不要执行 `nmcli connection up G1-MAP-LAN`。到香港接好路由器 LAN 和网线后再激活。

如果机器人尚未插入将来要使用的 USB 网卡，其接口名和 MAC 无法可靠预知。应先把该 USB 网卡送到香港并插入后远程配置，或者到现场再执行本节。

---

## 13. 远程预创建机器人 Wi-Fi 客户端配置

这是机器人无法通过网线连接便携路由器时的备用方案。

自动检测真实 Wi-Fi 接口：

```bash
MAP_WIFI_IF=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="wifi"{print $1; exit}')
echo "MAP_WIFI_IF=$MAP_WIFI_IF"
test -n "$MAP_WIFI_IF" || echo "ERROR: 未检测到 Wi-Fi 接口"
```

创建 5 GHz 配置，但暂不自动连接：

```bash
export MAP_PSK='<MAP_PSK>'

sudo rfkill unblock wifi
sudo nmcli radio wifi on
sudo nmcli device set "$MAP_WIFI_IF" managed yes
sudo nmcli connection delete G1-MAP-WIFI-5G 2>/dev/null || true

sudo nmcli connection add type wifi \
  ifname "$MAP_WIFI_IF" \
  con-name G1-MAP-WIFI-5G \
  ssid G1-MAP-HK-5G

sudo nmcli connection modify G1-MAP-WIFI-5G \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$MAP_PSK" \
  802-11-wireless.cloned-mac-address permanent \
  connection.autoconnect no \
  connection.permissions "" \
  ipv4.method manual \
  ipv4.addresses 10.77.0.30/24 \
  ipv4.never-default yes \
  ipv6.method disabled
```

到现场需要切换到无线方案时，确保有线配置不活动：

```bash
sudo nmcli connection down G1-MAP-LAN 2>/dev/null || true
sudo nmcli connection up G1-MAP-WIFI-5G
```

同一台机器人不要让有线和 Wi-Fi 同时使用 `10.77.0.0/24`。

---

## 14. 远程预创建香港调试电脑 Wi-Fi 配置

检测接口：

```bash
PC_WIFI_IF=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="wifi"{print $1; exit}')
echo "PC_WIFI_IF=$PC_WIFI_IF"
```

创建主网络配置，但远程阶段不要激活：

```bash
export MAP_PSK='<MAP_PSK>'

sudo nmcli connection delete G1-MAP-HK-5G 2>/dev/null || true
sudo nmcli connection add type wifi \
  ifname "$PC_WIFI_IF" \
  con-name G1-MAP-HK-5G \
  ssid G1-MAP-HK-5G

sudo nmcli connection modify G1-MAP-HK-5G \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$MAP_PSK" \
  802-11-wireless.cloned-mac-address permanent \
  connection.autoconnect yes \
  connection.permissions "" \
  ipv4.method auto
```

创建 2.4 GHz 备用配置：

```bash
sudo nmcli connection delete G1-MAP-HK-24G 2>/dev/null || true
sudo nmcli connection add type wifi \
  ifname "$PC_WIFI_IF" \
  con-name G1-MAP-HK-24G \
  ssid G1-MAP-HK-24G

sudo nmcli connection modify G1-MAP-HK-24G \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$MAP_PSK" \
  802-11-wireless.cloned-mac-address permanent \
  connection.autoconnect no \
  connection.permissions "" \
  ipv4.method auto
```

警告：如果香港调试电脑当前通过 Wi-Fi 提供深圳远程桌面，激活新配置会中断远程会话。远程阶段只创建，不执行 `nmcli connection up`。

---

## 15. 到香港后的便携路由器组装

按顺序执行：

1. 给便携路由器供电并等待启动完成。
2. 如果需要深圳保持远程连接，先将香港手机通过 USB 共享给便携路由器，确认路由器已有 WAN。
3. 香港调试电脑连接 `G1-MAP-HK-5G`。
4. 用短网线连接机器人外部网口和路由器 LAN，不能插到配置为 WAN 的端口。
5. 检查机器人外部接口 carrier 为 `1`。
6. 激活机器人 `G1-MAP-LAN`。
7. 从香港调试电脑执行 ping、SSH、Foxglove Bridge 和 ROS topic 验收。

机器人执行：

```bash
export MAP_ETH_IF='<MAP_ETH_IF>'

cat "/sys/class/net/$MAP_ETH_IF/carrier"
sudo nmcli connection up G1-MAP-LAN
ip -4 addr show dev "$MAP_ETH_IF"
ping -c 3 10.77.0.1
```

香港调试电脑执行：

```bash
export ROBOT_USER='CHANGE_ME_ROBOT_USER'
sudo nmcli connection up G1-MAP-HK-5G

ip -br -4 addr
ip route get 10.77.0.30
ping -c 10 10.77.0.30
nc -vz 10.77.0.30 22
nc -vz 10.77.0.30 8765
nc -vz 10.77.0.30 7448 || true
ssh "$ROBOT_USER@10.77.0.30"
```

如果 `carrier=0`，先处理线缆、USB 网卡、驱动和端口问题，不要继续排查 ROS。

---

## 16. 机器人 AP 模式备用方案

机器人 Wi-Fi 必须明确支持 AP：

```bash
MAP_WIFI_IF=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="wifi"{print $1; exit}')
nmcli -f GENERAL.DEVICE,WIFI-PROPERTIES.AP,WIFI-PROPERTIES.2GHZ,WIFI-PROPERTIES.5GHZ \
  device show "$MAP_WIFI_IF"
```

显示 `WIFI-PROPERTIES.AP: yes` 后，现场创建热点：

```bash
export MAP_PSK='<MAP_PSK>'

sudo nmcli connection delete G1-MAP-AP 2>/dev/null || true
sudo nmcli connection add type wifi \
  ifname "$MAP_WIFI_IF" \
  con-name G1-MAP-AP \
  connection.autoconnect no \
  ssid G1-ROBOT-AP

sudo nmcli connection modify G1-MAP-AP \
  802-11-wireless.mode ap \
  802-11-wireless.band a \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$MAP_PSK" \
  ipv4.method shared \
  ipv4.addresses 10.77.0.1/24 \
  ipv6.method disabled
```

激活会断开机器人当前 Wi-Fi SSH，只能在现场或有第二条管理链路时执行：

```bash
sudo nmcli connection up G1-MAP-AP
```

香港调试电脑连接 `G1-ROBOT-AP` 后，机器人地址为 `10.77.0.1`，Foxglove 连接地址相应改为 `ws://10.77.0.1:8765`。

5 GHz AP 启动失败时改成 2.4 GHz：

```bash
sudo nmcli connection modify G1-MAP-AP 802-11-wireless.band bg
sudo nmcli connection up G1-MAP-AP
```

---

## 17. 静态 IP 网线直连备用方案

只有便携路由器不可用时使用。机器人端设置：

```bash
export MAP_ETH_IF='<机器人外部网口>'

sudo nmcli connection delete G1-DIRECT 2>/dev/null || true
sudo nmcli connection add type ethernet \
  ifname "$MAP_ETH_IF" \
  con-name G1-DIRECT \
  ipv4.method manual \
  ipv4.addresses 10.77.0.30/24 \
  ipv4.never-default yes \
  ipv6.method disabled

sudo nmcli connection up G1-DIRECT
```

香港调试电脑端设置：

```bash
export PC_ETH_IF='<电脑有线接口>'

sudo nmcli connection delete G1-DIRECT-PC 2>/dev/null || true
sudo nmcli connection add type ethernet \
  ifname "$PC_ETH_IF" \
  con-name G1-DIRECT-PC \
  ipv4.method manual \
  ipv4.addresses 10.77.0.10/24 \
  ipv4.never-default yes \
  ipv6.method disabled

sudo nmcli connection up G1-DIRECT-PC
ping -c 10 10.77.0.30
```

Type-C 数据线本身不会自动形成以太网。只有两端支持并配置 USB Ethernet/Gadget 时才会产生可用网络接口。

---

## 18. Foxglove Bridge 与 ROS 2 验收

### 18.1 机器人端

先启动映射程序。本项目映射脚本会启动 `rmw_zenohd`，Foxglove Bridge 再通过机器人本机 Zenoh 接收 ROS 2 topic：

```bash
docker exec -it 3d_nav_ros2 \
  /g1_3d_nav_ros2/tools/mapping/mapping_launch.sh
```

在另一个机器人终端启动或重启 Foxglove 服务：

```bash
export ROBOT_PROJECT_ROOT='/absolute/path/to/botbrain_project'
cd "$ROBOT_PROJECT_ROOT"
docker compose up -d foxglove
docker logs --tail 100 g1_robot_foxglove
```

确认 Foxglove Bridge 对所有外部接口监听 `8765/tcp`：

```bash
ss -lntp | grep ':8765'
docker ps --filter name=g1_robot_foxglove
```

预期监听地址为 `0.0.0.0:8765`。项目配置位于 `botbrain_ws/src/bot_bringup/config/foxglove_bridge_params.yaml`，已经包含 `/cloud_.*`、`/accumulated_grid`、`/Odometry_loc`、`/tf` 和 `/tf_static` 等映射 topic。

如果 `8765` 没有监听：

```bash
docker logs --tail 200 g1_robot_foxglove
ss -lntp | grep ':7448' || true
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

先确认映射程序的 Zenoh router 正常，再重启 Foxglove Bridge：

```bash
docker restart g1_robot_foxglove
```

容器名称或项目路径不同时，先通过 `docker ps` 和部署目录确认，不要直接猜测。

### 18.2 香港调试电脑端

先验证网络和 Foxglove 端口：

```bash
export G1_IP=10.77.0.30
ping -c 10 "$G1_IP"
nc -vz "$G1_IP" 8765
```

打开 Foxglove Desktop：

1. 选择 `Open connection`。
2. 选择 `Foxglove WebSocket`。
3. 输入 `ws://10.77.0.30:8765`。
4. 连接后确认 topic 列表持续更新。

建图布局至少添加：

| 面板 | Topic/设置 |
|---|---|
| 3D | Fixed Frame 使用 `camera_init` |
| PointCloud2 | `/cloud_registered_1` |
| OccupancyGrid | `/accumulated_grid` |
| Pose/Odometry | `/Odometry_loc` |
| Transform | `/tf`、`/tf_static` |

判断世界地图是否漂移时主要查看 `/cloud_registered_1`，不要用会随机器人身体倾斜的 `/cloud_registered_body_1` 代替世界点云。

出发前在 Foxglove 中保存并导出建图 Layout，确保离线启动 Foxglove Desktop 后可以直接载入。更完整的面板和参考系说明见 [Foxglove Studio 使用指南](../foxglove-guide.md)。

### 18.3 可选：从调试电脑直接使用 ROS 2 CLI

Foxglove 正常使用不需要本节。只有调试电脑已经安装 ROS 2 Humble 和 `rmw_zenoh_cpp`，并且需要执行 `ros2 topic` 命令时才配置：

```bash
export G1_IP=10.77.0.30
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_CONFIG_OVERRIDE="mode=\"client\";connect/endpoints=[\"tcp/${G1_IP}:7448\"]"

ros2 daemon stop 2>/dev/null || true
ros2 daemon start
sleep 3
ros2 topic list
ros2 topic info /Odometry_loc
ros2 topic info /accumulated_grid
```

该诊断方式要求机器人 `7448/tcp` 可达；Foxglove WebSocket 只要求 `8765/tcp` 可达。

---

## 19. 防火墙检查

机器人执行：

```bash
if command -v ufw >/dev/null 2>&1; then
  sudo ufw status
else
  echo "ufw 未安装，跳过 ufw 检查"
fi
```

只有显示 `Status: active` 时才添加规则：

```bash
sudo ufw allow from 10.77.0.0/24 to any port 22 proto tcp
sudo ufw allow from 10.77.0.0/24 to any port 8765 proto tcp
# 只有调试电脑需要直接运行 ROS 2 CLI 时才开放：
sudo ufw allow from 10.77.0.0/24 to any port 7448 proto tcp
sudo ufw status numbered
```

不要为了排障直接永久关闭全部防火墙。

---

## 20. 深圳远程控制不中断方案

建图期间，香港调试电脑的本地 ROS 链路和互联网链路应分开：

```text
香港调试电脑 Wi-Fi -> 便携路由器 -> 机器人本地 ROS
便携路由器 WAN -> 香港手机 USB 共享 -> 深圳远程桌面
```

如果调试电脑当前依赖建筑 Wi-Fi 提供远程桌面，而直接切换到一个无 WAN 的建图 Wi-Fi，深圳远程会话会断开。因此现场切换前，先完成以下任意一项：

- 手机 USB 共享给便携路由器。
- 手机 USB 共享直接给香港调试电脑。
- 调试电脑使用有线互联网，Wi-Fi 专门连接建图网络。

原始点云、Foxglove 和 Zenoh 保持在香港本地运行。跨境网络仅传远程桌面画面和最终地图文件。

---

## 21. 常见故障与处理顺序

### 21.1 网线连接后无法 ping

```bash
export CHECK_IF='CHANGE_ME_INTERFACE'
cat "/sys/class/net/$CHECK_IF/carrier"
ip -br -4 addr
ip route
ip neigh
```

- `carrier=0`：物理线缆、USB 网卡、供电、驱动或端口问题。
- `carrier=1` 但无 IP：NetworkManager 配置没有激活。
- 双方 IP 不在同一 `/24`：修正静态地址。
- ping 通但 `8765` 不通：检查 Foxglove Bridge 容器、监听地址和防火墙。
- `8765` 正常但 Foxglove 没有 topic：检查机器人内部 Zenoh router、Foxglove Bridge 日志和 topic 白名单。

### 21.2 机器人不能连接便携路由器 Wi-Fi

```bash
export MAP_WIFI_IF='CHANGE_ME_WIFI_INTERFACE'
sudo rfkill unblock wifi
sudo nmcli radio wifi on
sudo nmcli device wifi rescan ifname "$MAP_WIFI_IF"
nmcli -f SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY \
  device wifi list ifname "$MAP_WIFI_IF"
journalctl -b -u NetworkManager --no-pager | tail -n 200
```

依次检查：

- 配置中是否错误写死为 `wlan0`。
- SSID 和密码是否完全一致。
- 是否为 WPA3-only。
- 是否使用 DFS/高信道导致机器人扫描不到。
- Wi-Fi 是否被 rfkill 阻塞或 NetworkManager 标记为 unmanaged。
- 保存的连接是否 `connection.autoconnect yes`。

### 21.3 手机 USB 共享和手机热点不能互访

这是常见现象。手机通常把 USB 共享客户端和 Wi-Fi 热点客户端放在不同子网，并通过 NAT/防火墙隔离。不要把这种组合当作 ROS 本地局域网。

### 21.4 Foxglove 无法连接或看不到 topic

先按层排查：

```bash
export G1_IP=10.77.0.30
ping -c 3 "$G1_IP"
nc -vz "$G1_IP" 8765                         # 调试电脑端
ss -lntp | grep 8765                         # 机器人端
docker ps --filter name=g1_robot_foxglove    # 机器人端
docker logs --tail 200 g1_robot_foxglove     # 机器人端
ss -lntp | grep 7448                         # 机器人内部 Zenoh
```

处理顺序：

1. ping 不通：先修复 IP、路由或物理网络。
2. ping 通但 `8765` 不通：启动 Foxglove Bridge 或修复防火墙。
3. `8765` 可连接但没有 topic：检查映射节点、Zenoh、Bridge 日志和 `foxglove_bridge_params.yaml` 白名单。
4. 能看到 topic 但 3D 无内容：检查 Fixed Frame、topic 选择和消息是否持续更新。

---

## 22. 现场最终验收清单

- [ ] 机器人内部 Unitree/LiDAR 网口未被修改。
- [ ] 路由器 LAN 为 `10.77.0.1/24`。
- [ ] 机器人稳定使用 `10.77.0.30/24`。
- [ ] 香港调试电脑能 ping 和 SSH 到 `10.77.0.30`。
- [ ] Foxglove `ws://10.77.0.30:8765` 可连接。
- [ ] Foxglove 能看到 `/cloud_registered_1`、`/accumulated_grid`、`/Odometry_loc`、`/tf` 和 `/tf_static`。
- [ ] Foxglove 3D Fixed Frame 为 `camera_init`，点云和累计栅格正常。
- [ ] 可选 ROS 2 CLI 场景下，`10.77.0.30:7448/tcp` 可连接。
- [ ] 100 次 ping 丢包率为 0%。
- [ ] 双向 iperf3 带宽至少 50 Mbps。
- [ ] 连续建图测试至少 30 分钟。
- [ ] 机器人、路由器和电脑断电重启三次后网络自动恢复。
- [ ] 手机互联网断开后，本地建图仍能继续。
- [ ] 手机互联网恢复后，深圳远程桌面可继续使用。
- [ ] USB 网卡、网线、路由器和供电均有备用件。
- [ ] UG、12、14、15 楼地图使用独立文件名并及时备份。

---

## 23. 出发前必须保存的信息

将以下信息写入离线文件并打印一份：

```text
机器人 SSH 用户名：
机器人当前可用 IP：
机器人建图 IP：10.77.0.30
机器人 Unitree/LiDAR 内部接口：
机器人外部管理接口：
机器人 Wi-Fi 接口：
香港调试电脑 Wi-Fi 接口：
路由器管理地址：10.77.0.1
主 SSID：G1-MAP-HK-5G
备用 SSID：G1-MAP-HK-24G
路由器管理员密码：
Wi-Fi 密码：
映射容器名称：
映射启动命令：
地图保存目录：
```

不要只把密码保存在依赖互联网的密码管理页面中。纸质副本和加密离线副本至少保留一种。
