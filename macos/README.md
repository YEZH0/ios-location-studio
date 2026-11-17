# iOS Location Studio · macOS

独立 PySide6 桌面应用，**默认 DVT 开发者定位**；iAP2 作为实验选项保留。
作者：欧耶哥爱数码 / iOS Location Studio contributors；上游 aur3l14no/accessory-location。
本子项目 GPL-3.0-only，根项目和 Windows 代码、许可证不变。

## 本机使用

打开 `dist/iOS Location Studio.app`，确认顶部选择 **DVT 开发者定位 · 推荐**。
本机已完成开发者连接准备；断开、重启或系统升级后如提示需准备，可再次点击准备按钮。

1. 用 USB 连接一台 iPhone，解锁并信任 Mac，点击“检测 USB”。
2. 手机需要已开启开发者模式；软件不会替你自动开启或降低安全设置。
3. 如需首次准备，点击“准备开发者连接”。会先显示 Apple 数据流同意框：
   官方 devicectl 可能向 Apple 发送 ECID、芯片/主板编号、nonce、镜像摘要申请票据；
   不发送模拟坐标或 MFi 私钥。准备需要本机完整 Xcode 与可用的开发者镜像。
4. 选择城市/离线地图点或输入 WGS-84 坐标；DVT 测试最长180秒，快捷档1/3分钟。
5. 点击“开始模拟”，确认坐标；在手机苹果地图点击当前位置，实际改变后点击人工确认。
6. 点击停止或等待到期。程序尝试清除 DVT 模拟并关闭隧道；断开 USB，在手机确认真实位置，
   再点击恢复确认。清除请求或进程退出不能代替手机实际恢复验证。

2026-11-17：新版打包 GUI 在 iPhone15 / iOS27.0.1 已通过纽约定位及停止恢复验证，
老板确认蓝点移动并恢复真实位置。其他设备/iOS版本不保证成功。

## 两种路线

- **DVT（推荐）**：使用开发者通道，无需 MFi 材料；本次已在独立脚本和打包 GUI 验证成功。
- **iAP2（实验）**：需要外部 DER PKCS#7 证书与匹配的 PKCS#8 P-256 私钥。
  选择此路线后展开认证设置。当前设备有认证/ACK却不采纳位置的记录，不能承诺生效。

两种路线均不会把“请求发送成功”或ACK自动标记为手机定位成功。
运行时路线/坐标/时长禁止改动；未确认恢复时阻止下一次模拟。
离线世界图不是街道导航图；不请求在线瓦片或地理编码，不上传坐标。

## 源码安装与运行

需要 macOS、Python3.11+、uv。普通用户可以双击 `scripts/install.command`，再双击 `scripts/run.command`。
终端运行（工作目录 macos/）：

```sh
python3 -m uv sync --locked
python3 -m uv run --no-sync ios-location-studio-mac
```

首次安装依赖需要网络；发送阶段不再下载依赖。DVT工作进程只允许本机回环IP和USB所需Unix通信，
iAP2发送禁止IP网络。官方准备流程与发送进程分开，准备前必须确认Apple数据流。

独立脚本也复用 GUI 的同一实现：

```sh
uv run --no-sync python scripts/prepare_dvt.py --allow-apple-ticket
sandbox-exec -f scripts/dvt-local-only.sb .venv/bin/python scripts/test_dvt.py \
  --latitude 40.7128 --longitude -74.0060 --duration 90
```

坐标需换成用户确认的目标；脚本不自行索取票据、不下载MFi身份。

## 故障与恢复

- 无设备：检查数据线、解锁、信任；多台USB设备时拒绝自动选取。
- 需准备开发者连接：确认已安装完整 Xcode、开发者模式开启，点击准备按钮并处理手机授权。
- DVT通道已连接但位置没变：在苹果地图请求当前位置，保持会话；不能仅看发送状态判成功。
- 清除失败或位置残留：停止、断开USB，关闭定位服务约10秒再开启，手机确认真实位置。
- iAP2认证失败：检查材料格式、匹配与设备接受；本地匹配不证明 Apple 授权、撤销状态或权限。
- 工作进程启动失败：界面显示失败与恢复指引；不输出私钥、设备标识或原始错误内容。
- 停止时为DVT清除保留最多15秒，超时才清理进程组；连接/测试也有总时限。

不越狱、不关闭SIP/Gatekeeper、不修改无关配置、不设置开机自启。
开发者镜像可保留用于后续调试；清除定位不等于卸载镜像或还原所有开发状态。

## 构建与发行状态

```sh
python3 -m uv run --no-sync pytest -q
python3 -m uv run --no-sync python scripts/build.py
```

输出 `dist/iOS Location Studio.app` 和当前HEAD的 `dist/macOS-source.zip`。
构建会收集 pymobiledevice3 的递归依赖元数据，避免源码可跑而打包DVT启动失败。
当前本地为arm64、ad-hoc签名，**无 Developer ID 签名或 Apple 公证**；Intel未验证。
公开二进制发行前仍需独立QA、安全、依赖对应源码与许可证审查，见THIRD_PARTY_NOTICES.md。
本轮54项本地测试通过；实机详情见TEST_REPORT.md，iAP2调查见RESEARCH.md。

仅修改 macos/ 与指定 Mac workflow。分支feat/macos-iap2，PR保持草稿，不推main、不自动合并。
源码提交用于备份；身份/配对数据保留在项目外，不打包、不提交。无生产部署或数据库迁移。
