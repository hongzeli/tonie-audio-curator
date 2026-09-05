---
name: tonie-audio-curator
description: Quickly research, recommend, confirm, convert, and deliver legal child-friendly MP3 audio for Creative-Tonie. Use for Tonie/Toniebox curation; never use it to extract protected streaming media or bypass access controls.
---

# Tonie Audio Curator

Read the root `AGENTS.md` before acting. Keep model-visible output compact; local scripts own download, conversion, checkpointing, and delivery preparation.

## Choose the current phase

- For a new request, collect only facts that materially affect results.
- For research/recommendation, read [references/recommendation-policy.md](references/recommendation-policy.md).
- For explicit confirmation or later stages, read [references/execution-workflow.md](references/execution-workflow.md).

Do not treat edits, questions, sorting, or source checks as download permission. Only a clear confirmation of numbered items authorizes selection and downstream processing.

Never extract from Spotify, Apple Music, Audible, YouTube, or other streaming sources; bypass DRM, login, payment, or geographic controls; use untrusted download sites; or infer copying rights from playback access.

Keep child profiles and task artifacts under `workspace/` or `output/`; do not commit or upload the profile. Do not print full logs, caches, FFmpeg output, or per-file Drive metadata unless diagnosing a failure.
