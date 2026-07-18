---
name: obsidian-solo-os
description: Configure or upgrade an Obsidian vault into a general Codex-assisted Chinese knowledge system with user-configured Claudian/Codex integration, GitHub-installed Horizon collection, incremental Markdown knowledge compilation, and three-day iteration. Use when a user says “初始化”, asks to connect Codex with Obsidian, initialize or upgrade an Obsidian knowledge base, locate the Codex CLI path, install Horizon, or create recurring knowledge-base automations.
---

# Configure Obsidian Solo OS

Run the five stages in order. “初始化” starts stage 1. After the initialization message, treat “初始化完成”, “配置好了”, “安装好了”, “开始搭建”, “搭建知识库”, and equivalent wording as a request to recheck the objective gate and continue. Resume from the first incomplete stage recorded by the vault bootstrap result. Preserve user-authored files and keep secrets outside Markdown notes.

## 1. Verify Obsidian and Codex

For the literal request “初始化”, run `scripts/detect_environment.py --start-path <workspace>`, then run `scripts/render_initialization_guide.py --start-path <workspace>` and send its `userMessage` unchanged. Stop after sending it. For a completion reply or a request to build the vault, rerun detection directly. Continue immediately when a vault is selected and initialized, Claudian is enabled, and a verified CLI path exists. Render the guide again only when one of those objective requirements is still missing.

Do not call computer-use, browser control, Chrome control, or any UI automation during initialization or installation. Do not click, type, install, enable, or configure Obsidian plugins for the user. Initialization is read-only: report only missing plugins and the verified CLI path.

- Continue only when a vault is selected, initialized, and the Codex CLI passes both version and app-server probes.
- On `codex-not-found` or `codex-unhealthy`, tell the user that no usable CLI path was found. Do not install or repair the CLI automatically.
- Treat `needs-obsidian-ui` as an incomplete stage. Read `references/obsidian-plugin-setup.md` and give the user only the missing-plugin list and CLI path.
- Never create a Claudian conversation, load its model list, send a model request, or require a successful provider response. Proxies and relay services may reject Claudian while the vault setup remains valid; such a response is outside the initialization gate.
- Do not list plugins that are already enabled. If every detectable requirement passes, continue a pending build request without asking for another confirmation.
- Identify plugins from each selected vault's manifest ID, folder ID, and display name. Claudian currently uses `realclaudian`; do not assume its folder is named `claudian`.
- Resolve the CLI independently for each machine and user from configured environment variables, PATH, user-scoped package locations, and application locations. Probe every candidate and never hardcode or reuse another user's home path.
- Never edit Obsidian's plugin registry or Claudian settings files to simulate UI configuration.

## 2. Install or upgrade the knowledge system

Run `scripts/bootstrap_vault.py --vault-path <vault>`.

The bootstrapper uses a managed manifest. Merge file records from both the current `06_系统` manifest and the old system manifest before cleanup. Update unchanged Skill-managed files, remove obsolete Skill-managed files only when their current hash matches a merged manifest or bundled legacy hash, preserve edited or unknown files, and retain unresolved hashes in the new manifest for later upgrades. Remove empty obsolete directories and delete the old manifest only after the new manifest is written. Write conflicting new versions under `06_系统/升级候选`. Treat preserved obsolete files as unresolved upgrade conflicts. Read `references/knowledge-system-prompt.md` and execute it against the vault after bootstrap. Do not merely copy the prompt into the vault. Use only the Chinese generic structure installed by the current template. Do not create industry-specific business modules unless the user explicitly requests them in a later task. Do not create a compatibility map, initialization report, or verification note during the first build.

## 3. Install and configure Horizon

Read `references/horizon-setup.md`, then run `scripts/setup_horizon.py --vault-path <vault>` and interpret its structured stage result.

