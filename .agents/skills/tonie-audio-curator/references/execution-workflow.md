# Confirmed execution workflow

Proceed only after the user clearly confirms recommendation numbers.

1. Copy exactly the confirmed records, in user-requested order, to `workspace/<job-id>/selection.json`; add `confirmed_at`, `job_id`, source recommendations path, and single-package choice. Validate against `schemas/selection.schema.json`.
2. Run `scripts/download_audio.py`. Report skipped/failed items without replacing them from untrusted sources.
3. Run `scripts/process_audio.py`, then `scripts/package_audio.py`. Do not generate previews. Preserve local results when any later action fails.
4. Run `scripts/upload_google_drive.py prepare output/<job-id>`.
5. Through the connected Google Drive plugin, search for `Chatgpt工作区`. Require exactly one matching folder and record its Drive ID. If zero or multiple matches exist, stop and ask the user.
6. Create a fresh `Tonie Audio/<YYYY-MM-DD_job-id>` destination without overwriting. Upload only manifest-listed deliverables; never upload raw inputs, caches, failures, or the child profile, and never change sharing.
7. List the destination after upload. Save a compact remote listing with relative path, file ID, parent ID, and size; use `upload_google_drive.py verify` and report success only if it passes.

Summarize downloaded, skipped, failed, processed, overflow, package duration, local path, Drive destination ID, and readback verification.
