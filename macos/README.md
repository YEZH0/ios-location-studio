# iOS Location Studio · macOS

独立 PySide6 桌面版，使用固定版本 accessory-location 的 USB iAP2/CarKit 引擎。
作者：欧耶哥爱数码 / iOS Location Studio contributors；上游 aur3l14no。
**实验性方案：认证、订阅、链路 ACK 和 iPhone 实际采用位置是不同状态。**

## 安装与启动

需要 macOS、Python 3.11+、USB 数据线。本次本地构建为 Apple Silicon；Intel 未验证。
在 Finder 双击 `scripts/install.command`，完成后双击 `scripts/run.command`。
安装脚本需要联网下载 PyPI 依赖；运行不需要下载地图、坐标或认证材料。
也可以在 macos/ 终端执行：

```sh
python3 -m uv sync --locked
python3 -m uv run --no-sync ios-location-studio-mac
```

应用依赖 macOS sandbox-exec，若系统移除或禁止它会安全失败，不自动降级为联网发送。
不需要越狱、修改 SIP 或安装开发者镜像；不主动配对或降低设备安全设置。

## 使用

1. 连接一台 iPhone，解锁并信任 Mac；点击“检测 USB 设备”。多台连接时拒绝自动选择。
2. 选择本地 DER PKCS#7 证书和匹配的非加密 DER PKCS#8 P-256 私钥。
   已有默认 `~/Library/Application Support/accessory-location/identity/` 时可自动填入路径。
   材料不复制进项目、不上传、不打包。GUI 不下载共享身份。
3. 点击“仅检查通信与认证”；probe 不发送位置。
4. 选择内置城市（可输入搜索）、点击离线经纬度网格，或输入 WGS-84 坐标。
   网格不是街道底图，不提供任意地址的在线解析；无第三方定位请求。
5. 设置 1–3600 秒时长（默认 180），确认坐标并开始。仅认证并收到订阅后才发送。
6. 在 iPhone 苹果地图点击当前位置，实际改变后点击人工确认按钮。
7. 点击停止或等待到期；工作进程和 helper 被清理。应用不声称已经恢复真实位置。
8. 断开 USB，在手机地图确认真实位置，再点击恢复确认。未确认恢复时禁止新模拟会话。

“断开会话”关闭本地协议连接，不代表物理 USB 已拔出，也不解除系统配对。
切勿在依赖真实位置的紧急服务场景中进行测试。

## 排查与恢复

- 无设备：检查数据线、USB、解锁与“信任”；本工具不会猜测密码或自动更改配对。
- 认证失败：格式和密钥匹配仅是本地检查，不能证明 Apple 信任、有效授权或撤销状态。
- 已认证、未订阅：打开苹果地图点击当前位置。
- 有 ACK、蓝点未动：不能判为成功；经用户确认后可关闭定位服务约 10 秒再打开并重试。
- 停止后位置残留：断开 USB，关闭定位服务约 10 秒再开启，重新请求当前位置。
- 无法恢复或协议错误：停止会话并保留“未验证”，不尝试降低设备安全设置。
- 关闭窗口先停止工作进程；正常停止发 SIGINT，超时后清理该进程组。
- 应用仅在内存显示脱敏事件，不落盘原始设备日志、密钥或配对数据。

## 构建

```sh
python3 -m uv run --no-sync pytest -q
python3 -m uv run --no-sync python scripts/build.py
```

输出 `dist/iOS Location Studio.app` 和 `dist/macOS-source.zip`。
**未进行 Developer ID 签名或 Apple 公证**；PyInstaller 的本地 ad-hoc 签名不等于 Apple 认证。
Gatekeeper 可能拦截其他电脑下载的应用；不建议关闭 Gatekeeper。可优先从源码运行。
目前不提供 DMG、不发布 GitHub Release；CI 工件仅用于构建审查。
源码 zip 来自当前 Git HEAD，分发前必须提交全部预期源码。
完整依赖对应源码与 notices 的公开发行核验仍待完成，详见 THIRD_PARTY_NOTICES.md。