- Install Horizon from `https://github.com/Thysrael/Horizon` at setup time. The Skill contains only a configuration profile, never Horizon source code.
- Keep helper code in this Skill. Do not patch Horizon's `src` tree.
- Enable the configured public keyless sources, keep GitHub anonymous, and leave X/Twitter disabled.
- Collect the provider and API key only in the visible Windows or macOS terminal window. Never ask for a key in chat or a note.
- `awaiting-provider` means the visible provider window owns secret entry and the setup process has already returned. Give one short instruction, do not keep a blocking command open, and check `scripts/horizon_status.py` after the user finishes.
- Provider completion starts dependency and first-report work in the background. Report the current named stage; never repeat messages claiming the provider window is still waiting after the state reaches `provider-ready`.
- Generate and import the first report once. Reconfiguration must reuse a successful report unless the user requests another run.
- On a recoverable provider failure, reopen the provider window once and retry. Report only the action the user must take.

## 4. Optimize the vault as incremental knowledge

Read `references/karpathy-optimization-prompt.md` and execute it against the vault. Preserve original sources, update only affected knowledge pages, record evidence and dates, and send uncertain merges, contradictions, deletions, and large rewrites to the review queue.

## 5. Create recurring automations and verify

Read `references/automation-creation-prompt.md` and `references/automation-plan.md`. Execute the creation prompt; do not copy it into the vault.

When `automation_update` is available, resolve the Codex project whose local path is the vault and create or update, without duplicates:

1. Daily Horizon collection at 08:00 local time.
2. Full knowledge iteration every three days at 20:30 local time.

Use the creation instructions and execution prompts separately. Recurring runs must write dated reports under `06_系统/自动化/执行记录`. When automation tools or a vault project are unavailable, write the pending setup status to `06_系统/自动化任务.md` and give the user one necessary action.

Run `scripts/verify_workspace.py --vault-path <vault>`. Fix every failed required check. Report the vault path and verification result. Do not create additional interface pages.

Verification must scan the full vault. It must fail when any obsolete business path still exists, including an empty directory, or when deprecated business-module text remains anywhere in Markdown. Return verification through the process output only; do not write a verification report into the vault.

## Final report

Tell the user only:

- vault path;
- directories created, reused, or preserved as legacy;
- plugins detected and any plugin configuration left to the user;
- templates and automations created;
- Horizon and first-report status;
- any single remaining user action.

After a successful first build, end with this user guidance in natural Chinese: “知识库已经搭建完成。接下来你可以告诉我你的身份、所在行业、想持续了解的内容，以及你希望通过这些信息完成什么目标。我会据此调整信息来源、分类方式和迭代重点。”

Do not show commands, helper paths, dependencies, raw logs, internal state JSON, or API values.

## Safety contract

- Never overwrite a user-edited file.
- Delete an obsolete Skill-managed file during upgrade only when its hash matches the previous manifest. Preserve every edited or unknown file and report it as an upgrade conflict.
- Keep API keys only in Horizon's ignored `.env` file.
- Keep raw sources immutable and separate evidence from interpretation.
- Record every automated content change and confidence level.
- Apply automatic fixes only to indexes, backlinks, metadata, formatting, and summaries.
- Require review for factual conflicts, uncertain merges, unsupported claims, deletions, and broad rewrites.

## Resources

- `scripts/detect_environment.py`: verify platform, vault, plugins, Codex CLI, and app-server.
- `scripts/render_initialization_guide.py`: turn environment detection into one concise missing-action message.
- `scripts/bootstrap_vault.py`: install and safely migrate managed vault files.
- `scripts/setup_horizon.py`: obtain and configure Horizon from GitHub.
- `scripts/configure_ai_provider.py`: collect provider and secret in a terminal.
- `scripts/horizon_status.py`: report the persistent Horizon setup stage without reading secrets.
- `scripts/run_horizon.py`: run Horizon and import only a newly generated report.
- `scripts/verify_workspace.py`: verify the completed vault.
- `references/obsidian-plugin-setup.md`: user-performed plugin configuration and acceptance checks.
- `references/knowledge-system-prompt.md`: full system initialization prompt.
- `references/horizon-setup.md`: Horizon source, configuration, and recovery contract.
- `references/karpathy-optimization-prompt.md`: incremental wiki optimization prompt.
- `references/automation-plan.md`: automation creation and execution prompts.
- `references/automation-creation-prompt.md`: installation-time automation creation prompt.
- `assets/vault-template/`: managed knowledge folders, rules, and note templates.
- `assets/horizon-profile/`: Horizon configuration profile only.
