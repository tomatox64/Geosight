# Geosight — 三维重建展示系统

## 项目概述

基于 Bentley ContextCapture + PyQt6 的倾斜摄影三维重建管线。8 个模块覆盖：数据导入 → 质控 → 补采 → 校准 → 融合 → 重建 → 导出 → 解译。

编辑器风格布局：左侧 56px 图标栏 + 中央 pyvista 3D 视口 + 右侧 300px 属性面板。模块 1-5 隐藏视口（全宽面板），模块 6-8 显示视口+面板并排。

## 环境

- **oymm** (Python 3.11, conda): 主应用 + PyQt6 + pyvista + Open3D + OpenCV
- **oymm-cc** (Python 3.6, conda): 仅用于 `scripts/cc_worker.py`，加载 CC SDK (ccmasterkernel)
- **CC Engine**: Bentley ContextCapture 10.20 @ `E:\Program\Bentley\ContextCapture`

**Python 路径** (不使用 `python` 命令，始终用完整路径):
- 主环境: `E:/Program/anaconda3/envs/oymm/python.exe`
- CC 环境: `E:/Program/anaconda3/envs/oymm-cc/python.exe`

## 架构关键约束

1. **跨版本桥接**: Python 3.11 主应用 → `subprocess.run()` → Python 3.6 cc_worker.py → CC SDK
   - `oymm_app/cc_bridge/engine.py` — 3.11 端，定义 `_call_worker(command, args, timeout)`
   - `scripts/cc_worker.py` — 3.6 端，接收 JSON 命令，调用 `ccmasterkernel`
   - 超时配置: AT=1800s, 生产=3600s, 其他=600s

2. **文件路径**: 使用正斜杠 `/`，绝对路径，盘符 `E:/`
   - 代码目录: `E:/oymm/`
   - 数据集: `E:/oymm/data/photos/<name>/images/`
   - 工程: `E:/oymm/projects/<name>/`
   - 输出: `E:/oymm/output/`
   - CC 引擎: `E:/Program/Bentley/ContextCapture/bin/CCEngine.exe`

3. **3D 视口**: `ViewportManager` 单例（`ui/viewport_manager.py`），per-module actor 管理。模块通过 `self._viewport` 引用添加 3D 内容。

4. **信号链**: 模块间数据传递通过 `data_ready` 信号 → `main_window._on_*_done` → 自动推进。模块 6 完成后会将真实数据回传给模块 3/4/5。

## 项目结构

```
oymm_app/
├── main.py                       # 入口: QApplication + MainWindow
├── ui/
│   ├── main_window.py            # 主窗口 (class MainWindow)
│   │   ├── MODULES[]             # 8 个模块的标题+描述
│   │   ├── _setup_ui()           # 布局: IconTabBar + QSplitter(Viewport | PropertyPanel)
│   │   ├── _switch_to_module(n)  # 模块切换 (0-4 隐藏视口, 5-7 显示)
│   │   ├── _on_recon_done()      # ★ 重建完成后分发真实数据到 3/4/5
│   │   └── _mark_completed(n)    # 标记完成，推进管线
│   ├── icon_tab_bar.py           # class IconTabBar — 56px 垂直图标栏
│   ├── viewport_manager.py       # class ViewportManager — pyvista 3D 视口
│   │   ├── add_mesh(id, mesh, **kw)   # 添加网格
│   │   ├── set_module_actors(id, [])  # 替换场景
│   │   └── activate_module(id)        # 切换活动模块
│   ├── property_panel.py         # class PropertyPanel — 右侧面板
│   │   ├── register_module(id, name, widget)  # 注册模块页面
│   │   ├── switch_to(id)                     # 切换面板
│   │   └── run_requested / next_requested    # 统一按钮信号
│   ├── module_*.py               # 8 个模块 UI 页面 (QWidget)
│   └── theme.qss                 # 全局 QSS 样式
├── modules/
│   ├── data_import.py            # DataImporter.scan_directory()
│   ├── quality_control.py        # QualityController.analyze_photos()
│   ├── resampling.py             # ResamplingAnalyzer — analyze() + analyze_from_poses()
│   ├── calibration.py            # CalibrationEngine — calibrate(tie_points=?)
│   ├── fusion.py                 # FusionEngine — fuse(mesh_vertices=?, photo_poses=?)
│   ├── export_formats.py         # ExportEngine.export() — 6 种格式
│   └── classification.py         # 模拟 NDVI 分类
└── cc_bridge/
    └── engine.py                 # EngineBridge — 静态方法调用 Python 3.6 worker

scripts/
├── cc_worker.py                  # ★ CC SDK 工人 (Python 3.6), 8 个命令
│   ├── create_project            # 创建工程 + 导入照片
│   ├── run_at                    # 空三 (提交 + 等待完成)
│   ├── run_reconstruct           # 创建重建对象 + 写文件
│   ├── run_production            # 导出 OBJ (提交 + 等待完成)
│   ├── get_photo_poses           # 提取所有照片位姿 (x,y,z)
│   └── get_tie_points            # 提取连接点 (x,y,z,r,g,b)
├── launch_oymm_db.bat            # ★ 启动脚本 (双击)
└── check_env.py / check_cc_license.py
```

