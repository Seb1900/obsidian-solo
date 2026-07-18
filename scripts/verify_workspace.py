import argparse
import json
import re
from pathlib import Path


REQUIRED_DIRECTORIES = (
    "00_输入", "01_理解", "02_知识", "03_项目", "04_成果", "05_复盘", "06_系统", "附件", "模板",
)
REQUIRED_TEMPLATES = (
    "输入模板.md", "理解模板.md", "知识条目模板.md", "项目模板.md", "成果模板.md",
    "复盘模板.md", "每日记录模板.md", "周复盘模板.md", "方法模板.md",
)
REQUIRED_PLUGINS = {"claudian": ("realclaudian", "claudian")}
LEGACY_ROOTS = (
    "00_INPUT", "01_TOPICS", "02_SCRIPTS", "03_PRODUCTION", "04_PUBLISHED", "05_PROJECTS",
    "06_KNOWLEDGE", "07_SKILLS", "08_REVIEWS", "09_SYSTEM", "ASSETS", "Templates",
    "01_UNDERSTAND", "02_CONTENT_ENGINE", "03_BUILD", "04_OUTPUT", "05_SYSTEM", "06_FEEDBACK",
)
FORBIDDEN_TERMS = (
    "\u9009\u9898\u5e93", "\u811a\u672c\u5e93", "\u5236\u4f5c\u770b\u677f",
    "\u53d1\u5e03\u4e0e\u6570\u636e", "\u4e2a\u4eba\u5de5\u4f5c\u53f0",
)


def frontmatter_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return set()
    return {line.split(":", 1)[0].strip() for line in match.group(1).splitlines() if ":" in line and not line.startswith((" ", "\t", "-"))}


def unresolved_links(vault: Path, paths: list[Path]) -> list[str]:
    notes = list(vault.rglob("*.md"))
    by_name = {path.stem for path in notes}
    failures = []
    for path in paths:
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8-sig", errors="ignore"), flags=re.DOTALL)
        for raw_link in re.findall(r"\[\[([^\]]+)\]\]", text):
            target = raw_link.split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            exact = vault / (target if target.endswith(".md") else target + ".md")
            if not exact.is_file() and Path(target).name not in by_name:
                failures.append(f"{path.relative_to(vault).as_posix()} -> {target}")
    return sorted(set(failures))


def plugin_checks(vault: Path) -> list[dict]:
    enabled_path = vault / ".obsidian" / "community-plugins.json"
    enabled = []
    if enabled_path.is_file():
        try:
            value = json.loads(enabled_path.read_text(encoding="utf-8-sig"))
            enabled = value if isinstance(value, list) else []
        except (OSError, ValueError):
            pass
    plugin_root = vault / ".obsidian" / "plugins"
    checks = []
    for plugin_id, aliases in REQUIRED_PLUGINS.items():
        matched = None
        for folder in plugin_root.iterdir() if plugin_root.is_dir() else ():
            manifest_path = folder / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                manifest = {}
            manifest_id = str(manifest.get("id") or folder.name)
            manifest_name = str(manifest.get("name") or "")
            if manifest_id in aliases or folder.name in aliases or (plugin_id == "claudian" and manifest_name.casefold() == "claudian"):
                matched = (manifest_id, folder.name)
                break
        checks.append({"check": f"plugin:{plugin_id}", "ok": bool(matched and ({matched[0], matched[1]} & set(enabled)))})
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-path", required=True)
    parser.add_argument("--content-only", action="store_true")
    args = parser.parse_args()
    vault = Path(args.vault_path).expanduser().resolve()
    checks = [{"check": f"directory:{name}", "ok": (vault / name).is_dir()} for name in REQUIRED_DIRECTORIES]
    for name in REQUIRED_TEMPLATES:
        path = vault / "模板" / name
        checks.append({"check": f"template:{name}", "ok": path.is_file() and bool(frontmatter_keys(path))})

    notes = [path for path in vault.rglob("*.md") if not any(part.startswith(".") for part in path.relative_to(vault).parts)]
    current_notes = [
        path for path in notes
        if path.name == "AGENTS.md" or path.relative_to(vault).parts[0] in REQUIRED_DIRECTORIES
    ]
    broken = unresolved_links(vault, current_notes)
    checks.append({"check": "navigation:links", "ok": not broken, "details": broken})
    checks.append({"check": "system:rules", "ok": (vault / "06_系统" / "系统规则.md").is_file()})
    checks.append({"check": "system:automation", "ok": (vault / "06_系统" / "自动化任务.md").is_file()})
    checks.append({"check": "system:iteration", "ok": (vault / "06_系统" / "知识库迭代机制.md").is_file()})

    legacy_paths = []
    for root_name in LEGACY_ROOTS:
        root = vault / root_name
        if root.exists():
            legacy_paths.append(root_name)
            if root.is_dir():
                legacy_paths.extend(path.relative_to(vault).as_posix() for path in root.rglob("*"))
    checks.append({"check": "content:no-legacy-paths", "ok": not legacy_paths, "details": sorted(legacy_paths)})
    dirty = [path.relative_to(vault).as_posix() for path in notes if any(term in path.read_text(encoding="utf-8-sig", errors="ignore") for term in FORBIDDEN_TERMS)]
    checks.append({"check": "content:generic", "ok": not dirty, "details": sorted(dirty)})
    checks.append({"check": "secrets:not-in-notes", "ok": not any(re.search(r"(?i)(sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,})", path.read_text(encoding="utf-8-sig", errors="ignore")) for path in notes)})
    if not args.content_only:
        checks.extend(plugin_checks(vault))

    failed = [item["check"] for item in checks if not item["ok"]]
    status = "ready" if not failed else "failed"
    print(json.dumps({"status": status, "vaultPath": str(vault), "checks": checks, "failed": failed}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
