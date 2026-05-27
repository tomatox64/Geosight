import sys, os
sys.path.insert(0, "E:/oymm")
print("step 1: import")
from oymm_app.modules.calibration import CalibrationEngine
print("step 2: numpy")
import numpy as np
rng = np.random.RandomState(123)
x = rng.uniform(-10, 10, 100)
y = rng.uniform(-10, 10, 100)
z = rng.uniform(0, 8, 100)
pts = np.column_stack([x, y, z])
print("step 3: generated", pts.shape)
print("step 4: calling method...")
pts2 = CalibrationEngine.generate_synthetic_lidar(100)
print("step 5: ok", pts2.shape)
