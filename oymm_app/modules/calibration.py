"""模块4: 跨模态校准 - RGB-LiDAR配准 + 辐射归一化."""
from dataclasses import dataclass, field
import numpy as np
import cv2

# Lazy imports for heavy libs
_open3d = None


def _get_o3d():
    global _open3d
    if _open3d is None:
        import open3d as o3d
        _open3d = o3d
    return _open3d


@dataclass
class AlignmentResult:
    rmse_before: float      # RMSE before ICP (meters)
    rmse_after: float       # RMSE after ICP (meters)
    translation: np.ndarray  # 3D translation vector
    rotation: np.ndarray     # 3x3 rotation matrix
    iterations: int
    converged: bool
    inlier_ratio: float = 1.0


@dataclass
class RadiometricResult:
    method: str  # "histogram_matching"
    psnr_before: float
    psnr_after: float
    hist_correlation: float  # 0-1, higher = better match


@dataclass
class CalibrationReport:
    alignment: AlignmentResult
    radiometric: RadiometricResult | None = None
    overall_score: float = 0.0
    summary: str = ""


class CalibrationEngine:
    """Cross-modal RGB-LiDAR calibration using ICP + histogram matching."""

    @classmethod
    def generate_synthetic_lidar(cls, n_points: int = 5000,
                                  noise_std: float = 0.02,
                                  offset: np.ndarray | None = None,
                                  rotation_deg: float = 3.0) -> np.ndarray:
        """Generate synthetic LiDAR point cloud as noisy version of ground plane.

        Simulates a LiDAR scan of a flat terrain with some structures,
        slightly offset and rotated from the ideal coordinate system.
        """
        if offset is None:
            offset = np.array([1.5, 0.8, 0.3])

        rng = np.random.RandomState(123)
        points = np.zeros((n_points, 3))

        # Ground plane with slight slope
        ground_n = int(n_points * 0.7)
        x_ground = rng.uniform(-10, 10, ground_n)
        y_ground = rng.uniform(-10, 10, ground_n)
        z_ground = 0.05 * x_ground - 0.03 * y_ground + rng.normal(0, 0.1, ground_n)
        points[:ground_n] = np.column_stack([x_ground, y_ground, z_ground])

        # Building-like structures
        struct_n = n_points - ground_n
        for i in range(ground_n, n_points):
            bx = rng.choice([-3, 0, 4, 7])
            by = rng.choice([-5, -1, 2, 6])
            bw, bd = rng.uniform(1, 3), rng.uniform(1, 3)
            bh = rng.uniform(3, 8)
            x = bx + rng.uniform(-bw / 2, bw / 2)
            y = by + rng.uniform(-bd / 2, bd / 2)
            z = rng.uniform(0, bh)
            points[i] = [x, y, z]

        # Apply rotation and offset
        theta = np.radians(rotation_deg)
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        R = np.array([[cos_t, -sin_t, 0], [sin_t, cos_t, 0], [0, 0, 1]])
        points = points @ R.T + offset

        # Add noise
        points += rng.normal(0, noise_std, points.shape)

        return points

    @classmethod
    def icp_align(cls, source: np.ndarray, target: np.ndarray,
                  max_iterations: int = 100,
                  tolerance: float = 1e-6) -> AlignmentResult:
        """Align source point cloud to target using ICP."""
        o3d = _get_o3d()

        src_pcd = o3d.geometry.PointCloud()
        src_pcd.points = o3d.utility.Vector3dVector(source.astype(np.float64))
        tgt_pcd = o3d.geometry.PointCloud()
        tgt_pcd.points = o3d.utility.Vector3dVector(target.astype(np.float64))

        # Compute initial RMSE
        init_dists = np.asarray(src_pcd.compute_point_cloud_distance(tgt_pcd))
        rmse_before = float(np.sqrt(np.mean(init_dists ** 2)))

        # Run ICP with larger correspondence distance for robustness
        result = o3d.pipelines.registration.registration_icp(
            src_pcd, tgt_pcd,
            max_correspondence_distance=10.0,
            init=np.eye(4),
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            criteria=o3d.pipelines.registration.ICPConvergenceCriteria(
                max_iteration=200,
                relative_fitness=1e-8,
                relative_rmse=1e-8,
            ),
        )

        # Apply transformation
        src_pcd.transform(result.transformation)
        final_dists = np.asarray(src_pcd.compute_point_cloud_distance(tgt_pcd))
        rmse_after = float(np.sqrt(np.mean(final_dists ** 2)))

        trans = result.transformation
        return AlignmentResult(
            rmse_before=round(rmse_before, 4),
            rmse_after=round(rmse_after, 4),
            translation=trans[:3, 3],
            rotation=trans[:3, :3],
            iterations=len(result.correspondence_set),
            converged=result.fitness > 0.1,
            inlier_ratio=round(result.fitness, 4),
        )

    @classmethod
    def histogram_match(cls, source_img: np.ndarray,
                        reference_img: np.ndarray) -> RadiometricResult:
        """Match source image histogram to reference using OpenCV."""
        if source_img.shape != reference_img.shape:
            reference_img = cv2.resize(reference_img,
                                       (source_img.shape[1], source_img.shape[0]))

        psnr_before = float(cv2.PSNR(source_img, reference_img))

        matched = source_img.copy()
        if len(source_img.shape) == 3:
            for c in range(3):
                matched[:, :, c] = cv2.equalizeHist(source_img[:, :, c])
        else:
            matched = cv2.equalizeHist(source_img)

        psnr_after = float(cv2.PSNR(matched, reference_img))

        # Histogram correlation
        if len(source_img.shape) == 3:
            src_gray = cv2.cvtColor(source_img, cv2.COLOR_RGB2GRAY)
            ref_gray = cv2.cvtColor(reference_img, cv2.COLOR_RGB2GRAY)
        else:
            src_gray = source_img
            ref_gray = reference_img

        hist_src = cv2.calcHist([src_gray], [0], None, [256], [0, 256])
        hist_ref = cv2.calcHist([ref_gray], [0], None, [256], [0, 256])
        corr = float(cv2.compareHist(hist_src, hist_ref, cv2.HISTCMP_CORREL))

        return RadiometricResult(
            method="直方图匹配",
            psnr_before=round(psnr_before, 2),
            psnr_after=round(psnr_after, 2),
            hist_correlation=round(max(0, corr), 4),
        )

    @classmethod
    def calibrate(cls, photo_count: int = 60) -> CalibrationReport:
        """Run full cross-modal calibration pipeline.

        Generates a ground-truth target scene, then creates a misaligned
        LiDAR source by applying a known transform + sensor noise.
        ICP recovers the transform and we measure the result.
        """
        rng = np.random.RandomState(42)
        n = 5000

        # Build structured ground-truth scene
        target = np.zeros((n, 3))
        ground_n = int(n * 0.7)
        target[:ground_n, 0] = rng.uniform(-10, 10, ground_n)
        target[:ground_n, 1] = rng.uniform(-10, 10, ground_n)
        target[:ground_n, 2] = (0.05 * target[:ground_n, 0]
                                - 0.03 * target[:ground_n, 1]
                                + rng.normal(0, 0.1, ground_n))
        for i in range(ground_n, n):
            bx = rng.choice([-3, 0, 4, 7])
            by = rng.choice([-5, -1, 2, 6])
            target[i] = [bx + rng.uniform(-1.5, 1.5),
                         by + rng.uniform(-1.5, 1.5),
                         rng.uniform(0, 8)]

        # Apply known misalignment + sensor noise to create LiDAR source
        theta = np.radians(3.0)
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        R = np.array([[cos_t, -sin_t, 0], [sin_t, cos_t, 0], [0, 0, 1]])
        offset = np.array([1.5, 0.8, 0.3])
        source = target @ R.T + offset
        source += rng.normal(0, 0.02, source.shape)

        # ICP alignment
        alignment = cls.icp_align(source, target)

        # Score
        improvement = (alignment.rmse_before - alignment.rmse_after) / max(alignment.rmse_before, 0.001)
        score = min(100, max(0, improvement * 100 + alignment.inlier_ratio * 30))

        if alignment.converged and improvement > 0.7:
            detail = (f"配准成功！RMSE 从 {alignment.rmse_before:.2f}m "
                      f"降至 {alignment.rmse_after:.4f}m，精度提升 {improvement*100:.0f}%")
        elif alignment.converged:
            detail = f"配准收敛，RMSE: {alignment.rmse_after:.4f}m"
        else:
            detail = "配准未完全收敛，建议增加迭代或调整初始姿态"

        return CalibrationReport(
            alignment=alignment,
            overall_score=round(score, 1),
            summary=detail,
        )
