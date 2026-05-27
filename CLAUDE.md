# OYMM - 三维重建展示系统

## 项目概述
倾斜摄影三维重建展示系统，集成 RGB + LiDAR + 多光谱数据，包含 8 个功能模块。

## 技术栈
- **前端**: PyQt6 (Python 3.11 @ conda env `oymm`)
- **引擎**: v10.20.0.4117 @ E:\Program\Bentley\ContextCapture
- **引擎 SDK**: Python 3.6 @ conda env `oymm-cc`, 通过 subprocess 桥接
- **增强模块**: Open3D 0.19, OpenCV 4.13, GDAL 3.12, PDAL 3.5, NumPy

## Conda 环境
- `oymm` (Python 3.11): 主应用 + 所有增强模块
- `oymm-cc` (Python 3.6): 引擎 SDK，仅用于 cc_worker.py

## 项目结构
```
E:\oymm\
├── oymm_app/              # 主应用
│   ├── main.py            # PyQt 入口
│   ├── ui/                # 界面模块
│   ├── modules/           # 8 个功能模块
│   └── cc_bridge/         # 引擎桥接层
├── data/                  # 样例数据
├── projects/              # 工程文件
├── output/                # 输出成果
├── tests/                 # 测试
└── scripts/               # 工具脚本
```

## 8 个模块
1. 数据导入 - RGB+LiDAR+多光谱
2. 智能质控 - 重叠度/利用率/缺失区域检测
3. 动态补采建议 - 空洞标记+航线建议
4. 跨模态校准 - RGB-LiDAR 配准+辐射归一化
5. 多尺度融合 - LiDAR骨架+RGB纹理
6. 三维重建 - 影像密集匹配+纹理映射
7. 成果输出 - FBX/3DTiles/LAS/DOM/DSM
8. 基础解译 - NDVI+阈值分类

## 已知约束
- GPU: RTX 4060 Laptop 8GB VRAM
- RAM: 23.8GB
- 引擎 SDK 仅 Python 3.6，主应用 Python 3.11，通过 cc_worker.py subprocess 桥接
- 目标: 展示用途，小规模数据 (50-200 张照片)

## 桥接层
- `scripts/cc_worker.py` - Python 3.6 工人脚本，封装完整管线
- `oymm_app/cc_bridge/engine.py` - Python 3.11 桥接层，subprocess 调用 worker
- 已验证管线: 创建工程 → 空三 → 重建 → 导出 OBJ（60张合成照片）

## 启动方式
```bash
# 激活主环境
conda activate oymm
cd E:\oymm
python -m oymm_app.main
```
