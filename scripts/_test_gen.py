import sys
sys.path.insert(0, "E:/oymm")
from oymm_app.modules.calibration import CalibrationEngine
print("generating...")
pts = CalibrationEngine.generate_synthetic_lidar(100)
print("generated", len(pts), pts.dtype)
