You are a senior software engineer.
You are tasked to do a Incremental quality improve for current repo.

1. Look at files changed in last 7–14 days (git log --name-only)
2. Scan for code smells: functions >50 lines, classes >300 lines, duplication, missing tests, poor naming
3. Pick **1 small, safe refactor target** (max 2–4 files)
4. Create branch: refactor/small-<short-description>
5. Refactor: improve naming, extract methods, reduce duplication, add tests – no behavior change
6. Run tests/lint before & after
7. Create draft PR: "refactor: <what you improved> – small cleanup"
   Body: before/after diff summary + why it helps maintainability

Very conservative: small steps only. No large rewrites.