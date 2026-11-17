# iOS Location Studio

> A visual control panel that simulates an iPhone's location over Apple's own DVT developer channel.
> No jailbreak. No MFi certificate. No accessory impersonation.

在浏览器里为 iPhone 模拟定位。点地图 → 选时长 → 开始，手机上的地图、天气、指南针和 App 会一起跟着走。

**作者：欧耶哥爱数码** · 详细教程见 [抖音 / 小红书同名](#视频教程)

![CI](https://github.com/YEZH0/ios-location-studio/actions/workflows/ci.yml/badge.svg)
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
- **限时会话** — 仅 1 分钟 / 3 分钟两档，到期自动恢复真实定位，剩余时间实时显示
- **一键恢复** — 停止会话，iOS 立刻回到真实 GPS
- **实时设备信息** — 设备名、iOS 版本、Build、UDID 后缀
- **暗色 / 标准底图** — 一键切换
- **零配置启动** — `pip install` 后一条命令，自动开浏览器
- **跨平台** — Windows / macOS / Linux 同一套代码

---

## 视频教程

**抖音 / 小红书 搜索「欧耶哥爱数码」** 领取详细使用教程，或直接扫码：

<p align="center">
  <img src="src/ios_location_studio/web/assets/follow-banner.jpg" alt="关注作者：欧耶哥爱数码（抖音 / 小红书）" width="760" />
</p>

| 平台 | 搜索词 | 内容 |
| --- | --- | --- |
| 抖音 | 欧耶哥爱数码 | 从零安装、开发者模式开启、首次连接全程录屏 |
| 小红书 | 欧耶哥爱数码 | 图文步骤、认证失败排查、多设备切换、常见报错对照 |

> 控制台侧栏的教程卡片里也放了这张图，点一下会放大到原尺寸，直接用手机扫。

装不上、连不上、建隧道卡住，先看教程，比翻 README 快。

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
2. 选持续时间（1 分钟或 3 分钟），到期自动恢复真实定位
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

## ⚠️ 免责声明

> **使用本工具前请完整阅读本节。控制台首次打开会强制弹出本节全文，未勾选同意无法开始模拟；继续操作即表示你已阅读、理解并接受全部条款。**

1. 本项目基于苹果 Xcode 调试私有 `DTSimulateLocation` 协议实现，**仅面向 iOS 开发者做定位相关功能技术研究**。
2. 本项目**仅用于验证 Apple Watch 健康功能地区限制（高血压通知）的技术实验**，禁止用于企业考勤打卡、游戏作弊、活动薅羊毛、轨迹造假、虚假报备等欺诈、规避风控场景。
3. 通过本工具跨地区解锁 Watch 医疗类功能，**违反 Apple 用户协议**；该健康通知未经过国内药监审批，**结果不能作为医疗诊断参考**。
4. 本工具只提供技术能力，不替任何人决定用途——**就像卖菜刀：刀能切菜，也可能被拿去伤人，卖刀的人不为用刀的方式负责**。同理，项目作者不对违规使用承担任何责任。衍生分发遵循原开源协议。
5. 开始之前请确认：**你本人自愿授权本工具修改这台设备的定位设置**，设备归你所有，或你已取得设备所有者的明确同意。给不出这份授权，就请立即关闭页面，不要把工具用在别人的设备上。

补充说明：

- 适用于：调试依赖定位的 App、测试地理围栏逻辑、演示 LBS 功能、隐私与合规研究。
- 会话时长上限 3 分钟（接口层强制，`hold_seconds` ≤ 180），到期自动恢复真实定位；需要更长的观察请重新开始一次。
- 模拟定位会改变设备上报的位置，可能影响依赖位置的紧急服务（如紧急呼叫定位）。
- 本项目调用的 `LocationSimulation` 是 Apple 提供给开发者的公开调试接口，不涉及越狱、不修改系统分区、不伪造硬件身份、不绕过设备安全机制。
- 控制台首次打开会弹出完整免责声明，侧栏底部常驻「免责声明」卡片，`/api/brand` 的 `disclaimer` 字段与每个 HTTP 响应的 `X-Usage-Policy` 头都会带上用途限定。

---

## 致谢

- [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) — 整个 DVT 通道的实现基础
- [Leaflet](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/) — 地图（暗色由 CSS 滤镜实现，不依赖需要 Key 的瓦片服务）
- [Nominatim](https://nominatim.org/) — 地理编码
- [FastAPI](https://fastapi.tiangolo.com/) — 本地服务

## 关于作者

**欧耶哥爱数码** · 抖音 / 小红书同名

做这个工具是因为找了一圈，能用的方案要么要越狱，要么要买 MFi 证书，要么在 iOS 27 上直接失效。踩完坑顺手整理成可视化工具，希望后来的人少走点弯路。

如果它帮到你，去主页点个关注就是最大的支持。控制台侧栏有抖音和小红书的二维码，扫一下就到。

## 转载与二次分发

本项目以 MIT 协议开源，**允许修改、允许再分发、允许商用**，但请保留以下四处署名与声明：

1. `README.md` 中的作者信息与免责声明
2. 界面侧栏的教程卡片与关注图（含抖音 / 小红书二维码）
3. 地图左下角的水印
4. 「免责声明」卡片（不得为了"看起来能用"而删掉用途限制）

这几处由后端 `brand.py` 统一下发，改模板删不掉。如果你在别处看到一个把这些字样全部去干净的版本，那不是原版，也别指望它能跟着更新。

发现有人盗版打包、去掉署名收费的，欢迎来抖音或小红书告诉我。

## License

[MIT](LICENSE)
