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
             calibration_score: float = 100,
             mesh_vertices: np.ndarray | None = None,
             photo_poses: list[dict] | None = None,
             photo_paths: list[str] | None = None) -> FusionResult:
        """Fuse LiDAR geometry with RGB texture colors.

        If mesh_vertices + photo_poses + photo_paths are provided, uses real
        geometry from CC reconstruction and projects photo colors onto it.
        Otherwise falls back to fully synthetic data.
        """
        if (mesh_vertices is not None and len(mesh_vertices) > 0
                and photo_poses and photo_paths):
            return cls._fuse_from_real(mesh_vertices, photo_poses,
                                       photo_paths, calibration_score)
        return cls._fuse_synthetic(calibration_score)

    @classmethod
    def _fuse_from_real(cls, vertices: np.ndarray, poses: list[dict],
                         paths: list[str], calib_score: float) -> FusionResult:
        """Real fusion: mesh vertices as geometry, photo projection for colors."""
        import cv2
        from pathlib import Path

        # Subsample vertices for manageable point cloud size
        n_max = 20000
        indices = np.arange(len(vertices))
        if len(vertices) > n_max:
            indices = np.random.RandomState(42).choice(len(vertices), n_max, replace=False)
        geom = vertices[indices].astype(np.float64)
        n_points = len(geom)

        # Build photo position array
        pose_arr = np.array([[p["x"], p["y"], p["z"]] for p in poses])
        colors = np.zeros((n_points, 3), dtype=np.uint8)

        # For each vertex, find nearest photo and sample color
        # Simplified: use XY distance only (aerial nadir assumption)
        for i, pt in enumerate(geom):
            dists = np.sqrt((pose_arr[:, 0] - pt[0]) ** 2 + (pose_arr[:, 1] - pt[1]) ** 2)
            nearest = int(np.argmin(dists))

            # Load photo lazily (cache in dict)
            if not hasattr(cls, '_photo_cache'):
                cls._photo_cache = {}
            if nearest not in cls._photo_cache:
                img_path = paths[nearest] if nearest < len(paths) else paths[0]
                img = cv2.imread(img_path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                cls._photo_cache[nearest] = img
            img = cls._photo_cache[nearest]

            if img is not None:
                # Approximate projection: use XY offset from photo center
                dx = pt[0] - pose_arr[nearest, 0]
                dy = pt[1] - pose_arr[nearest, 1]
                # Simple perspective: ~2cm GSD at 80m altitude, scale to pixels
                alt = max(pose_arr[nearest, 2], 1.0)
                gsd = alt * 0.0003  # rough GSD m/pixel
                h, w = img.shape[:2]
                px = int(w / 2 + dx / gsd)
                py = int(h / 2 - dy / gsd)
                if 0 <= px < w and 0 <= py < h:
                    colors[i] = img[py, px]
                else:
                    colors[i] = [128, 128, 128]
            else:
                colors[i] = [128, 128, 128]

        cls._photo_cache = {}

        xy_area = (geom[:, 0].max() - geom[:, 0].min()) * (geom[:, 1].max() - geom[:, 1].min())
        density = n_points / max(xy_area, 1)
        texture_coverage = float(np.sum(colors.sum(axis=1) > 10) / n_points)
        color_consistency = float(1.0 - np.std(colors.astype(np.float32)) / 128)
        score = min(100, round(texture_coverage * 40 + color_consistency * 30 + min(density / 20, 1) * 30, 1))

        summary = (f"[真实数据] 融合完成：{n_points:,} 点，纹理覆盖率 {texture_coverage:.0%}，"
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

    @classmethod
    def _fuse_synthetic(cls, calibration_score: float) -> FusionResult:
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
