# Profile maintenance contract

This is Xinglan233's GitHub profile repository, not a personal website.

## Preserve the intent
- Keep the existing avatar, GitHub native Popular/Pinned repositories and native contribution calendar. Do not change account settings or pinned items automatically.
- Use understated typography, generous but not excessive spacing, quiet gray surfaces and restrained blue accents. Support light/dark and narrow/wide layouts together.
- Keep prose specific and modest. Do not invent professional titles, achievements, technologies or project claims. Do not add generic AI-style slogans.
- No hero banners, typing animations, snake animations, trophy walls, visitor trackers, badge walls or redundant contribution charts.
- Keep one integrated statistics panel. Do not substitute mismatched remote widgets.
- Only the two linked public repositories are approved personal-project content. Do not inspect or publish private repository names, descriptions, language totals or code to enhance this profile.

## Implementation boundaries
- Preserve Markdown outside the PROFILE marker pair when refreshing statistics.
- Use the automatic repository GITHUB_TOKEN, not a personal access token or external API secret.
- Use only GitHub's API. Never persist credentials or raw API responses.
- Keep all pagination and privacy filters. Failed requests must preserve the last published statistics, never become zeros.
- The activity grade is a nonofficial heuristic, not a skills assessment or a measured global ranking.
- Top languages means eligible source bytes, not time spent or proficiency.
- Do not fabricate initial data. The initial em dashes are intentional.
- Never publish synthetic test fixtures as account statistics.
- Update all four SVG variants together; do not remove the text-based details.
- Do not force-push or weaken branch protection. Use a feature branch and PR when updating an existing profile.

## Verification
Run `python3 -m unittest discover -s tests -v`.
Use `python3 scripts/update_profile.py --init` only in a temporary copy for an offline empty-state preview: this command intentionally resets displayed statistics.
Test the four actual image variants at desktop and phone widths. Check that labels and percentages do not overlap.
Do not claim the Action ran successfully without inspecting its live result.
