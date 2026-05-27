"""模块1: 数据导入 - RGB + LiDAR + 多光谱."""
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from PIL import Image


class DataType(Enum):
    RGB = "rgb"
    LIDAR = "lidar"
    MULTISPECTRAL = "multispectral"
    UNKNOWN = "unknown"


@dataclass
class PhotoInfo:
    path: Path
    width: int = 0
    height: int = 0
    size_mb: float = 0.0


@dataclass
class LidarInfo:
    path: Path
    point_count: int = 0
    size_mb: float = 0.0


@dataclass
class MultispecInfo:
    path: Path
    bands: int = 0
    width: int = 0
    height: int = 0


@dataclass
class ImportResult:
    rgb: list[PhotoInfo] = field(default_factory=list)
    lidar: list[LidarInfo] = field(default_factory=list)
    multispectral: list[MultispecInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.rgb) + len(self.lidar) + len(self.multispectral)

    @property
    def summary(self) -> str:
        parts = []
        if self.rgb:
            parts.append(f"RGB影像: {len(self.rgb)} 张")
        if self.lidar:
            pts = sum(l.point_count for l in self.lidar)
            parts.append(f"LiDAR: {len(self.lidar)} 个文件 ({pts:,} 点)")
        if self.multispectral:
            parts.append(f"多光谱: {len(self.multispectral)} 个文件")
        return " | ".join(parts) if parts else "无数据"


RGB_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
LIDAR_EXTENSIONS = {".las", ".laz"}
MULTISPEC_EXTENSIONS = {".tif", ".tiff"}


class DataImporter:
    """Handles discovery and loading of photogrammetry data."""

    @staticmethod
    def scan_directory(directory: str | Path) -> ImportResult:
        """Scan a directory tree for supported data files."""
        result = ImportResult()
        root = Path(directory)

        if not root.exists():
            result.errors.append(f"目录不存在: {directory}")
            return result

        files = list(root.rglob("*"))
        rgb_files = []
        lidar_files = []
        ms_files = []

        for f in files:
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext in RGB_EXTENSIONS:
                if ext in MULTISPEC_EXTENSIONS:
                    ms_files.append(f)
                else:
                    rgb_files.append(f)
            elif ext in LIDAR_EXTENSIONS:
                lidar_files.append(f)

        # Resolve multi-spectral vs RGB for TIFF files
        for f in ms_files:
            info = DataImporter._read_tiff_info(f)
            if info and info.bands > 3:
                result.multispectral.append(info)
            else:
                rgb_files.append(f)

        # Process RGB files
        for f in rgb_files:
            info = DataImporter._read_photo_info(f)
            if info:
                result.rgb.append(info)

        # Sort by name
        result.rgb.sort(key=lambda p: p.path.name)
        result.lidar = sorted(lidar_files, key=lambda f: f.name)

        # Process LiDAR files
        for f in lidar_files:
            info = DataImporter._read_lidar_info(f)
            if info:
                result.lidar.append(info)

        return result

    @staticmethod
    def _read_photo_info(path: Path) -> PhotoInfo | None:
        try:
            img = Image.open(path)
            w, h = img.size
            size_mb = path.stat().st_size / (1024 * 1024)
            return PhotoInfo(path=path, width=w, height=h, size_mb=round(size_mb, 2))
        except Exception:
            return PhotoInfo(path=path, size_mb=round(path.stat().st_size / (1024 * 1024), 2))

    @staticmethod
    def _read_lidar_info(path: Path) -> LidarInfo | None:
        try:
            import laspy
            las = laspy.open(path)
            count = las.header.point_count
            size_mb = path.stat().st_size / (1024 * 1024)
            return LidarInfo(path=path, point_count=count, size_mb=round(size_mb, 2))
        except Exception:
            size_mb = path.stat().st_size / (1024 * 1024)
            return LidarInfo(path=path, size_mb=round(size_mb, 2))

    @staticmethod
    def _read_tiff_info(path: Path) -> MultispecInfo | None:
        try:
            img = Image.open(path)
            bands = len(img.getbands()) if hasattr(img, "getbands") else 1
            w, h = img.size
            return MultispecInfo(path=path, bands=bands, width=w, height=h)
        except Exception:
            return None

    @staticmethod
    def classify_file(path: str | Path) -> DataType:
        """Classify a single file by extension."""
        ext = Path(path).suffix.lower()
        if ext in RGB_EXTENSIONS:
            if ext in MULTISPEC_EXTENSIONS:
                return DataType.MULTISPECTRAL
            return DataType.RGB
        if ext in LIDAR_EXTENSIONS:
            return DataType.LIDAR
        return DataType.UNKNOWN
