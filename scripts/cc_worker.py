"""CC Worker - Python 3.6 bridge script for ContextCapture automation.

Called by the main PyQt app (Python 3.11) via subprocess.
Accepts JSON commands via stdin or first CLI argument, returns JSON results.

Commands:
  create_project  - Create a new CC project from photos
  run_at          - Run aerial triangulation on a project
  run_reconstruct - Run 3D reconstruction
  run_production  - Export results (FBX, OBJ, etc.)
  status          - Check CC license and version
"""

import sys
import os
import json
import time
import ccmasterkernel


def respond(data, exit_code=0):
    """Print JSON response and exit."""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def check_license():
    if not ccmasterkernel.isLicenseValid():
        return False, ccmasterkernel.lastLicenseErrorMsg()
    return True, None


def cmd_status(args):
    return {
        "ok": True,
        "version": ccmasterkernel.version(),
        "edition": ccmasterkernel.edition(),
        "license_valid": ccmasterkernel.isLicenseValid(),
    }


def cmd_create_project(args):
    """Create a CC project and import photos."""
    photos_dir = args.get("photos_dir")
    project_dir = args.get("project_dir")
    project_name = args.get("name", os.path.basename(project_dir))

    if not photos_dir or not project_dir:
        return {"ok": False, "error": "Missing photos_dir or project_dir"}

    if not os.path.isdir(photos_dir):
        return {"ok": False, "error": f"Photos directory not found: {photos_dir}"}

    project = ccmasterkernel.Project()
    project.setName(project_name)
    project.setDescription("Created by OYMM")

    os.makedirs(project_dir, exist_ok=True)
    project.setProjectFilePath(os.path.join(project_dir, project_name))

    err = project.writeToFile()
    if not err.isNone():
        return {"ok": False, "error": err.message}

    # Create block and import photos
    block = ccmasterkernel.Block(project)
    project.addBlock(block)
    block.setName("Block #1")

    photogroups = block.getPhotogroups()
    files = sorted(os.listdir(photos_dir))
    added = 0
    failed = []

    for f in files:
        path = os.path.join(photos_dir, f)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
            continue
        photo = photogroups.addPhotoInAutoMode(path)
        if photo is None:
            failed.append(f)
        else:
            added += 1
            if not photo.pose.center is None:
                block.setPositioningLevel(
                    ccmasterkernel.PositioningLevel.PositioningLevel_georeferenced
                )

    err = project.writeToFile()
    if not err.isNone():
        return {"ok": False, "error": err.message}

    project_path = os.path.join(project_dir, f"{project_name}.ccm")
    return {
        "ok": True,
        "project_path": project_path,
        "photos_added": added,
        "photos_failed": failed,
        "photogroups": photogroups.getNumPhotogroups(),
        "ready_for_at": block.isReadyForAT(),
    }


def cmd_run_at(args):
    """Run aerial triangulation."""
    project_path = args.get("project_path")
    if not project_path:
        return {"ok": False, "error": "Missing project_path"}

    # Load project
    project = ccmasterkernel.Project()
    err = project.readFromFile(project_path)
    if not err.isNone():
        return {"ok": False, "error": f"Failed to load project: {err.message}"}

    if project.getNumBlocks() < 1:
        return {"ok": False, "error": "No blocks in project"}

    block = project.getBlock(0)

    # Create AT block
    block_at = ccmasterkernel.Block(project)
    project.addBlock(block_at)
    block_at.setBlockTemplate(
        ccmasterkernel.BlockTemplate.Template_adjusted, block
    )

    # Configure AT settings
    density = args.get("keypoints_density", "normal")
    density_map = {
        "normal": ccmasterkernel.KeyPointsDensity.KeyPointsDensity_normal,
        "high": ccmasterkernel.KeyPointsDensity.KeyPointsDensity_high,
    }
    at_settings = block_at.getAT().getSettings()
    at_settings.keyPointsDensity = density_map.get(density, ccmasterkernel.KeyPointsDensity.KeyPointsDensity_normal)

    if not block_at.getAT().setSettings(at_settings):
        return {"ok": False, "error": "Failed to set AT settings"}

    err = project.writeToFile()
    if not err.isNone():
        return {"ok": False, "error": err.message}

    submit_err = block_at.getAT().submitProcessing()
    if not submit_err.isNone():
        return {"ok": False, "error": f"Failed to submit AT: {submit_err.message}"}

    # Wait for completion
    last_progress = -1
    last_status = None
    while True:
        status = block_at.getAT().getJobStatus()
        progress = block_at.getAT().getJobProgress()
        msg = block_at.getAT().getJobMessage()

        if status != last_status:
            status_name = ccmasterkernel.jobStatusAsString(status)
            last_status = status

        if progress != last_progress:
            last_progress = progress

        if status in (
            ccmasterkernel.JobStatus.Job_failed,
            ccmasterkernel.JobStatus.Job_cancelled,
            ccmasterkernel.JobStatus.Job_completed,
        ):
            break

        time.sleep(2)
        block_at.getAT().updateJobStatus()

    if status != ccmasterkernel.JobStatus.Job_completed:
        return {
            "ok": False,
            "error": f"AT failed: {block_at.getAT().getJobMessage()}"
        }

    return {
        "ok": True,
        "status": "completed",
        "project_path": project_path,
    }


