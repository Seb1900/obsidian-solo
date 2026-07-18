import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


REQUIRED_PLUGINS = {
    "claudian": {"name": "Claudian", "ids": ("realclaudian", "claudian")},
}


def parent_vault(start: Path) -> Path | None:
    current = start if start.is_dir() else start.parent
    for candidate in (current, *current.parents):
        if (candidate / ".obsidian").is_dir():
            return candidate
    return None


def obsidian_config() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "obsidian" / "obsidian.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/obsidian/obsidian.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "obsidian" / "obsidian.json"


def existing(paths: list[Path | None]) -> list[str]:
    result = []
    for path in paths:
        if path and path.is_file():
            resolved = str(path.resolve())
            if resolved not in result:
                result.append(resolved)
    return result


def obsidian_apps() -> list[str]:
    command = shutil.which("obsidian")
    candidates: list[Path | None] = [Path(command) if command else None]
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        program_files = Path(os.environ.get("ProgramFiles", ""))
        candidates.extend([local / "Obsidian/Obsidian.exe", local / "Programs/Obsidian/Obsidian.exe", program_files / "Obsidian/Obsidian.exe"])
    elif sys.platform == "darwin":
        app = Path("/Applications/Obsidian.app")
        return [str(app)] if app.exists() else []
    return existing(candidates)


def codex_paths() -> list[str]:
    command = shutil.which("codex")
    configured = os.environ.get("CODEX_CLI_PATH") or os.environ.get("CODEX_PATH")
    home = Path.home()
    candidates: list[Path | None] = [
        Path(configured).expanduser() if configured else None,
        Path(command) if command else None,
        home / ".local/bin/codex",
        home / ".npm-global/bin/codex",
        home / ".bun/bin/codex",
    ]
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        appdata = Path(os.environ.get("APPDATA", ""))
        candidates.extend([
            local / "Programs/Codex/codex.exe",
            local / "Programs/OpenAI Codex/codex.exe",
            appdata / "npm/codex.cmd",
            local / "pnpm/codex.cmd",
        ])
        windows_apps = Path(os.environ.get("ProgramFiles", "")) / "WindowsApps"
        if windows_apps.is_dir():
            candidates.extend(windows_apps.glob("OpenAI.Codex_*/app/resources/codex.exe"))
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Applications/Codex.app/Contents/Resources/codex"),
            Path.home() / ".local/bin/codex",
            Path("/opt/homebrew/bin/codex"),
            Path("/usr/local/bin/codex"),
            Path.home() / "Library/pnpm/codex",
        ])
    return existing(candidates)


