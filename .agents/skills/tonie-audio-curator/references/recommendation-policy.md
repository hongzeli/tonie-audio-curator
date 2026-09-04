# Recommendation policy

1. Extract age/range, preferred and acceptable languages, interests, content types, exclusions, item duration, total duration, number of Tonies, and source constraints.
2. Browse authoritative catalogs/source pages and license pages. Every candidate must be real; never invent metadata.
3. Record title, author/uploader, type, language, verified duration or `unknown`, age range, source page, direct download availability, exact license, license URL, safety tags, and retrieval time.
4. Exclude unsafe, age-inappropriate, unreliable, or license-unclear candidates. Streaming access alone is insufficient.
5. Rank using age 30%, interest 25%, safety 15%, language 10%, duration composition 10%, license confidence 5%, and source quality 5%.
6. Validate `schemas/recommendations.schema.json`, write exactly 20 items to `workspace/<job-id>/recommendations.json`, display the 20 items with source and license, and stop. Do not download or produce a preview.

Use `unknown` only for a field the schema permits and make uncertainty visible. A direct file URL is not proof of a license; preserve source and license evidence separately.