def cmd_run_reconstruct(args):
    """Create reconstruction from AT result."""
    project_path = args.get("project_path")
    if not project_path:
        return {"ok": False, "error": "Missing project_path"}

    project = ccmasterkernel.Project()
    err = project.readFromFile(project_path)
    if not err.isNone():
        return {"ok": False, "error": f"Failed to load project: {err.message}"}

    # Find the AT block (last block)
    block_at = project.getBlock(project.getNumBlocks() - 1)

    if not block_at.isReadyForReconstruction():
        return {"ok": False, "error": "Block not ready for reconstruction"}

    reconstruction = ccmasterkernel.Reconstruction(block_at)
    block_at.addReconstruction(reconstruction)

    err = project.writeToFile()
    if not err.isNone():
        return {"ok": False, "error": err.message}

    return {
        "ok": True,
        "tiles": reconstruction.getNumInternalTiles(),
        "project_path": project_path,
    }


def cmd_run_production(args):
    """Submit production (export) job."""
    project_path = args.get("project_path")
    output_format = args.get("format", "OBJ")

    if not project_path:
        return {"ok": False, "error": "Missing project_path"}

    project = ccmasterkernel.Project()
    err = project.readFromFile(project_path)
    if not err.isNone():
        return {"ok": False, "error": f"Failed to load project: {err.message}"}

    block = project.getBlock(project.getNumBlocks() - 1)

    if block.getNumReconstructions() < 1:
        return {"ok": False, "error": "No reconstruction found"}

    reconstruction = block.getReconstruction(0)

    production = ccmasterkernel.Production(reconstruction)
    reconstruction.addProduction(production)
    production.setName("OYMM_Production")
    production.setDriverName(output_format)

    dest = os.path.join(project.getProductionsDirPath(), production.getName())
    production.setDestination(dest)

    # Configure output options
    driver_opts = production.getDriverOptions()
    texture = args.get("texture", True)
    quality = args.get("texture_quality", 80)
    driver_opts.put_bool("TextureEnabled", texture)
    driver_opts.put_int("TextureCompressionQuality", quality)
    production.setDriverOptions(driver_opts)

    err = project.writeToFile()
    if not err.isNone():
        return {"ok": False, "error": err.message}

    submit_err = production.submitProcessing()
    if not submit_err.isNone():
        return {"ok": False, "error": f"Failed to submit: {submit_err.message}"}

    # Wait for completion
    while True:
        status = production.getJobStatus()
        if status in (
            ccmasterkernel.JobStatus.Job_failed,
            ccmasterkernel.JobStatus.Job_cancelled,
            ccmasterkernel.JobStatus.Job_completed,
        ):
            break
        time.sleep(2)
        production.updateJobStatus()

    if status != ccmasterkernel.JobStatus.Job_completed:
        return {"ok": False, "error": f"Production failed: {production.getJobMessage()}"}

    return {
        "ok": True,
        "output_dir": production.getDestination(),
        "format": output_format,
    }


def cmd_get_photo_poses(args):
    """Extract photo positions after AT completion."""
    project_path = args.get("project_path")
    if not project_path:
        return {"ok": False, "error": "Missing project_path"}

    project = ccmasterkernel.Project()
    err = project.readFromFile(project_path)
    if not err.isNone():
        return {"ok": False, "error": f"Failed to load project: {err.message}"}

    poses = []
    for bi in range(project.getNumBlocks()):
        block = project.getBlock(bi)
        pgs = block.getPhotogroups()
        for gi in range(pgs.getNumPhotogroups()):
            pg = pgs.getPhotogroup(gi)
            photos = pg.getPhotoArray()
            for pi in range(len(photos)):
                photo = photos[pi]
                center = photo.pose.center
                if center is None:
                    continue
                poses.append({
                    "path": photo.imageFilePath,
                    "x": center.x,
                    "y": center.y,
                    "z": center.z,
                })

    return {
        "ok": True,
        "count": len(poses),
        "poses": poses,
    }


COMMANDS = {
    "status": cmd_status,
    "create_project": cmd_create_project,
    "run_at": cmd_run_at,
    "run_reconstruct": cmd_run_reconstruct,
    "run_production": cmd_run_production,
    "get_photo_poses": cmd_get_photo_poses,
}


def main():
    if len(sys.argv) < 2:
        respond({"ok": False, "error": "No command specified. Use: cc_worker.py <command> [json_args]"})

    cmd = sys.argv[1]

    if cmd not in COMMANDS:
        respond({"ok": False, "error": f"Unknown command: {cmd}. Available: {list(COMMANDS.keys())}"})

    # Read args from stdin if available, else from CLI or use empty
    args = {}
    if len(sys.argv) >= 3:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            respond({"ok": False, "error": "Invalid JSON args"})

    # Check license for commands that need it
    if cmd != "status":
        valid, err = check_license()
        if not valid:
            respond({"ok": False, "error": f"License error: {err}"})

    try:
        result = COMMANDS[cmd](args)
        respond(result)
    except Exception as e:
        respond({"ok": False, "error": str(e)})


if __name__ == "__main__":
    main()
