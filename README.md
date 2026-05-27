# Geosight — 三维重建展示系统

基于 Bentley ContextCapture + PyQt6 的倾斜摄影三维重建管线，集成 RGB / LiDAR / 多光谱数据处理。

![](https://img.shields.io/badge/Python-3.11-blue) ![](https://img.shields.io/badge/UI-PyQt6-green) ![](https://img.shields.io/badge/Engine-CC%2010.20-orange) ![](https://img.shields.io/badge/GPU-RTX%204060%208GB-76b900)

## 快速开始

```bash
# 1. 激活环境
conda activate oymm

# 2. 进入项目
cd E:\oymm

# 3. 启动（二选一）
python -m oymm_app.main          # 命令行启动
scripts\launch_oymm_db.bat       # 双击启动（日志写入 scripts/app_*.log）
```

首次运行：模块 6 点击「开始重建」→ 自动跑 CC 管线（30-75 分钟）→ 视口显示带纹理的 3D 模型。

如果之前已重建过，弹窗选择「是」直接加载已有模型。

## 架构

```
┌──────────────────────────────────────────────────────────┐
│  PyQt6 主应用 (Python 3.11, conda env: oymm)             │
│                                                          │
│  main_window.py  ←── 编辑器布局（图标栏 + 3D视口 + 面板）│
│       │                                                  │
│       ├─ ui/  8 个模块页面 (module_*.py)                  │
│       ├─ modules/  8 个业务逻辑模块                       │
│       └─ cc_bridge/engine.py  ←── subprocess ──────────┐ │
│                                                         │ │
└─────────────────────────────────────────────────────────┘ │
                                                            │
┌────────────────────────────────────────────────────────── │
│  CC Worker (Python 3.6, conda env: oymm-cc)             │ │
│  scripts/cc_worker.py                                   │ │
│       │                                                  │ │
│       └─ ccmasterkernel  ←── CC SDK (C++)         ◄─────┘ │
│                                                          │
│  Bentley ContextCapture 10.20                             │
│  E:\Program\Bentley\ContextCapture\bin\CCEngine.exe       │
└──────────────────────────────────────────────────────────┘
```

**关键约束**：CC SDK (ccmasterkernel) 仅支持 Python 3.6，主应用 Python 3.11。两者通过 `subprocess.run()` + JSON stdin/stdout 通信。

## 管线流程

```
模块1(导入) → 模块2(质控) → 模块3(补采) → 模块4(校准) → 模块5(融合)
                                                              ↓
模块8(解译) ← 模块7(导出) ← 模块6(重建) ←─────────────────────┘
                              ↑ CC 管线
                              ① 创建工程 → ② 空三(AT) → ③ 重建(MVS) → ④ 导出OBJ
```

**数据依赖链**：
- 模块 2 → 3：照片数量 + 重叠度估算
- 模块 6 → 3：CC 空三位姿 → 真实覆盖度分析
- 模块 6 → 4：CC 连接点(TiePoints) → 真实 ICP 配准
- 模块 6 → 5：CC 网格顶点 + 照片位姿 → 真实融合着色

每个模块处理完成后自动推进到下一步，也可通过左侧图标栏自由跳转。

## 项目文件清单

```
E:\oymm\
├── oymm_app/
│   ├── main.py                       # 应用入口
│   ├── ui/
│   │   ├── main_window.py            # 主窗口：布局、信号链、模块调度
│   │   ├── icon_tab_bar.py           # 左侧 56px 图标导航栏
│   │   ├── viewport_manager.py       # 中央 3D 视口 (pyvista QtInteractor 单例)
│   │   ├── property_panel.py         # 右侧属性面板容器（统一工具栏）
│   │   ├── module_adapter.py         # 模块基类（未强制使用）
│   │   ├── module_import.py          # 模块1: 数据导入页面
│   │   ├── module_quality.py         # 模块2: 智能质控页面
│   │   ├── module_resampling.py      # 模块3: 补采建议页面
│   │   ├── module_calibration.py     # 模块4: 跨模态校准页面
│   │   ├── module_fusion.py          # 模块5: 多尺度融合页面
│   │   ├── module_reconstruction.py  # 模块6: 三维重建页面 (核心)
│   │   ├── module_export.py          # 模块7: 成果输出页面
│   │   ├── module_classify.py        # 模块8: 基础解译页面
│   │   └── theme.qss                 # 全局样式表
│   ├── modules/
│   │   ├── data_import.py            # 模块1: 文件扫描 + 分类
│   │   ├── quality_control.py        # 模块2: 模糊/曝光/重叠度分析
│   │   ├── resampling.py             # 模块3: 覆盖度分析 + 航线建议
│   │   ├── calibration.py            # 模块4: ICP 配准 + 直方图匹配
│   │   ├── fusion.py                 # 模块5: 点云融合 + 纹理投影
│   │   ├── export_formats.py         # 模块7: 多格式导出引擎
│   │   └── classification.py         # 模块8: NDVI + 阈值分类
│   └── cc_bridge/
│       └── engine.py                 # CC 桥接层 (subprocess → cc_worker.py)
├── scripts/
│   ├── cc_worker.py                  # ★ Python 3.6 工人脚本，封装 CC SDK 调用
│   ├── launch_oymm_db.bat            # 主启动脚本（双击）
│   ├── launch_oymm_debug.bat         # 调试模式启动
│   ├── launch_oymm_full.bat          # 全功能启动（含 CC 引擎）
│   ├── check_env.py                  # 环境检查
│   ├── check_cc_license.py           # CC 许可证检查
│   ├── generate_test_photos.py       # 合成测试照片生成
│   └── _test_*.py                    # 各模块测试脚本
├── data/photos/
│   ├── aukerman/images/  77张 20MP   # ★ 当前默认数据集 (EXIF+GPS)
│   ├── seneca/images/    167张 8MP   # 中等规模
│   ├── quarry/images/    347张 20MP  # 大规模（CC 处理可能超 1 小时）
│   └── test_scene/       60张 合成   # 无 EXIF，仅演示模式使用
├── projects/                         # CC 工程文件 (gitignore)
│   └── aukerman_demo/                # 当前默认工程
├── output/                           # 导出成果 (gitignore)
├── requirements.txt
├── CLAUDE.md                         # AI Agent 上下文文件
└── .gitignore
```

### 每个文件做什么（Agent 速查）

| 你要做的事 | 找哪个文件 |
|-----------|-----------|
| 修改界面布局 | `ui/main_window.py` + `ui/property_panel.py` |
| 修改左侧图标 | `ui/icon_tab_bar.py` |
| 修改 3D 视口 | `ui/viewport_manager.py` |
| 修改某个模块的 UI | `ui/module_<name>.py` |
| 修改某个模块的计算逻辑 | `modules/<name>.py` |
| 修改 CC 管线调用 | `cc_bridge/engine.py` (3.11 端) + `scripts/cc_worker.py` (3.6 端) |
| 修改样式 | `ui/theme.qss` |
| 修改启动方式 | `scripts/launch_oymm_db.bat` |
| 切换数据集 | `ui/module_reconstruction.py` → `_start_pipeline()` 中的 `photos_dir` |

## 当前状态

| 模块 | 数据来源 | 备注 |
|------|---------|------|
| 1. 数据导入 | 扫描目录（模拟） | 路径可配 |
| 2. 智能质控 | 真实照片分析 | OpenCV 拉普拉斯 + 曝光直方图 |
| 3. 补采建议 | **先模拟后真实** | CC 空三完成后用真实位姿重新计算覆盖度 |
| 4. 跨模态校准 | **真实 CC 连接点** | 有 LiDAR 数据时可直接替换 |
| 5. 多尺度融合 | **真实 CC 网格 + 照片投影** | 无 LiDAR 时用 OBJ 顶点作为几何 |
| 6. 三维重建 | **真实 CC 管线** | Aukerman 77 张已跑通 |
| 7. 成果输出 | 演示文件生成 | OBJ/FBX/LAS 等格式 demo 文件 |
| 8. 基础解译 | 模拟 NDVI | 无真实多光谱数据 |

### 已知限制

- **没有真实 LiDAR 数据**：模块 4/5 用 CC 输出近似替代，效果可达演示级别
- **CC SDK 仅 Python 3.6**：跨版本通信通过 subprocess + JSON
- **OBJ 纹理**：pyvista 对有 MaterialNames 的网格自动使用 MTL 纹理
- **重建超时**：AT 上限 30 分钟，导出上限 60 分钟（`cc_bridge/engine.py` 中配置）
- **项目清理**：Windows 上 CC 可能锁文件，`_rmtree_force()` 做了 chmod+重试+改名三层兜底

## 切换数据集

编辑 `oymm_app/ui/module_reconstruction.py` 的 `_start_pipeline()` 方法：

```python
# 当前使用 Aukerman（77 张，最快）
photos_dir = "E:/oymm/data/photos/aukerman/images"
project_dir = "E:/oymm/projects/aukerman_demo"

# 换成 Seneca（167 张，中等）
photos_dir = "E:/oymm/data/photos/seneca/images"
project_dir = "E:/oymm/projects/seneca_demo"

# 换成 Quarry（347 张，最慢但最精细）
photos_dir = "E:/oymm/data/photos/quarry/images"
project_dir = "E:/oymm/projects/quarry_demo"
```

切换后首次运行会跑完整 CC 管线，之后自动检测已有 OBJ 直接加载。

## 导入已有模型

模块 6 提供三个入口：
1. **自动检测**：点击「开始重建」→ 弹窗 → 选「是」直接加载
2. **手动导入**：点击「导入模型」→ 选择 OBJ/FBX/PLY/STL/GLB 文件
3. **重建失败**：自动回退加载已有 OBJ（如有）

## 常见问题

| 问题 | 解决 |
|------|------|
| 启动报 DLL 错误 | 确保 conda 环境已激活（`conda activate oymm`） |
| CC 报 License 错误 | 运行 `python scripts/check_cc_license.py` 检查 |
| CC 创建工程失败（目录已存在） | 手动删除 `E:\oymm\projects\<name>\` 后重试 |
| 重建完成后模型纯色无纹理 | 确认 OBJ 同目录下有 MTL + JPG 文件 |
| 风扇响很久后没动静 | 可能超时，查看日志中是否有 "timed out"，联系开发者调整 |
| 想添加新模块 | 参考 `module_adapter.py` 基类，在 `main_window.py` 的 `MODULES` 列表中添加 |

## 硬件要求

- GPU: NVIDIA 显卡 8GB+ VRAM（CC 引擎必需）
- RAM: 24GB+
- 磁盘: 10GB+ 空闲（数据集 + CC 工程文件）
- OS: Windows 10/11（CC SDK 仅 Windows）
- 软件: Anaconda/Miniconda, Bentley ContextCapture 10.20

## Agent 使用指南

本项目已配置 `CLAUDE.md`（AI Agent 上下文文件）。用 Claude Code 等 AI 工具打开此项目时，Agent 会自动读取项目结构、环境配置和关键约束。

**推荐的 Agent 任务描述示例**：
- "在模块 X 的 UI 页面上添加一个 Y 按钮"
- "修改 cc_worker.py 中的空三参数"
- "帮我把数据集从 Aukerman 切换到 Seneca"
- "检查为什么重建完成后视口是空的"

## License

开发阶段，暂未设定。
