"""模块8: 基础解译 - NDVI + 阈值分类."""
from dataclasses import dataclass
import numpy as np


@dataclass
class ClassificationResult:
    total_pixels: int
    vegetation_pct: float
    water_pct: float
    bareland_pct: float
    building_pct: float
    ndvi_mean: float
    ndvi_std: float
    summary: str = ""


class Classifier:
    @classmethod
    def analyze(cls) -> ClassificationResult:
        """Simulate NDVI analysis on the reconstructed scene."""
        rng = np.random.RandomState(77)
        n = 100000

        # Simulated NDVI distribution for a mixed urban-rural scene
        ndvi = np.concatenate([
            rng.normal(0.65, 0.12, int(n * 0.35)),   # Vegetation
            rng.normal(0.15, 0.08, int(n * 0.10)),   # Water
            rng.normal(0.25, 0.10, int(n * 0.20)),   # Bare land
            rng.normal(0.18, 0.06, int(n * 0.35)),   # Buildings/urban
        ])
        ndvi = np.clip(ndvi, -1, 1)

        veg = float(np.mean(ndvi > 0.4))
        water = float(np.mean(ndvi < 0.1))
        bare = float(np.mean((ndvi >= 0.1) & (ndvi <= 0.3)))
        building = float(np.mean((ndvi > 0.3) & (ndvi <= 0.4)))

        return ClassificationResult(
            total_pixels=n,
            vegetation_pct=round(veg * 100, 1),
            water_pct=round(water * 100, 1),
            bareland_pct=round(bare * 100, 1),
            building_pct=round(building * 100, 1),
            ndvi_mean=round(float(ndvi.mean()), 3),
            ndvi_std=round(float(ndvi.std()), 3),
            summary=f"植被覆盖 {veg:.0%} | 水体 {water:.0%} | 裸地 {bare:.0%} | 建筑 {building:.0%}"
        )
