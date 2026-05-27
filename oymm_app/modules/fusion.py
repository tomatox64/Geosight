"""模块5: 多尺度融合 - LiDAR骨架 + RGB纹理."""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class FusionResult:
    """Result of LiDAR + RGB fusion."""
    points: np.ndarray          # Nx3 geometry
    colors: np.ndarray          # Nx3 RGB colors (0-255)
    point_count: int
    lidar_density: float        # points/m2
    texture_coverage: float     # 0-1, fraction of points with valid color
    color_consistency: float    # 0-1, std dev of colors (lower = more consistent)
    score: float                # 0-100
    summary: str = ""


class FusionEngine:
    """Fuses LiDAR geometry with RGB texture colors."""

    @classmethod
    def fuse(cls, photo_count: int = 60,
             calibration_score: float = 100) -> FusionResult:
        """Generate a fused point cloud with RGB colors projected from imagery.

        Simulates LiDAR geometry colored by aerial imagery, demonstrating
        the multi-scale fusion concept of the system.
        """
        rng = np.random.RandomState(99)
        n_points = 15000

        # Ground plane with slight undulation
        ground_n = int(n_points * 0.65)
        x_g = rng.uniform(-15, 15, ground_n)
        y_g = rng.uniform(-15, 15, ground_n)
        z_g = (0.03 * np.sin(x_g * 0.5) * np.cos(y_g * 0.5)
               + rng.normal(0, 0.08, ground_n))
        geom = np.column_stack([x_g, y_g, z_g])

        # Building-like structures (LiDAR skeleton)
        struct_defs = [
            (-8, -5, 4, 3, 6), (3, -7, 3, 2, 8),
            (-2, 2, 5, 3, 5), (7, 4, 2, 2, 7),
            (-6, 8, 3, 3, 4), (0, -3, 4, 4, 9),
        ]
        for bx, by, bw, bd, bh in struct_defs:
            n_s = int(n_points * 0.06)
            sx = bx + rng.uniform(-bw / 2, bw / 2, n_s)
            sy = by + rng.uniform(-bd / 2, bd / 2, n_s)
            sz = rng.uniform(0, bh, n_s)
            geom = np.vstack([geom, np.column_stack([sx, sy, sz])])

        # Trim to exact count
        geom = geom[:n_points]
        n_points = len(geom)

        # Generate RGB colors based on height + position
        colors = np.zeros((n_points, 3), dtype=np.uint8)
        z_min, z_max = geom[:, 2].min(), geom[:, 2].max()
        z_norm = (geom[:, 2] - z_min) / max(z_max - z_min, 0.01)

        # Ground: greens/browns
        ground_mask = z_norm < 0.15
        colors[ground_mask, 0] = rng.randint(60, 120, ground_mask.sum())
        colors[ground_mask, 1] = rng.randint(100, 180, ground_mask.sum())
        colors[ground_mask, 2] = rng.randint(30, 80, ground_mask.sum())

        # Low vegetation
        veg_mask = (z_norm >= 0.15) & (z_norm < 0.3)
        colors[veg_mask, 0] = rng.randint(40, 100, veg_mask.sum())
        colors[veg_mask, 1] = rng.randint(120, 200, veg_mask.sum())
        colors[veg_mask, 2] = rng.randint(20, 60, veg_mask.sum())

        # Buildings: grays + warm tones
        bld_mask = z_norm >= 0.3
        base = rng.randint(150, 220, bld_mask.sum())
        colors[bld_mask, 0] = np.clip(base + rng.randint(-20, 20, bld_mask.sum()), 0, 255)
        colors[bld_mask, 1] = np.clip(base + rng.randint(-20, 20, bld_mask.sum()), 0, 255)
        colors[bld_mask, 2] = np.clip(base + rng.randint(-30, 10, bld_mask.sum()), 0, 255)

        # Texture coverage: most points have valid color
        texture_coverage = 0.92 + (calibration_score / 100) * 0.08

        # Color consistency
        color_consistency = 0.85 + (calibration_score / 100) * 0.10

        # Density (points per m2 of XY area)
        xy_area = (geom[:, 0].max() - geom[:, 0].min()) * (geom[:, 1].max() - geom[:, 1].min())
        density = n_points / max(xy_area, 1)

        # Score
        score = (texture_coverage * 40 + color_consistency * 30
                 + min(density / 20, 1) * 30)
        score = min(100, round(score, 1))

        summary = (f"融合完成：{n_points} 点，纹理覆盖率 {texture_coverage:.0%}，"
                   f"密度 {density:.0f} pts/m²")

        return FusionResult(
            points=geom,
            colors=colors,
            point_count=n_points,
            lidar_density=round(density, 1),
            texture_coverage=round(texture_coverage, 4),
            color_consistency=round(color_consistency, 4),
            score=score,
            summary=summary,
        )
