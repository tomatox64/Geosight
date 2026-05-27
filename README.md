# Geosight — 三维重建展示系统

基于 ContextCapture + PyQt6 的倾斜摄影三维重建管线，集成 RGB / LiDAR / 多光谱数据。

![](https://img.shields.io/badge/Python-3.11-blue) ![](https://img.shields.io/badge/UI-PyQt6-green) ![](https://img.shields.io/badge/Engine-CC%2010.20-orange) ![](https://img.shields.io/badge/GPU-RTX%204060%20Laptop-76b900)

## 开发状态

> 处于早期开发阶段，UI 框架和 8 模块管线已搭建完成，当前使用合成数据验证流程。

| 模块 | 功能 | 状态 |
|------|------|------|
| 1. 数据导入 | RGB + LiDAR + 多光谱扫描导入 | 可用 |
| 2. 智能质控 | 模糊/曝光/重叠度分析 | 可用 |
| 3. 补采建议 | 空洞检测 + 航线建议生成 | 可用 |
| 4. 跨模态校准 | RGB-LiDAR ICP 配准 + 辐射归一化 | 可用 |
| 5. 多尺度融合 | LiDAR 骨架 + RGB 纹理融合 | 可用 |
| 6. 三维重建 | CC 密集匹配 + 纹理映射 | 需真实照片 |
| 7. 成果输出 | FBX / 3DTiles / LAS / DOM | 可用 |
| 8. 基础解译 | NDVI + 阈值分类 | 可用 |

### 已知问题
- 合成测试照片缺少 EXIF 元数据，CC 三维重建管线无法完成空三 → 当前使用程序生成的地形网格作为演示替代
- 需使用真实无人机航拍照片（含 GPS/EXIF）才能完成完整的三维重建

## 界面预览

编辑器风格布局：左侧图标栏（56px）→ 中央 3D 视口（pyvista）← 右侧属性面板（300px）

- 模块 1-5（数据处理）：视口隐藏，属性面板展开为全宽
- 模块 6-8（3D 相关）：视口 + 紧凑属性面板并排

## 技术栈

```
主应用 (Python 3.11, conda: oymm)
├── PyQt6          — UI 框架
├── pyvista        — 3D 视口渲染
├── Open3D         — 点云处理
├── OpenCV         — 影像处理
├── GDAL / PDAL    — 地理空间 / 点云 IO
├── scikit-learn   — ML 分类
└── matplotlib     — 图表

引擎桥接 (Python 3.6, conda: oymm-cc)
└── cc_worker.py   — subprocess 调用 ContextCapture SDK
```

## 项目结构

```
E:\oymm\
├── oymm_app/              # 主应用
│   ├── main.py            # 入口
│   ├── ui/                # 界面层（编辑器布局组件 + 8模块页面）
│   ├── modules/           # 功能模块（业务逻辑）
│   └── cc_bridge/         # CC 引擎桥接
├── scripts/               # 启动脚本 + 测试工具
├── tests/                 # 单元测试
├── data/                  # 样例数据（不入库）
├── projects/              # 工程文件（不入库）
└── output/                # 导出成果（不入库）
```

## 环境配置

```bash
# 创建主环境
conda create -n oymm python=3.11
conda activate oymm
pip install -r requirements.txt

# 创建 CC 桥接环境（需 Python 3.6）
conda create -n oymm-cc python=3.6
```

## 启动

```bash
conda activate oymm
cd E:\oymm
python -m oymm_app.main
```

或双击 `scripts/launch_oymm_db.bat`。

## 硬件要求

- GPU: NVIDIA RTX 4060 Laptop 8GB VRAM（当前开发环境）
- RAM: 24GB+
- 目标规模: 50-200 张倾斜摄影照片

## License

暂无，开发阶段。
