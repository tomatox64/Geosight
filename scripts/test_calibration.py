"""Quick test of calibration module."""
import sys
sys.path.insert(0, "E:/oymm")
from oymm_app.modules.calibration import CalibrationEngine

r = CalibrationEngine.calibrate(60)
print(f"Before RMSE: {r.alignment.rmse_before:.4f}m")
print(f"After  RMSE: {r.alignment.rmse_after:.4f}m")
print(f"Converged: {r.alignment.converged}")
print(f"Inliers: {r.alignment.inlier_ratio:.2%}")
print(f"Score: {r.overall_score}")
print(f"Summary: {r.summary}")
