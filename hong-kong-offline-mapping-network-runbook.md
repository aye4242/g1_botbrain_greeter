# 香港无 Wi-Fi 楼层建图网络手册

## 目录

- [1. 手机热点连接](#1-手机热点连接)
- [2. 移动 Wi-Fi 连接](#2-移动-wi-fi-连接)
- [3. 通过网线 SSH Jetson 并配置正式 Wi-Fi](#3-通过网线-ssh-jetson-并配置正式-wi-fi)

## 1. 手机热点连接

### 1.1 连接方式

```text
机器人 --Wi-Fi--> G1-PHONE <--Wi-Fi-- Linux 调试电脑
```

- 不使用 Type-C/USB 共享。
- 不需要网线或互联网。
- 手机热点：`G1-PHONE`，密码 `88888888`，2.4 GHz，WPA2。

### 1.2 保存热点和自动连接

执行位置：**当前已经 SSH 到机器人的终端**。切换热点前执行。

```bash
WIFI_IF=$(nmcli -t -f DEVICE,TYPE device |
  awk -F: '$2=="wifi"{print $1; exit}')

echo "WIFI_IF=$WIFI_IF"
cat "/sys/class/net/$WIFI_IF/address"

sudo nmcli connection delete G1-PHONE 2>/dev/null || true
sudo nmcli connection add type wifi ifname "$WIFI_IF" \
  con-name G1-PHONE ssid G1-PHONE
sudo nmcli connection modify G1-PHONE \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk 88888888 \
  ipv4.method auto \
  connection.autoconnect yes \
  connection.autoconnect-priority 5
```

保存机器人 Wi-Fi MAC。香港机器人必须使用自己的实际 MAC。

### 1.3 扫描并连接热点

执行位置：**机器人 SSH 终端**。

```bash
sudo nmcli radio wifi on
sudo nmcli device wifi rescan ifname "$WIFI_IF"

nmcli -t -f SSID,SIGNAL,SECURITY \
  device wifi list ifname "$WIFI_IF" --rescan yes |
  grep '^G1-PHONE:'
```

能看到 `G1-PHONE` 后连接：

```bash
sudo nmcli connection up G1-PHONE
```

SSH 断开是正常现象。机器人已从原网络切换到手机热点。

### 1.4 Linux 电脑通过 MAC 找机器人 IP

执行位置：**连接了 `G1-PHONE` 的 Linux 调试电脑**。

```bash
sudo apt update
sudo apt install -y nmap netcat-openbsd

ROBOT_MAC='CHANGE_ME_ROBOT_MAC'
PC_WIFI_IF=$(nmcli -t -f DEVICE,TYPE device |
  awk -F: '$2=="wifi"{print $1; exit}')
SUBNET=$(ip -4 route show dev "$PC_WIFI_IF" scope link |
  awk 'NR==1{print $1}')

sudo nmap -sn "$SUBNET" >/dev/null
ROBOT_IP=$(ip neigh show dev "$PC_WIFI_IF" |
  awk -v mac="$ROBOT_MAC" 'tolower($5)==tolower(mac){print $1; exit}')

echo "ROBOT_IP=$ROBOT_IP"
```

手机已经显示机器人 IP 时，可跳过扫描。MAC 只用于查 IP；SSH `22` 和 Foxglove `8765` 是固定端口。

### 1.5 SSH 和 Foxglove

执行位置：**Linux 调试电脑**。

```bash
ping -c 5 "$ROBOT_IP"
nc -vz "$ROBOT_IP" 22
nc -vz "$ROBOT_IP" 8765
ssh unitree@"$ROBOT_IP"
```

Foxglove：

```text
ws://机器人IP:8765
```

### 1.6 常见问题

- 机器人必须显示 Wi-Fi 接口连接 `G1-PHONE`，不能只通过 USB 连接手机。
- `192.168.123.x` 可能是 Unitree 内部网口，不是热点 IP。
- 两台设备连接同一热点但 ping 不通：手机启用了客户端隔离，直接使用第 2 部分。
- 手机给两个客户端分配不同 `/24` 网段时，不要手动改电脑 IP，直接使用移动路由器。

## 2. 移动 Wi-Fi 连接

### 2.1 路由器设置

执行位置：**移动 Wi-Fi/便携路由器管理页面**。

```text
模式：Router
SSID：G1-MAP
密码：88888888
安全：WPA2
DHCP Server：开启
AP/Client Isolation：关闭
Guest Network：关闭
WAN/互联网：不需要
```

移动路由器不需要 SIM、流量或互联网，只需要通电并提供本地 Wi-Fi 和 DHCP。

### 2.2 保存移动 Wi-Fi

执行位置：**机器人 SSH 终端**。切换网络前执行。

```bash
WIFI_IF=$(nmcli -t -f DEVICE,TYPE device |
  awk -F: '$2=="wifi"{print $1; exit}')

sudo nmcli connection delete G1-MAP 2>/dev/null || true
sudo nmcli connection add type wifi ifname "$WIFI_IF" \
  con-name G1-MAP ssid G1-MAP
sudo nmcli connection modify G1-MAP \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk 88888888 \
  ipv4.method auto \
  connection.autoconnect yes \
  connection.autoconnect-priority 6
```

### 2.3 扫描并连接移动 Wi-Fi

执行位置：**机器人 SSH 终端**。

```bash
sudo nmcli device wifi rescan ifname "$WIFI_IF"
nmcli -t -f SSID,SIGNAL,SECURITY \
  device wifi list ifname "$WIFI_IF" --rescan yes |
  grep '^G1-MAP:'

sudo nmcli connection up G1-MAP
```

SSH 断开后，让 Linux 电脑也连接 `G1-MAP`，再重复第 1.4、1.5 节。

### 2.4 常见问题

- 电脑和机器人都使用 Wi-Fi，不需要网线。
- 路由器必须开启 DHCP、关闭客户端隔离和 Guest Network。
- 在路由器 `Connected Devices/DHCP Clients` 中也可按机器人 MAC 查 IP。
- Foxglove `8765` 关闭时，在机器人项目目录执行：

```bash
docker compose up -d foxglove
ss -lntp | grep 8765
docker logs --tail 100 g1_robot_foxglove
```

## 3. 通过网线 SSH Jetson 并配置正式 Wi-Fi

### 3.1 用途和注意事项

连接方式：

```text
Linux 电脑 --网线--> Jetson 192.168.123.164
Jetson --Wi-Fi--> HUAWEI-AX6_5G
```

- 以下命令先在 Linux 电脑 SSH Jetson，再在机器人 SSH 终端执行。
- 原指令中的 `wlan0` 不一定正确，应先确认实际 Wi-Fi 接口。
- 深圳测试机器人实际接口是 `wlx94ba06f26399`。
- 正式 Wi-Fi 优先级 `10`；`G1-PHONE` 为 `5`；`G1-MAP` 为 `4`。
- 手动执行 `nmcli connection up <名称>` 会立即切换到指定 Wi-Fi，不受自动优先级限制。

### 3.2 步骤 0：SSH 连接 Jetson

执行位置：**通过网线连接机器人的 Linux 电脑**。

```bash
ssh unitree@192.168.123.164
```

### 3.3 步骤 1：查看网络设备并开启 Wi-Fi

执行位置：**机器人 SSH 终端**。

```bash
iwconfig
nmcli device status
rfkill list
nmcli radio
sudo nmcli radio wifi on
nmcli dev wifi list

WIFI_IF=$(nmcli -t -f DEVICE,TYPE device |
  awk -F: '$2=="wifi"{print $1; exit}')
echo "WIFI_IF=$WIFI_IF"
```

### 3.4 步骤 2：连接正式 Wi-Fi

执行位置：**机器人 SSH 终端**。

```bash
# 首次连接，会保存配置
sudo nmcli dev wifi connect HUAWEI-AX6_5G \
  password huawei7n \
  ifname "$WIFI_IF" \
  name HUAWEI-AX6_5G

# 验证连接
ip -4 -br addr show dev "$WIFI_IF"
nmcli connection show

# 启用已保存连接
sudo nmcli connection up HUAWEI-AX6_5G
```

### 3.5 步骤 3：设置开机自动连接

执行位置：**机器人 SSH 终端**。

```bash
sudo nmcli connection modify HUAWEI-AX6_5G \
  connection.autoconnect yes

sudo nmcli connection modify HUAWEI-AX6_5G \
  connection.autoconnect-priority 10

# 查看优先级
nmcli -f NAME,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY \
  connection show

# 立即切换到正式 Wi-Fi
sudo nmcli connection up HUAWEI-AX6_5G
```
