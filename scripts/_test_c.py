import sys
sys.path.insert(0, "E:/oymm")
print("import cv2 + numpy")
import cv2
import numpy as np
print("cv2:", cv2.__version__, "np:", np.__version__)
rng = np.random.RandomState(123)
x = rng.uniform(0, 1, 100)
print("random ok", x[:3])