## CC Worker 命令参考

所有命令通过 `_call_worker("command", {args}, timeout=N)` 调用，返回 `{"ok": True/False, ...}`。

- `create_project`: `{photos_dir, project_dir, name}` → `{ok, project_path, photos_added, ready_for_at}`
- `run_at`: `{project_path, keypoints_density}` → `{ok, status}`
- `run_reconstruct`: `{project_path}` → `{ok, tiles}`
- `run_production`: `{project_path, format, texture, texture_quality}` → `{ok, output_dir}`
- `get_photo_poses`: `{project_path}` → `{ok, count, poses: [{path, x, y, z}]}`
- `get_tie_points`: `{project_path}` → `{ok, count, points: [{x, y, z, r, g, b}]}`

## 数据集

| 名称 | 照片数 | 路径 | 规模 |
|------|--------|------|------|
| Aukerman ★ | 77 | `data/photos/aukerman/images/` | 默认，已通过 CC 管线验证 |
| Seneca | 167 | `data/photos/seneca/images/` | 中等 |
| Quarry | 347 | `data/photos/quarry/images/` | 大型（>1h） |
| test_scene | 60 | `data/photos/test_scene/` | 合成，无 EXIF（仅演示） |

切换数据集：修改 `module_reconstruction.py` → `_start_pipeline()` → `photos_dir` + `project_dir`。

## 已知问题

- 没有真实 LiDAR 数据（UseGeo 服务器国内无法连接）
- 模块 7/8 仍用模拟数据（无可用的多光谱/LiDAR 输入）
- OC 重建超时后 OBJ 不完整 → 需重新运行
- Windows 文件锁可能导致 rmtree 失败 → 手动删除项目目录

## 启动与调试

```bash
# 主启动
E:\oymm\scripts\launch_oymm_db.bat

# 日志位置
E:\oymm\scripts\app_stdout.log
E:\oymm\scripts\app_stderr.log

# 检查环境
E:\Program\anaconda3\envs\oymm\python.exe E:\oymm\scripts\check_env.py

# 检查 CC 许可证
E:\Program\anaconda3\envs\oymm-cc\python.exe E:\oymm\scripts\check_cc_license.py
```

## 代码规范

- Python 文件用 4 空格缩进
- 注释仅用于解释 WHY，不解释 WHAT
- PyQt 信号链: Worker(QThread) → Page → MainWindow._on_*_done()
- 路径用 `/`，绝对路径，盘符 `E:/`
- 所有 `oymm` 显示文字已改为 `Geosight`，文件系统路径不变
