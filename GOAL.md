# GOAL — 目标总纲（持续执行，不许停止）

> 状态跟踪文件。每完成一项打勾并更新日期；发现新任务追加到对应里程碑，**不删除未完成项**。

## 使命

打造一款**普惠全球的全设备同声传译软件**，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0）开源引擎，
让任何人在游戏、小说、网页、会议、视频场景下都能零门槛跨语言沟通。

## 硬性需求（用户原始需求，全要）

- [x] 实时语音翻译字幕（麦克风 → ASR → 翻译 → 双语悬浮字幕）
- [ ] 屏幕文字 / OCR 翻译（游戏文本、小说、网页）
- [ ] 反向语音输出（TTS 朗读译文）
- [ ] 整篇阅读模式 + 结果可复制 / 导出
- [ ] 全平台（架构目标跨平台；Windows 先行，macOS/Linux 跟进）
- [x] **本地翻译为显性目标**：离线为主，API（`SIMUL_API_*`）仅可选
- [x] GitHub Actions 构建 + **tag 自动上传 Release**

## 技术决策（已定，见 DECISION.md）

组合式 Adopt：sherpa-onnx（ASR/VAD/TTS）+ Argos Translate（离线 NMT，英语枢纽 pivot）+ Tauri 2（壳）+ Python 管线子进程。

## 里程碑

### M0 — 原型闭环 ✅（2026-09-24）
- [x] 文件管线验证（wav → ASR → 离线NMT → 双语字幕，纯离线）
- [x] 视频端到端验证 + VAD 门控（8.9x 实时）+ 文本清洗
- [x] 翻译引擎层（语种检测 / pivot 路由 / 按需装包 / API 可选回落）
- [x] Tauri 悬浮字幕壳（透明置顶窗，读 Python 子进程 stdout）
- [x] CI：push 构建 artifact；**tag → 自动创建 Release 挂 NSIS 安装包**
- [x] CI：rust-cache（构建 5m → 2m23s）
- [x] CI 权限三坑修复（workflow permissions 块 / 仓库默认 write / rerun 不刷新权限快照）
- [x] Release v0.1.0 发布：https://github.com/lilyco-42/simul-overlay/releases/tag/v0.1.0

### M1 — 输入面扩展（进行中）
- [ ] 22 个语对包安装完成 + pivot 路由实测（zh→ja = zh→en→ja）🔄 批量安装后台跑着
- [x] **WASAPI loopback 系统声音捕获**（`demo_system.py`，实测通过 2026-09-24：48k 立体声 loopback → 16k 单声道 → 全管线字幕输出）
- [ ] 麦克风实测（⚠️ Blocked：等用户检查系统麦克风权限后跑 `demo_mic.py 60`）
- [ ] 多音源选择 UI（麦克风 / 系统声音 / 指定应用）

#### M1 途中修复的坑（2026-09-24）
- [x] Argos 语对下载 403：argos-net.com 拒 Python 默认 UA → 浏览器 UA + 只走 https（ipfs 回落会无限挂起）
- [x] `ensure_pair` 死锁：持 `Lock` 内重入 `installed_pairs()` → 改 `RLock`（此前所有下载路径必卡死）

### M2 — 输出面补全
- [ ] TTS 朗读译文（sherpa-onnx offline TTS，反向语音输出）
- [ ] 字幕历史面板 + 一键复制 / 导出 srt/txt
- [ ] 整篇阅读模式（段落重排、可读性版式）

### M3 — 屏幕文字翻译
- [ ] OCR 抓屏翻译（游戏文本、小说阅读器、网页选区）
- [ ] OCR 与字幕悬浮窗共存交互

### M4 — 分发体验
- [ ] 安装包全量化：模型/管线随包分发或首启按需下载（当前 1.68MB 壳仅指向本机 `SIMUL_PYTHON`）
- [ ] 语对包管理界面（已装/未装/下载进度）

### M5 — 跨平台
- [ ] macOS 构建（GitHub Actions matrix）
- [ ] Linux 构建（AppImage/deb）
- [ ] 移动端评估（Android/iOS 路线）

## 每日推进规则

1. 完成项打勾 + 注明日期；进行中标 🔄；阻塞标 ⚠️ 并写明解除条件。
2. **不停机**：当前任务完成即刻进入下一项；阻塞项跳过，继续其他里程碑。
3. 每个可交付动作完成后 commit + push；对外可见的里程碑打 tag 出 Release。
