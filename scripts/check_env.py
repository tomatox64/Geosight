"""Verify all key packages import correctly."""
import sys
print(f"Python: {sys.version}")

packages = [
    ("PyQt6", "PYQT_VERSION_STR"),
    ("numpy", "__version__"),
    ("open3d", "__version__"),
    ("cv2", "__version__"),
    ("osgeo.gdal", "__version__"),
    ("pdal", "__version__"),
    ("rasterio", "__version__"),
    ("laspy", "__version__"),
    ("PIL", "__version__"),
    ("scipy", "__version__"),
    ("sklearn", "__version__"),
    ("pyvista", "__version__"),
    ("matplotlib", "__version__"),
]

results = []
for mod_name, attr in packages:
    try:
        mod = __import__(mod_name, fromlist=[attr]) if "." not in mod_name else \
              getattr(__import__(mod_name.rsplit(".", 1)[0]), mod_name.rsplit(".", 1)[1])
        version = getattr(mod, attr, None)
        results.append((mod_name, True, str(version) if version else "OK"))
    except Exception as e:
        results.append((mod_name, False, str(e)))

for name, ok, info in results:
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {name}: {info}")

failures = [r for r in results if not r[0]]
if failures:
    print(f"\n{failures} package(s) failed!")
    sys.exit(1)
else:
    print(f"\nAll {len(results)} packages OK")