def probe(command: str, args: list[str], timeout: int = 8) -> dict:
    try:
        result = subprocess.run([command, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=timeout)
        first_line = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
        return {"ok": result.returncode == 0, "exitCode": result.returncode, "summary": first_line[:200]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "exitCode": None, "summary": type(exc).__name__}


def plugin_status(vault: Path | None) -> dict:
    if not vault:
        return {
            plugin_id: {"name": requirement["name"], "installed": False, "enabled": False, "resolvedId": None}
            for plugin_id, requirement in REQUIRED_PLUGINS.items()
        }
    obsidian = vault / ".obsidian"
    plugin_root = obsidian / "plugins"
    enabled_path = obsidian / "community-plugins.json"
    enabled = []
    if enabled_path.is_file():
        try:
            value = json.loads(enabled_path.read_text(encoding="utf-8-sig"))
            enabled = value if isinstance(value, list) else []
        except (OSError, ValueError):
            pass
    discovered = []
    if plugin_root.is_dir():
        for folder in plugin_root.iterdir():
            manifest_path = folder / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                manifest = {}
            discovered.append({
                "folder": folder.name,
                "id": str(manifest.get("id") or folder.name),
                "name": str(manifest.get("name") or ""),
            })
    result = {}
    enabled_set = {str(item) for item in enabled}
    for plugin_id, requirement in REQUIRED_PLUGINS.items():
        aliases = {item.casefold() for item in requirement["ids"]}
        display_name = requirement["name"].casefold()
        match = next((item for item in discovered if item["id"].casefold() in aliases or item["folder"].casefold() in aliases or item["name"].casefold() == display_name), None)
        resolved_id = match["id"] if match else None
        enabled_match = bool(match and ({match["id"], match["folder"]} & enabled_set))
        result[plugin_id] = {
            "name": requirement["name"],
            "installed": bool(match),
            "enabled": enabled_match,
            "resolvedId": resolved_id,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-path", default=os.getcwd())
    args = parser.parse_args()
    start = Path(args.start_path).expanduser().resolve()
    config_path = obsidian_config()
    vaults = []
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
            for vault_id, value in raw.get("vaults", {}).items():
                path = Path(unquote(value.get("path", ""))).expanduser()
                vaults.append({
                    "id": vault_id,
                    "path": str(path),
                    "exists": path.is_dir(),
                    "initialized": (path / ".obsidian").is_dir(),
                    "open": bool(value.get("open")),
                    "timestamp": value.get("ts"),
                })
        except (OSError, ValueError):
            pass
    nearby = parent_vault(start)
    if nearby and not any(Path(item["path"]) == nearby for item in vaults):
        vaults.append({"id": "workspace", "path": str(nearby), "exists": True, "initialized": True, "open": True, "timestamp": None})
    valid = [item for item in vaults if item["exists"]]
    selected = str(nearby) if nearby else next((item["path"] for item in sorted(valid, key=lambda item: item.get("timestamp") or 0, reverse=True) if item["open"]), None)
    if not selected and len(valid) == 1:
        selected = valid[0]["path"]
    selected_path = Path(selected) if selected else None

    cli_paths = codex_paths()
    probes = []
    preferred = None
    version_probe = {"ok": False, "exitCode": None, "summary": "not-found"}
    app_server_probe = {"ok": False, "exitCode": None, "summary": "not-probed"}
    for candidate in cli_paths:
        candidate_version = probe(candidate, ["--version"])
        candidate_app_server = probe(candidate, ["app-server", "--help"]) if candidate_version["ok"] else {"ok": False, "exitCode": None, "summary": "not-probed"}
        probes.append({"path": candidate, "version": candidate_version, "appServer": candidate_app_server})
        if not preferred and candidate_version["ok"] and candidate_app_server["ok"]:
            preferred = candidate
            version_probe = candidate_version
            app_server_probe = candidate_app_server
    plugins = plugin_status(selected_path)
    missing_plugins = [plugin_id for plugin_id, state in plugins.items() if not state["enabled"]]
    apps = obsidian_apps()
    installed = bool(apps or config_path.exists())
    initialized = bool(selected_path and (selected_path / ".obsidian").is_dir())

    if not installed:
        state = "obsidian-not-found"
    elif not valid:
        state = "vault-not-found"
    elif not selected:
        state = "vault-selection-required"
    elif not initialized:
        state = "vault-not-initialized"
    elif not preferred:
        state = "codex-unhealthy" if cli_paths else "codex-not-found"
    elif missing_plugins:
        state = "needs-obsidian-ui"
    else:
        state = "ready"

    print(json.dumps({
        "connectionState": state,
        "platform": sys.platform,
        "startPath": str(start),
        "obsidian": {
            "installed": installed,
            "executablePaths": apps,
            "configPath": str(config_path),
            "vaults": vaults,
            "selectedVault": selected,
            "selectedVaultInitialized": initialized,
            "plugins": plugins,
            "missingPlugins": missing_plugins,
            "communityPluginsEnabled": bool(selected_path and (selected_path / ".obsidian" / "community-plugins.json").is_file()),
        },
        "codex": {
            "found": bool(preferred),
            "cliPaths": cli_paths,
            "preferredCliPath": preferred,
            "probes": probes,
            "versionProbe": version_probe,
            "appServerProbe": app_server_probe,
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
