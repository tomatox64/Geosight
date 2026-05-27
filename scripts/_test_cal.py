import sys
sys.path.insert(0, "E:/oymm")
from oymm_app.modules.calibration import CalibrationEngine
import numpy as np

rng = np.random.RandomState(42)
target = np.column_stack([
    rng.uniform(-10, 10, 100),
    rng.uniform(-10, 10, 100),
    rng.uniform(0, 8, 100),
])
source = CalibrationEngine.generate_synthetic_lidar(100)
print("source:", source.shape, "target:", target.shape)
print("ICP running...")
result = CalibrationEngine.icp_align(source, target)
print("Before:", result.rmse_before, "After:", result.rmse_after)
print("Converged:", result.converged, "Inliers:", result.inlier_ratio)
