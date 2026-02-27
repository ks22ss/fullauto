You are tasked to do a quick dependency & security scan.

1. Run security scanner (npm audit / pip-audit / cargo audit / osv-scanner / dependabot alerts if integrated)
2. If critical/high vulnerabilities found:
   - Create branch: security/fix-deps-<date>
   - Apply minimal version bumps / patches to fix
   - Update lockfile
   - Run tests to verify nothing broke
   - Create draft PR: "security: fix critical vulnerabilities in dependencies"
   - List CVEs / affected packages in PR body
3. If no critical issues → no action

Do not upgrade unrelated packages. Test thoroughly.

Then , you are tasked to do a Project health check – run on main branch.

1. git pull origin main
2. Run full test suite, lint, type check, build (whatever commands exist)
3. If any failure or warning:
   - Create new branch: fix/health-<timestamp>
   - Try to fix the issue(s) – small changes only
   - Add or improve tests that catch the problem
   - Commit fixes with clear messages
   - Push branch and create draft PR titled "fix: resolve health check failures"
   - In PR body: paste the failing output + what you fixed
4. If everything passes → no action, but log "main branch healthy"

Do not touch unrelated code. Fail-fast if fix is too complex – create issue instead.