# Fast recommendation policy

1. Extract age, languages, interests, content type, exclusions, and item duration; default missing non-material details.
2. Prefer `scripts/research_commons.py "<query>" --output workspace/<job-id>/candidates.json` to save roughly 20–30 machine-readable candidates locally. Read only its compact count before filtering.
3. Research at most 12 candidates. For each work, collect at most one educational/library signal, one credible review/editorial signal, and one readily available play-count signal. Cache work-level findings for 180 days in `workspace/cache/work-reputation.json`.
4. Distinguish the underlying work's reputation from the specific recording. Popularity never overrides age safety or licensing.
5. Rank with age 25%, interest 20%, safety 15%, reputation 15%, duration 10%, license 7%, recording quality 5%, and language 3%.
6. Record the real title, author/uploader, duration or `unknown`, source page, direct availability, exact license, safety tags, and a compact reputation object. Never invent missing evidence.
7. Validate `schemas/recommendations.schema.json`, save at most 8 items to `workspace/<job-id>/recommendations.json`, display one short reason per item, and stop for confirmation.

Streaming access is not a license. Do not broaden to an unreliable source to fill all 8 slots.
