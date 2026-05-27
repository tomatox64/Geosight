"""Engine bridge - calls Python 3.6 worker via subprocess.

The photogrammetry SDK only supports Python 3.6, so the main
Python 3.11 app invokes a thin Python 3.6 worker for compute operations.
"""

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any

PY36 = Path("E:/Program/anaconda3/envs/oymm-cc/python.exe")
WORKER = Path("E:/oymm/scripts/cc_worker.py")
ENGINE_BIN = Path("E:/Program/Bentley/ContextCapture/bin")


def _call_worker(command: str, args: dict | None = None) -> dict[str, Any]:
    """Call the Python 3.6 worker and return parsed JSON result."""
    cmd = [str(PY36), str(WORKER), command]
    if args:
        cmd.append(json.dumps(args, ensure_ascii=False))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(WORKER.parent),
        )
        if result.returncode != 0 and not result.stdout.strip():
            return {"ok": False, "error": result.stderr.strip() or "Unknown error"}
        return json.loads(result.stdout.strip() or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Operation timed out"}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid response from worker: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EngineJob:
    job_id: str
    status: JobStatus
    progress: float = 0.0
    message: str = ""


class Project:
    """Represents a photogrammetry project."""

    def __init__(self, project_dir: Path, name: str):
        self.name = name
        self.project_dir = Path(project_dir)
        self.ccm_path = self.project_dir / f"{name}.ccm"
        self.photos_dir = self.project_dir / "Photos"

    def exists(self) -> bool:
        return self.ccm_path.exists()


class EngineBridge:
    """Facade for photogrammetry operations via Python 3.6 worker."""

    @staticmethod
    def version() -> str:
        result = _call_worker("status")
        if result.get("ok"):
            return f"Engine {result.get('version')}"
        return "Engine (unknown)"

    @staticmethod
    def is_installed() -> bool:
        return PY36.exists() and WORKER.exists()

    @staticmethod
    def license_valid() -> bool:
        result = _call_worker("status")
        return result.get("license_valid", False)

    @staticmethod
    def create_project(photos_dir: Path, project_dir: Path, name: str) -> dict:
        """Create a project and import photos."""
        return _call_worker("create_project", {
            "photos_dir": str(photos_dir),
            "project_dir": str(project_dir),
            "name": name,
        })

    @staticmethod
    def run_aerotriangulation(project_path: Path, density: str = "normal") -> dict:
        """Run aerial triangulation."""
        return _call_worker("run_at", {
            "project_path": str(project_path),
            "keypoints_density": density,
        })

    @staticmethod
    def run_reconstruction(project_path: Path) -> dict:
        """Create reconstruction from AT results."""
        return _call_worker("run_reconstruct", {
            "project_path": str(project_path),
        })

    @staticmethod
    def get_photo_poses(project_path: Path) -> dict:
        """Get photo positions from AT results."""
        return _call_worker("get_photo_poses", {
            "project_path": str(project_path),
        })

    @staticmethod
    def get_tie_points(project_path: Path) -> dict:
        """Get tie points (sparse point cloud) from AT results."""
        return _call_worker("get_tie_points", {
            "project_path": str(project_path),
        })

    @staticmethod
    def run_production(
        project_path: Path,
        output_format: str = "OBJ",
        texture: bool = True,
        texture_quality: int = 80,
    ) -> dict:
        """Submit production/export job."""
        return _call_worker("run_production", {
            "project_path": str(project_path),
            "format": output_format,
            "texture": texture,
            "texture_quality": texture_quality,
        })

    def start_engine(self) -> bool:
        """Start engine process in background."""
        try:
            self._process = subprocess.Popen(
                [str(ENGINE_BIN / "CCEngine.exe")],
                cwd=str(ENGINE_BIN),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def stop_engine(self):
        if hasattr(self, "_process") and self._process:
            self._process.terminate()
            self._process.wait(timeout=10)


engine_bridge = EngineBridge()
