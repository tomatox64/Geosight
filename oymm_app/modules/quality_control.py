"""模块2: 智能质控 - 重叠度/利用率/缺失检测."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import cv2
from PIL import Image


@dataclass
class PhotoQuality:
    path: Path
    blur_score: float = 0.0       # Laplacian variance, higher = sharper
    exposure_mean: float = 0.0     # Mean pixel brightness (0-255)
    exposure_ok: bool = True
    blur_ok: bool = True
    resolution_ok: bool = True
    issues: list[str] = field(default_factory=list)


@dataclass
class QCOverlapInfo:
    estimated_overlap_pct: float = 0.0
    coverage_ok: bool = True
    gap_regions: list = field(default_factory=list)
    note: str = ""


@dataclass
class QualityReport:
    photos: list[PhotoQuality] = field(default_factory=list)
    total_count: int = 0
    blur_issues: int = 0
    exposure_issues: int = 0
    resolution_issues: int = 0
    overall_score: float = 0.0
    overlap: QCOverlapInfo = field(default_factory=QCOverlapInfo)
    density_data: Optional[np.ndarray] = None

    @property
    def pass_rate(self) -> float:
        if len(self.photos) == 0:
            return 0
        ok = sum(1 for p in self.photos
                 if p.blur_ok and p.exposure_ok and p.resolution_ok)
        return ok / len(self.photos) * 100

    @property
    def summary(self) -> str:
        sampled = len(self.photos)
        lines = [
            f"照片总数: {self.total_count} (分析 {sampled} 张采样)",
            f"采样通过率: {self.pass_rate:.1f}%",
            f"模糊问题: {self.blur_issues} 张",
            f"曝光问题: {self.exposure_issues} 张",
            f"分辨率不足: {self.resolution_issues} 张",
        ]
        if self.overlap.note:
            lines.append(f"重叠度: {self.overlap.note}")
        return "\n".join(lines)


class QualityController:
    """Analyzes photo quality and overlap."""

    BLUR_THRESHOLD = 100.0       # Laplacian var below this = blurry
    EXPOSURE_LOW = 30.0          # Too dark
    EXPOSURE_HIGH = 230.0        # Too bright
    MIN_RESOLUTION_MP = 2.0      # Minimum megapixels

    @classmethod
    def analyze_photos(cls, photo_paths: list[Path]) -> QualityReport:
        """Analyze a batch of photos for quality issues.

        Samples large datasets; small datasets (<100 photos) are fully analyzed.
        """
        report = QualityReport()
        report.total_count = len(photo_paths)

        if not photo_paths:
            return report

        # Full analysis for small datasets, 30% sample for large ones
        if len(photo_paths) <= 100:
            indices = range(len(photo_paths))
        else:
            n_sample = max(20, int(len(photo_paths) * 0.3))
            indices = np.linspace(0, len(photo_paths) - 1, n_sample, dtype=int)

        for i in indices:
            pq = cls._analyze_single(photo_paths[i])
            report.photos.append(pq)

            if not pq.blur_ok:
                report.blur_issues += 1
            if not pq.exposure_ok:
                report.exposure_issues += 1
            if not pq.resolution_ok:
                report.resolution_issues += 1

        # Overall score (weighted)
        if report.photos:
            scores = []
            for p in report.photos:
                s = 0.0
                s += 0.4 * min(p.blur_score / 500, 1.0)  # Blur weight
                s += 0.3 * (1.0 if p.exposure_ok else 0.5)  # Exposure weight
                s += 0.3 * (1.0 if p.resolution_ok else 0.5)  # Resolution weight
                scores.append(s)
            report.overall_score = np.mean(scores) * 100

        # Overlap estimation
        report.overlap = cls._estimate_overlap(photo_paths)

        return report

    @classmethod
    def _analyze_single(cls, path: Path) -> PhotoQuality:
        pq = PhotoQuality(path=path)

        try:
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                pq.issues.append("无法读取")
                return pq

            h, w = img.shape

            # Resolution check
            mp = (w * h) / 1_000_000
            if mp < cls.MIN_RESOLUTION_MP:
                pq.resolution_ok = False
                pq.issues.append(f"分辨率过低 ({mp:.1f}MP)")

            # Blur detection
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            pq.blur_score = laplacian.var()
            if pq.blur_score < cls.BLUR_THRESHOLD:
                pq.blur_ok = False
                pq.issues.append(f"图像模糊 ({pq.blur_score:.0f})")

            # Exposure check
            pq.exposure_mean = img.mean()
            if pq.exposure_mean < cls.EXPOSURE_LOW:
                pq.exposure_ok = False
                pq.issues.append(f"曝光不足 ({pq.exposure_mean:.0f})")
            elif pq.exposure_mean > cls.EXPOSURE_HIGH:
                pq.exposure_ok = False
                pq.issues.append(f"过曝 ({pq.exposure_mean:.0f})")

        except Exception as e:
            pq.issues.append(str(e))

        return pq

    @classmethod
    def _estimate_overlap(cls, photo_paths: list[Path]) -> QCOverlapInfo:
        """Estimate potential overlap from photo count and naming.

        Without actual AT results, this gives a rough estimate based on:
        - Number of photos vs typical coverage
        - Sequential naming suggesting systematic capture
        """
        info = QCOverlapInfo()
        n = len(photo_paths)

        if n < 3:
            info.coverage_ok = False
            info.note = "照片数量不足，无法估算重叠度"
            return info

        # Check for sequential naming pattern
        names = sorted([p.stem for p in photo_paths])
        sequential = 0
        for i in range(len(names) - 1):
            try:
                a = int(''.join(c for c in names[i] if c.isdigit()) or '0')
                b = int(''.join(c for c in names[i + 1] if c.isdigit()) or '0')
                if abs(b - a) <= 10:
                    sequential += 1
            except Exception:
                pass

        seq_ratio = sequential / max(n - 1, 1)

        # Rough overlap estimate
        if seq_ratio > 0.7:
            info.estimated_overlap_pct = 65.0 + (n - 10) * 0.5
            info.note = f"序列化采集，估计重叠度 {info.estimated_overlap_pct:.0f}%"
        elif seq_ratio > 0.3:
            info.estimated_overlap_pct = 40.0
            info.note = f"部分序列化，估计重叠度 ~{info.estimated_overlap_pct:.0f}%"
        else:
            info.estimated_overlap_pct = 30.0
            info.note = "随机命名，建议检查重叠度"

        info.estimated_overlap_pct = min(info.estimated_overlap_pct, 90.0)
        info.coverage_ok = info.estimated_overlap_pct >= 30.0

        return info

    @classmethod
    def compute_density_heatmap(cls, points: np.ndarray,
                                 grid_size: int = 64) -> np.ndarray:
        """Compute 2D density heatmap from point cloud (XY only).

        Args:
            points: Nx3 or Nx2 array of point coordinates
            grid_size: output heatmap resolution
        Returns:
            2D numpy array of density values
        """
        if len(points) == 0:
            return np.zeros((grid_size, grid_size))

        xy = points[:, :2]
        x_min, y_min = xy.min(axis=0)
        x_max, y_max = xy.max(axis=0)

        x_range = x_max - x_min or 1
        y_range = y_max - y_min or 1

        heatmap = np.zeros((grid_size, grid_size))
        for i in range(len(xy)):
            gx = int((xy[i, 0] - x_min) / x_range * (grid_size - 1))
            gy = int((xy[i, 1] - y_min) / y_range * (grid_size - 1))
            gx = max(0, min(grid_size - 1, gx))
            gy = max(0, min(grid_size - 1, gy))
            heatmap[gy, gx] += 1

        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        return heatmap
