# Confirmed fast workflow

Proceed only after the user clearly confirms recommendation numbers.

1. Copy only confirmed records, in order, to `workspace/<job-id>/selection.json`; add confirmation time and source recommendation path, then validate it.
2. Run `scripts/run_fast_job.py workspace/<job-id>/selection.json`. It checkpoints each download, performs one-pass MP3 conversion, creates playlist/licenses, and writes a Drive upload plan.
3. Read only the command's compact JSON. Inspect detailed reports only for failed items.
4. Create the random destination named in `drive-upload-plan.json` under its cached parent ID. Do not search for the root or check for duplicates.
5. Upload all plan entries in parallel. Do not upload raw sources, logs, child profiles, reports, or ZIP files; do not change sharing.
6. Do not list or read back the destination. Report “Drive accepted” only for successful upload API results.

Summarize requested, downloaded, converted, failed, Drive-accepted count, local directory, and Drive URL. State that duration, output audio, and Drive readback were not verified.
