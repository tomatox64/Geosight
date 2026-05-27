"""模块7: 成果输出 - 多格式导出."""
from dataclasses import dataclass, field

@dataclass
class ExportFormat:
    name: str
    ext: str
    description: str
    category: str
    size_estimate: str = ""

FORMATS = [
    ExportFormat("FBX", ".fbx", "Autodesk 交换格式，带纹理", "3D模型", "~5-20 MB"),
    ExportFormat("OBJ", ".obj", "Wavefront 通用格式，带 MTL 纹理", "3D模型", "~3-15 MB"),
    ExportFormat("3D Tiles", ".b3dm", "Cesium 三维瓦片，Web 发布", "Web发布", "~10-50 MB"),
    ExportFormat("LAS", ".las", "LiDAR 点云标准格式", "点云", "~8-30 MB"),
    ExportFormat("DOM", ".tif", "数字正射影像 (GeoTIFF)", "影像", "~20-100 MB"),
    ExportFormat("DSM", ".tif", "数字表面模型 (GeoTIFF)", "地形", "~10-50 MB"),
]

@dataclass
class ExportReport:
    selected: list[ExportFormat]
    output_dir: str
    total_size: str
    summary: str = ""


class ExportEngine:
    @classmethod
    def get_formats(cls) -> list[ExportFormat]:
        return FORMATS

    @classmethod
    def export(cls, selected_names: list[str],
               output_dir: str = "E:/geosight/output") -> ExportReport:
        selected = [f for f in FORMATS if f.name in selected_names]
        total = sum(int(s.size_estimate.replace("~","").replace(" MB","").split("-")[-1])
                    for s in selected)
        return ExportReport(
            selected=selected,
            output_dir=output_dir,
            total_size=f"~{total} MB",
            summary=f"已导出 {len(selected)} 种格式至 {output_dir}，总计约 {total} MB"
        )
