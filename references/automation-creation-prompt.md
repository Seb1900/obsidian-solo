# Automation creation prompt

Execute this prompt during installation after the vault is registered as a Codex project:

```text
Use the Codex automation management capability. Find the local project whose root is this Obsidian vault. Inspect existing automations and create or update two active local jobs without duplicates:

1. 知识库-每日信息收集, every day at 08:00 local time, using the daily collection execution prompt in the obsidian-solo-os Skill's references/automation-plan.md.
2. 知识库-三天增量迭代, every three days at 20:30 local time, using the three-day iteration execution prompt in the same reference.

Keep both jobs in the vault project and local execution environment. Record the resulting names, status, next run time, and identifiers in 06_系统/自动化任务.md. Do not write recurrence internals, commands, helper paths, or secrets into the vault. If the vault is not a Codex project, request only that project-registration action and resume afterward. If automation management is unavailable, leave both entries marked 待创建 and report that limitation.
```
