Tauri resources 打包源（随安装包分发，M4 离线全量包）：
  simul-pipe/  PyInstaller onedir 侧车（CI/本地: python build_sidecar.py 产出后拷入）
  models/      离线模型 + argos-packages 核心语对（python fetch_models.py 产出后拷入）
本 README 保证 glob `resources/*` 非空——开发构建未拷资源时打包仍不报错。
