---
name: tonie-audio-curator
description: Research, recommend, confirm, download, normalize, package, and deliver legal child-friendly audio for Creative-Tonie. Use for Tonie/Toniebox audio curation; never use it to extract protected streaming media or bypass access controls.
---

# Tonie Audio Curator

Use this project Skill to coordinate research and the deterministic scripts in the repository root. Read the root `AGENTS.md` before acting.

## Choose the current phase

- For a new request, collect only missing facts that materially affect results. Reasonable defaults are allowed when disclosed.
- For research/recommendation, read [references/recommendation-policy.md](references/recommendation-policy.md).
- For explicit confirmation or later stages, read [references/execution-workflow.md](references/execution-workflow.md).

Do not treat edits, questions, sorting, or source checks as download permission. Only a clear confirmation of numbered items authorizes selection and downstream processing.

Never extract from Spotify, Apple Music, Audible, YouTube, or other streaming sources; bypass DRM, login, payment, or geographic controls; substitute untrusted download sites; or infer copying rights from playback access.

Keep child profiles and all task artifacts under `workspace/` or `output/`; do not commit or upload the profile. The local scripts own download, FFmpeg, packaging, and verification logic—do not reproduce those algorithms in chat.

