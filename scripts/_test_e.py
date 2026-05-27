import sys, os
sys.path.insert(0, "E:/oymm")
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"

from oymm_app.modules.calibration import CalibrationEngine
print("has generate_synthetic_lidar:", hasattr(CalibrationEngine, "generate_synthetic_lidar"))
print("has icp_align:", hasattr(CalibrationEngine, "icp_align"))
# Just test with 10 points
pts = CalibrationEngine.generate_synthetic_lidar(10)
print("ok", pts.shape)
