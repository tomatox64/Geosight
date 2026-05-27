"""Generate synthetic aerial photos for testing the CC pipeline.

Creates a textured ground plane + colored cubes seen from multiple oblique angles,
simulating a simple aerial photography scenario.
"""

import numpy as np
from pathlib import Path
import cv2

OUT_DIR = Path("E:/oymm/data/photos/test_scene")


def create_scene_image(
    width: int = 1920,
    height: int = 1080,
    angle: float = 0,
    elevation: float = 45,
    distance: float = 100,
) -> np.ndarray:
    """Render a simple 3D-like scene with ground texture and objects."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Sky gradient
    for y in range(height // 2):
        t = y / (height // 2)
        color = np.array([200 + int(55 * t), 180 + int(40 * t), 100 + int(80 * t)])
        img[y, :] = color

    # Ground plane with perspective-like texture (checkerboard)
    horizon_y = height // 2 - int(50 * np.sin(np.radians(elevation)))
    ground_h = height - horizon_y

    rad = np.radians(angle)
    for y in range(horizon_y, height):
        py = (y - horizon_y) / ground_h  # 0 (far) to 1 (near)
        for x in range(width):
            # Simulate perspective ground coordinates
            px = (x - width / 2) / width * 2 * (1 - py * 0.8) * distance / 20
            pz = py * distance

            # Rotate
            rx = px * np.cos(rad) - pz * np.sin(rad)
            rz = px * np.sin(rad) + pz * np.cos(rad)

            # Checkerboard
            cx = int(np.floor(rx * 2))
            cz = int(np.floor(rz * 2))
            if (cx + cz) % 2 == 0:
                img[y, x] = (60, 120, 50)
            else:
                img[y, x] = (80, 150, 70)

    # Add some colored "buildings" (rectangles on the ground)
    buildings = [
        (0.3, 0.4, 0.08, 0.06, (180, 150, 100)),   # building 1
        (-0.2, 0.35, 0.06, 0.08, (200, 190, 170)),  # building 2
        (0.1, 0.5, 0.05, 0.04, (160, 140, 120)),    # building 3
        (-0.5, 0.45, 0.07, 0.05, (190, 170, 140)),  # building 4
        (0.6, 0.5, 0.04, 0.07, (220, 200, 180)),    # building 5
    ]

    for bx, bz, bw, bd, color in buildings:
        # Project building position to image coordinates
        rx = bx * np.cos(rad) - bz * np.sin(rad)
        rz = bx * np.sin(rad) + bz * np.cos(rad)

        if rz <= 0:
            continue  # Behind camera

        py_img = rz / distance
        if py_img <= 0 or py_img >= 1:
            continue

        yi = int(horizon_y + py_img * ground_h)
        xi = int(width / 2 + rx / (1 - py_img * 0.8) / 2 * width)

        bhi = int(bd * 200 * (1 - py_img * 0.5))
        bwi = int(bw * 300 * (1 - py_img * 0.5))

        y1 = max(horizon_y, yi - bhi)
        y2 = min(height - 1, yi)
        x1 = max(0, xi - bwi // 2)
        x2 = min(width - 1, xi + bwi // 2)

        if y2 > y1 and x2 > x1:
            # Shade based on distance
            shade = 1 - py_img * 0.4
            col = tuple(min(255, int(c * shade)) for c in color)
            img[y1:y2, x1:x2] = col

    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating synthetic test photos in {OUT_DIR}...")

    angles = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
    elevations = [35, 40, 45, 50, 55]

    count = 0
    for elev in elevations:
        for ang in angles:
            img = create_scene_image(angle=ang, elevation=elev)
            # Add slight variation
            path = OUT_DIR / f"img_{ang:03d}_{elev:02d}.jpg"
            cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            count += 1

    print(f"Generated {count} synthetic photos at {OUT_DIR}")
    return 0


if __name__ == "__main__":
    main()