## 证据与协作

见 TEST_REPORT.md。此前同聊天中上游工具在 iPhone 15 / iOS 27.0.1 经定位开关操作后，
用户确认纽约蓝点及恢复；这不是新桌面应用的真机验收。根 README 记录的失败属于另一组证据，
不据此推断所有 iOS 27 都失败或都兼容。新 Mac 应用端到端实机验证单独列为待完成。

仅修改 macos/ 与 .github/workflows/macos.yml；不调用或修改 Windows 包。
分支 feat/macos-iap2；不推 main，不自动合并。Windows 合并后先确认工作区干净，
fetch origin 并 merge origin/main，再测试和正常 push；若冲突涉及公共/Windows 文件，停止并报告。

## 许可与维护

本子项目独立 GPL-3.0-only，见 LICENSE、THIRD_PARTY_NOTICES.md。
保留上游完整固定版本源码与版权声明，未将 GPL 引擎作为 MIT 代码处理。
备份：保存源码提交与私有本地身份；恢复应用可切换至先前源码版本重建，不自动覆盖或删除身份。
无生产部署、数据库或自动启动服务。

## 可选 DVT 独立实验（已实机验证，不替换 GUI）

2026-11-17：iPhone 15 / iOS 27.0.1 的原始 iAP2 对照仍未改变地图；
独立 DVT 测试中，老板确认纽约蓝点生效，清除并断开后真实位置正常。
**当前 GUI 仍是 iAP2**，下面是独立实验脚本，不表示 iAP2 已修复。

要求：完整 Xcode、手机开发者模式已开启、USB 信任关系。不会自动开启开发者模式。
首次准备可能向 Apple 申请开发者镜像票据，包含设备标识和 nonce/镜像摘要。
必须取得用户对该数据流的同意后才执行带显式同意参数的准备命令。
本次老板已在聊天明确同意；准备使用 Apple 官方 devicectl，不使用第三方票据服务器。

```sh
# 工作目录 macos/；先完成 uv sync --locked
uv run --no-sync python scripts/prepare_dvt.py --allow-apple-ticket
# 请换成经用户确认的 WGS-84 坐标；测试阶段最长 180 秒
sandbox-exec -f scripts/dvt-local-only.sb .venv/bin/python scripts/test_dvt.py \
  --latitude 40.7128 --longitude -74.0060 --duration 90
```

运行中打开手机地图点击当前位置。`dvt_set_sent` 只表示请求已发送，必须人工验证蓝点。
脚本到期或收到 SIGINT/SIGTERM 会尝试 `clear` 并关闭隧道；异常时同样执行清理。
`dvt_clear_sent` 不替代真实定位恢复确认。结束后断开 USB 并在手机验证。
本次准备挂载的开发者镜像供开发者服务使用，清除定位不等同于卸载该镜像。
发送沙箱允许本机回环通信供 userspace 隧道使用，禁止外部 IP 通信。
不需要管理员权限、内核隧道、SIP/Gatekeeper 调整或 MFi 身份。
详见 RESEARCH.md。如需把 DVT 接入 GUI，另作明确的功能与发布审查。

## Mac 界面与 Windows 品牌对齐

参考 Windows 稳定分支的设备/会话/坐标控制台：左侧控制，右侧离线世界选点；
开始和停止固定在底部，认证与日志可展开。支持1/3分钟快捷时长、自定义时长、
快捷城市、坐标复制与标记同步、地图缩放/全球视图。小窗口可滚动控制区。
离线地图使用 Natural Earth 公共领域陆地轮廓，不请求在线地图服务；不包含街道或地标搜索。
本轮只改变界面与随包资源；默认仍是实验性 iAP2，DVT 仍使用独立脚本。
