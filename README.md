# Tonie Audio Curator

Tonie Audio Curator combines an AI-guided recommendation workflow with deterministic local Python/FFmpeg tools. It finds verifiable, age-appropriate audio, waits for explicit confirmation, safely downloads only confirmed licensed items, normalizes them, groups them into Creative-Tonie-compatible 90-minute packages, and prepares verified delivery through the connected Google Drive plugin.

## Safety and product boundaries

- A recommendation run contains exactly 20 real, source-backed items and never starts a download.
- Downloads require explicit user confirmation and an unambiguous reusable license.
- The downloader rejects local/private network destinations, suspicious MIME/signature pairs, oversized files, excessive redirects, and invalid audio.
- The project never extracts from streaming services, converts YouTube, bypasses DRM/login/paywalls/regions, or generates preview files.
- Local tools do not store Google Drive or GitHub credentials.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- FFmpeg and ffprobe on `PATH`
- Git (GitHub CLI is also needed for repository creation/push)
- A connected Google Drive plugin in Codex for delivery

Install and check the local environment:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe scripts\verify_environment.py
```

## Workflow

1. Ask Codex to use the project-level `tonie-audio-curator` Skill and provide the child's age, languages, interests, content preferences, exclusions, and desired total duration.
2. Codex researches and writes exactly 20 source-backed items to `workspace/<job-id>/recommendations.json`, then stops.
3. Explicitly confirm recommendation numbers. Codex validates and writes `selection.json`.
4. Run the deterministic stages:

```powershell
.\.venv\Scripts\python.exe scripts\download_audio.py workspace\<job-id>\selection.json
.\.venv\Scripts\python.exe scripts\process_audio.py workspace\<job-id>\download-report.json
.\.venv\Scripts\python.exe scripts\package_audio.py output\<job-id>\processing-report.json
.\.venv\Scripts\python.exe scripts\upload_google_drive.py prepare output\<job-id> --target-folder-id 1QJbEZBo0BqsU-018KfWzvACu7eZHyi6g
```

The final upload is performed by Codex through the connected Google Drive plugin. The unique `Chatgpt工作区` folder ID is recorded in `config/google-drive.json`; re-search it before the first upload on another account or if the folder moves. Create `Tonie Audio/<YYYY-MM-DD_job-id>`, upload only manifest-listed deliverables, list the destination again, and verify size and parent ID. If duplicate root folders exist, the workflow stops for user selection.

## Input formats

`schemas/recommendations.schema.json` defines the fixed 20-item research result. `schemas/selection.schema.json` defines the explicitly confirmed subset and requires direct download URLs and non-unknown licenses. Keep recommendation and selection state under `workspace/`; it is intentionally ignored by Git.

## Audio defaults

Defaults live in `config/audio-profile.json`: MP3, 44.1 kHz, 160 kbps CBR, -18 LUFS, -1.5 dBTP, ID3v2.3, and at most 5,400 seconds per package. The first FFmpeg pass measures loudness; the second and only lossy encode applies measured normalization. Conservative denoising is added only when the analyzer returns a noise floor above the configured threshold.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

CI performs offline code tests and linting only. It does not research, download, upload, or retain audio.

## Project data and retention

Audio, downloads, task state, archives, credentials, and child profiles are excluded from Git. Raw downloads default to a seven-day local retention policy; deletion is an explicit user/admin operation and is not performed automatically by these tools.
