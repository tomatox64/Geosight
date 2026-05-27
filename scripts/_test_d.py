import sys
sys.path.insert(0, "E:/oymm")
print("import CalibrationEngine...")
from oymm_app.modules.calibration import CalibrationEngine
import numpy as np
print("calling generate_synthetic_lidar(10)...")
try:
    pts = CalibrationEngine.generate_synthetic_lidar(10)
    print("result:", pts.shape)
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
