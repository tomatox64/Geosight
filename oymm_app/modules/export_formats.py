"""模块7: 成果输出 - 多格式导出."""
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

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
               output_dir: str = "E:/oymm/output") -> ExportReport:
        selected = [f for f in FORMATS if f.name in selected_names]
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_bytes = 0

        for fmt in selected:
            out_path = Path(output_dir) / f"geosight_{timestamp}{fmt.ext}"
            data = cls._generate_demo(fmt)
            total_bytes += len(data)
            with open(out_path, "wb") as fh:
                fh.write(data)

        total_mb = total_bytes / (1024 * 1024)
        return ExportReport(
            selected=selected,
            output_dir=output_dir,
            total_size=f"~{total_mb:.1f} MB",
            summary=f"已导出 {len(selected)} 种格式至 {output_dir}，总计 {total_mb:.1f} MB"
        )

    @classmethod
    def _generate_demo(cls, fmt: ExportFormat) -> bytes:
        header = f"# Geosight Demo Export — {fmt.name}\n".encode()
        rng = np.random.RandomState(42)

        if fmt.name == "OBJ":
            verts = 1000
            v_data = rng.uniform(-10, 10, (verts, 3)).astype(np.float32)
            f_data = rng.randint(1, verts, (verts // 3 * 3, 3))
            lines = [header]
            for v in v_data:
                lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}".encode())
            for f in f_data:
                lines.append(f"f {f[0]} {f[1]} {f[2]}".encode())
            return b"\n".join(lines)

        if fmt.name == "FBX":
            return header + b"FBX binary placeholder (demo mesh)\n" + rng.bytes(4096)

        if fmt.name == "3D Tiles":
            tile = b'{"asset":{"version":"1.0"},"geometricError":50.0,"root":{"boundingVolume":{"box":[0,0,0,10,0,0,0,10,0,0,0,5]}}}'
            return header + tile + b"\n" + rng.bytes(2048)

        if fmt.name == "LAS":
            from struct import pack
            buf = bytearray()
            buf.extend(header)
            buf.extend(b"LASF" + b"\x00" * 4)
            buf.extend(pack("<HH", 1, 2))
            buf.extend(b"\x00" * 8)
            buf.extend(pack("<I", 500))
            buf.extend(b"\x00" * (227 - len(buf)))
            for _ in range(500):
                x, y, z = rng.uniform(-10, 10, 3).astype(np.float64)
                buf.extend(pack("<ddd", x, y, z))
                buf.extend(pack("<H", rng.randint(0, 255)))
                buf.extend(b"\x00" * 14)
            return bytes(buf)

        if fmt.name in ("DOM", "DSM"):
            return header + rng.bytes(512 * 512 * 1)

        return header + rng.bytes(1024)
