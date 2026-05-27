"""Launch OYMM application with proper DLL paths."""
import os
import sys

# Add Qt6 DLL directory before importing PyQt6
qt_bin = "E:/Program/anaconda3/envs/oymm/Lib/site-packages/PyQt6/Qt6/bin"
os.add_dll_directory(qt_bin)

# Add project root to path
sys.path.insert(0, "E:/oymm")

from oymm_app.main import main

if __name__ == "__main__":
    main()
