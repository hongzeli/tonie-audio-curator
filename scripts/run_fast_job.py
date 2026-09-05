from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT
    from scripts.download_audio import download_selection
    from scripts.package_audio import finalize_delivery
    from scripts.process_audio import process_report
    from scripts.upload_google_drive import prepare_upload_plan
except ModuleNotFoundError:
    from common import PROJECT_ROOT
    from download_audio import download_selection
    from package_audio import finalize_delivery
    from process_audio import process_report
    from upload_google_drive import prepare_upload_plan


def run_job(
    selection_path: Path,
    workspace_root: Path,
    output_root: Path,
    profile_path: Path,
    drive_config_path: Path,
) -> dict:
    downloads = download_selection(selection_path, workspace_root)
    processing = process_report(
        workspace_root / downloads["job_id"] / "download-report.json",
        output_root,
        profile_path,
    )
    delivery = finalize_delivery(output_root / downloads["job_id"] / "processing-report.json")
    plan = prepare_upload_plan(output_root / downloads["job_id"], drive_config_path)
    return {
        "job_id": downloads["job_id"],
        "requested": processing["summary"]["requested"],
        "downloaded": processing["summary"]["downloaded"],
        "converted": delivery["mp3_count"],
        "failed": processing["summary"]["failed"] + processing["summary"]["download_failed"],
        "delivery_dir": delivery["delivery_dir"],
        "zip_created": False,
        "drive_upload_file_count": len(plan["files"]),
        "drive_destination_name": plan["destination_name"],
        "drive_target_parent_id": plan["target_parent_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fast Tonie audio workflow after explicit confirmation")
    parser.add_argument("selection", type=Path)
    parser.add_argument("--workspace", type=Path, default=PROJECT_ROOT / "workspace")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output")
    parser.add_argument("--profile", type=Path, default=PROJECT_ROOT / "config" / "audio-profile.json")
    parser.add_argument("--drive-config", type=Path, default=PROJECT_ROOT / "config" / "google-drive.json")
    args = parser.parse_args()
    result = run_job(
        args.selection.resolve(),
        args.workspace.resolve(),
        args.output.resolve(),
        args.profile.resolve(),
        args.drive_config.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["converted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
