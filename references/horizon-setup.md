# Horizon setup contract

Source: `https://github.com/Thysrael/Horizon`.

At setup time, obtain Horizon with a shallow Git clone. When Git is unavailable, download the GitHub main-branch archive and verify its README and `pyproject.toml`. Record the source and commit when available.

Keep the runtime under `<vault>/.horizon-system`. The Skill package may contain `assets/horizon-profile/config.general.json`; it must not contain Horizon's `src`, `docs`, `.github`, `tests`, lockfile, or project metadata.

Use the upstream local installation flow: synchronize with `uv`, store secrets in the ignored `.env`, store source configuration in `data/config.json`, and run `uv run horizon`. Do not patch upstream source files.

Enable Hacker News, anonymous GitHub, RSS, Reddit public endpoints, Telegram public channels, OSS Insight, GDELT, and Google News. Leave X/Twitter absent. Remove inherited `GITHUB_TOKEN` from the run environment so GitHub remains at its anonymous limit.

Use the general profile for new installations. During upgrades, remove the obsolete role-specific filter from the existing OSS Insight keyword list, preserve user-added keywords, and add any missing general-profile keywords.

The terminal provider picker is the only secret-entry surface. It must render immediately with the title “Horizon AI 服务配置”, show input feedback as stars, support Windows Ctrl+V and normal macOS terminal paste, remove inactive provider keys, and never echo the secret.

Provider setup is asynchronous. The first setup call returns `awaiting-provider` as soon as the window opens. After valid input, the window writes `provider-ready` and launches dependency synchronization plus first-report generation in the background. Use `scripts/horizon_status.py` to read `provider-window-open`, `provider-ready`, `dependencies-running`, `dependencies-ready`, `first-report-running`, `first-report-ready`, `complete`, or `error`. Do not infer the stage from process names or `.env` existence, and do not read `.env`.

Keep the stage file until the full setup is complete. If provider status is missing but the selected provider and its key are internally complete, recover to `provider-ready` without showing the window again. A failed or closed provider window may be reopened once with `--reopen-provider`.

Generate one first report after a successful new installation. Reuse that result during later setup checks. Daily automation imports subsequent reports into `00_输入/原始资料/资讯日报/<timestamp>`.
