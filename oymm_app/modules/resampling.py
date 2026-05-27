"""模块3: 动态补采建议 - 空洞检测与航线建议."""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Waypoint:
    """A suggested shooting position."""
    x: float
    y: float
    altitude: float
    direction: str = "N"  # N/S/E/W
    priority: str = "normal"  # high/normal/low


@dataclass
class GapRegion:
    """A detected gap that needs re-shooting."""
    id: int
    x_center: float
    y_center: float
    area_pct: float  # % of total area
    coverage_pct: float  # current coverage in this region
    severity: str = "low"  # critical/high/medium/low
    suggested_waypoints: list[Waypoint] = field(default_factory=list)


@dataclass
class CoverageMap:
    """2D coverage analysis."""
    grid: np.ndarray  # coverage values 0-1
    gap_mask: np.ndarray  # boolean, True = gap
    total_area: float
    covered_area: float
    gap_area: float

    @property
    def coverage_pct(self) -> float:
        if self.total_area <= 0:
            return 0
        return self.covered_area / self.total_area * 100

    @property
    def gap_pct(self) -> float:
        if self.total_area <= 0:
            return 0
        return self.gap_area / self.total_area * 100


@dataclass
class ResamplingReport:
    coverage: CoverageMap
    gaps: list[GapRegion]
    suggested_waypoints: list[Waypoint]
    total_photos: int
    needs_resampling: bool
    summary: str = ""


class ResamplingAnalyzer:
    """Analyzes coverage and suggests re-shooting positions."""

    GRID_SIZE = 32

    @classmethod
    def analyze(cls, photo_count: int, estimated_overlap_pct: float,
                width: int = 1920, height: int = 1080) -> ResamplingReport:
        """Generate coverage analysis and gap suggestions.

        For demo purposes, simulates coverage grid with realistic patterns.
        In production, this would use actual AT pose data.
        """
        grid = cls._build_coverage_grid(photo_count, estimated_overlap_pct,
                                         width, height)
        gap_mask = grid < 0.25  # <25% coverage = gap

        total_cells = grid.size
        covered_cells = int(np.sum(grid >= 0.25))
        gap_cells = int(np.sum(gap_mask))

        coverage = CoverageMap(
            grid=grid,
            gap_mask=gap_mask,
            total_area=total_cells,
            covered_area=covered_cells,
            gap_area=gap_cells,
        )

        gaps = cls._detect_gaps(grid, gap_mask)
        waypoints = cls._generate_waypoints(gaps)

        needs = coverage.coverage_pct < 80 or len(gaps) > 0

        if needs:
            summary = (f"发现 {len(gaps)} 个覆盖不足区域，"
                       f"建议补拍 {len(waypoints)} 个点位")
        else:
            summary = f"覆盖度良好 ({coverage.coverage_pct:.0f}%)，无需补拍"

        return ResamplingReport(
            coverage=coverage,
            gaps=gaps,
            suggested_waypoints=waypoints,
            total_photos=photo_count,
            needs_resampling=needs,
            summary=summary,
        )

    @classmethod
    def _build_coverage_grid(cls, n_photos: int, overlap_pct: float,
                              width: int, height: int) -> np.ndarray:
        """Build synthetic coverage grid based on photo count and overlap."""
        size = cls.GRID_SIZE
        grid = np.zeros((size, size), dtype=np.float32)

        aspect = width / height if height > 0 else 1.78
        photo_grid_w = max(4, int(np.sqrt(n_photos * aspect)))
        photo_grid_h = max(4, int(n_photos / photo_grid_w))

        # Radius scales with overlap: higher overlap → photos cover wider area
        base_radius = size / photo_grid_w
        radius = int(base_radius * (1.0 + overlap_pct / 100 * 1.5))

        for i in range(photo_grid_h):
            for j in range(photo_grid_w):
                cx = int((j + 0.5) / photo_grid_w * size)
                cy = int((i + 0.5) / photo_grid_h * size)

                y1 = max(0, cy - radius)
                y2 = min(size, cy + radius + 1)
                x1 = max(0, cx - radius)
                x2 = min(size, cx + radius + 1)

                yy, xx = np.ogrid[y1:y2, x1:x2]
                dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                falloff = np.clip(1 - dist / radius, 0, 1)
                grid[y1:y2, x1:x2] = np.maximum(grid[y1:y2, x1:x2], falloff)

        # Mild edge fade: edges degrade to ~60% of max, not zero
        edge = np.ones((size, size), dtype=np.float32)
        fade_zone = size * 0.08
        for i in range(size):
            for j in range(size):
                di = min(i, size - 1 - i)
                dj = min(j, size - 1 - j)
                factor = min(1.0, min(di, dj) / fade_zone) if fade_zone > 0 else 1.0
                edge[i, j] = 0.6 + 0.4 * factor

        grid = grid * edge
        noise = np.random.RandomState(42).normal(0, 0.02, (size, size))
        grid = np.clip(grid + noise, 0, 1)

        return grid

    @classmethod
    def _detect_gaps(cls, grid: np.ndarray,
                     gap_mask: np.ndarray) -> list[GapRegion]:
        """Find contiguous gap regions using simple flood-fill."""
        size = grid.shape[0]
        visited = np.zeros_like(gap_mask, dtype=bool)
        regions = []

        for y in range(size):
            for x in range(size):
                if gap_mask[y, x] and not visited[y, x]:
                    # Flood fill
                    cells = []
                    stack = [(y, x)]
                    visited[y, x] = True
                    while stack:
                        cy, cx = stack.pop()
                        cells.append((cy, cx))
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < size and 0 <= nx < size:
                                if gap_mask[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    stack.append((ny, nx))

                    if len(cells) >= 3:  # Minimum gap size
                        ys = [c[0] for c in cells]
                        xs = [c[1] for c in cells]
                        cy = np.mean(ys) / size
                        cx = np.mean(xs) / size
                        cov = float(np.mean([grid[c[0], c[1]] for c in cells]))

                        area_pct = len(cells) / (size * size) * 100
                        severity = ("critical" if area_pct > 10 else
                                    "high" if area_pct > 5 else
                                    "medium" if area_pct > 2 else "low")

                        regions.append(GapRegion(
                            id=len(regions) + 1,
                            x_center=round(cx, 3),
                            y_center=round(cy, 3),
                            area_pct=round(area_pct, 1),
                            coverage_pct=round(cov * 100, 1),
                            severity=severity,
                        ))

        return sorted(regions, key=lambda g: g.area_pct, reverse=True)

    @classmethod
    def _generate_waypoints(cls, gaps: list[GapRegion]) -> list[Waypoint]:
        """Generate suggested shooting positions for each gap."""
        waypoints = []
        alt_base = 100  # meters

        for gap in gaps:
            n_wp = 1 if gap.area_pct < 3 else 2 if gap.area_pct < 8 else 3
            alt = alt_base + 20 * (1 - gap.coverage_pct / 100)

            for i in range(n_wp):
                offset_x = (i - (n_wp - 1) / 2) * 0.02
                offset_y = 0 if n_wp == 1 else (i - (n_wp - 1) / 2) * 0.02
                waypoints.append(Waypoint(
                    x=round(gap.x_center + offset_x, 3),
                    y=round(gap.y_center + offset_y, 3),
                    altitude=round(alt, 0),
                    direction=["N", "E", "S", "W"][i % 4],
                    priority=gap.severity,
                ))

        return waypoints
