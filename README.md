# iOS Location Studio

> A visual control panel that simulates an iPhone's location over Apple's own DVT developer channel.
> No jailbreak. No MFi certificate. No accessory impersonation.

在浏览器里为 iPhone 模拟定位。点地图 → 选时长 → 开始，手机上的地图、天气、指南针和 App 会一起跟着走。

![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-22d3ee)
![License](https://img.shields.io/badge/license-MIT-34d399)

---

## 为什么不是 iAP2

很多开源方案走的是 **iAP2 配件通道**：把自己伪装成一个 MFi 车载配件（CarKit），再通过 `com.apple.carkit.service` 给 iPhone 喂 NMEA 定位语句。

这条路在 iOS 27 上会卡在一个很隐蔽的地方。实测数据（iPhone 15 / iOS 27.0.1）：

| 环节 | 结果 |
| --- | --- |
| USB lockdown | ✅ 连通 |
| CarKit service | ✅ 成功打开 |
| 配件认证 | ✅ `identification_accepted` + `authentication_succeeded` |
| 定位包发送 | ✅ 154 个包全部 `location_link_acknowledged` |
| **地图蓝点** | ❌ **一次都没动** |

日志里是这样一个循环：

```
location_requested → location_stopped → location_requested → location_stopped ...
```

手机反复发起订阅又立刻放弃。**链路层 ACK 只证明数据被收到，不证明系统采纳。** 认证通过等于"这把钥匙能开门"，不等于"你有权限用这个房间"。iOS 对第三方配件上报的位置有独立的采纳策略，而 `location_requested/stopped` 的死循环就是它拒绝的信号。

**本项目的做法完全不同**：走 `com.apple.instruments.server.services.LocationSimulation`，也就是 Xcode 里 "Simulate Location" 用的那条官方调试通道。它不冒充任何硬件，iOS 明确把它当作"模拟位置"注入，全系统覆盖，不存在"要不要采纳"的博弈。

---

## 特性

- **地图点选** — 点击世界任意位置，标记落点、自动解析地名
- **城市搜索** — 内置 Nominatim 搜索，输入"巴塞罗那"直达
- **20 个快捷地点** — 时代广场、太阳门广场、涩谷、外滩……
- **倒计时会话** — 1 分钟到不限时，剩余时间实时显示
- **一键恢复** — 停止会话，iOS 立刻回到真实 GPS
- **实时设备信息** — 设备名、iOS 版本、Build、UDID 后缀
- **暗色 / 标准底图** — 一键切换
- **零配置启动** — `pip install` 后一条命令，自动开浏览器
- **跨平台** — Windows / macOS / Linux 同一套代码

---

## 安装

需要 Python 3.11 或更新版本。

```bash
git clone https://github.com/YEZH0/ios-location-studio.git
cd ios-location-studio
pip install -e .
```

或者直接装依赖跑源码：

```bash
pip install pymobiledevice3 fastapi "uvicorn[standard]"
python -m ios_location_studio
```

> **中文用户名用户注意**：如果你的用户目录含中文（例如 `C:\Users\张三\`），`pip install -e .` 生成的 `.pth` 文件可能被 Python 按 GBK 解码导致 `ModuleNotFoundError`。
> 改用非可编辑安装即可：`pip install .`（或 `uv sync --no-editable`）。

---

## 开始使用

### 1. iPhone 侧准备（只需一次）

1. 用 USB 数据线连接电脑，解锁手机，弹"要信任此电脑吗"时点**信任**
2. **设置 → 隐私与安全性 → 开发者模式** → 打开（打开后需重启一次）
3. 确认能连上：`pymobiledevice3 usbmux list` 能看到设备

> 开发者模式是 DVT 通道的硬前提。iOS 16 及以上才有这个菜单。

### 2. 启动控制台

```bash
ios-location-studio
```

终端会打印地址并自动打开浏览器（默认 `http://127.0.0.1:8899`，端口被占用时自动顺延）。

```
  iOS Location Studio 0.1.0
  ---------------------------------------------
  控制台   http://127.0.0.1:8899/
  接口文档 http://127.0.0.1:8899/docs
```

### 3. 模拟定位

1. 地图上点选目标，或搜城市，或点快捷地点
2. 选持续时间（1/5/10/30 分钟，或不限时）
3. 点 **开始模拟**，等 3~10 秒隧道建立
4. 打开 iPhone 的**苹果地图**，就位

**停止**：点 **停止并恢复真实定位**，或直接 `Ctrl+C` 关掉服务。

---

## 工作原理

```
浏览器 UI (Leaflet 地图)
        │  HTTP / JSON
        ▼
FastAPI 本地服务  ──  单例 SessionManager
        │                  │  保持 asyncio 上下文存活
        │                  ▼
        │         UserspaceRsdTunnel  (USB, 无需管理员)
        │                  ▼
        │            DvtProvider
        │                  ▼
        │      LocationSimulation.set(lat, lon)
        ▼
   每秒轮询 /api/status
```

关键点是**会话必须一直活着**。`LocationSimulation` 的上下文一旦退出，iOS 立刻回落到真实 GPS——这也是 `pymobiledevice3 developer dvt simulate-location set` 命令看起来"没生效"的原因：它设置完会等按键，非交互执行时立即退出，通道当场断开。

本项目用后台 `asyncio.Task` 持有隧道，只在用户点停止、时长到期或进程退出时才释放。

---

## 限制

- **只在会话存活期间有效**。停止、拔线、进程崩溃、电脑休眠，都会让 iOS 立刻恢复真实定位。
- **必须走 USB**，不支持 Wi-Fi 连接。
- **需要开发者模式**。关闭后会失败。
- **重启设备后**可能需要重新确认信任关系。
- **部分 App 会检测**。银行、游戏反作弊、企业 MDM 类应用可能识别模拟位置并拒绝服务，这不是本项目能绕过的。
- **iOS 大版本升级后 API 可能变化**，若失效请先升级 `pymobiledevice3`。

---

## 故障排查

| 现象 | 原因与处理 |
| --- | --- |
| 界面显示"未检测到 iPhone" | 数据线只充电不传数据；换线换口；重新解锁并信任 |
| 点开始后卡在"正在建立隧道" | 开发者模式没开，或手机锁屏。解锁后重试 |
| 建立成功但地图蓝点不动 | 用**苹果地图**验证（第三方 App 有缓存）；确认会话仍在倒计时 |
| 提示 `DeveloperModeStatus` 相关错误 | 设置里打开开发者模式并重启设备 |
| `ModuleNotFoundError` | 中文路径 + editable 安装，改 `pip install .` |
| 端口被占用 | 自动顺延到 8900+，或 `--port 9001` |

调试日志：

```bash
ios-location-studio --no-browser
```

---

## 合规声明

**本项目仅供开发、测试与教学使用。**

适用于：调试依赖定位的 App、测试地理围栏逻辑、演示 LBS 功能、隐私研究。

**不得用于**：考勤作弊、游戏定位作弊、规避监管或司法监控、冒充他人行踪、任何形式的欺诈。

模拟定位会改变设备上报的位置，可能影响依赖位置的紧急服务（如紧急呼叫定位）。使用者需自行承担全部责任。作者不对任何滥用行为负责。

本项目调用的 `LocationSimulation` 是 Apple 提供给开发者的公开调试接口，不涉及越狱、不修改系统分区、不伪造硬件身份、不绕过设备安全机制。

---

## 致谢

- [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) — 整个 DVT 通道的实现基础
- [Leaflet](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/) + [CARTO](https://carto.com/) — 地图
- [Nominatim](https://nominatim.org/) — 地理编码
- [FastAPI](https://fastapi.tiangolo.com/) — 本地服务

## License

[MIT](LICENSE)
