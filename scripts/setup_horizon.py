import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


REPOSITORY_URL = "https://github.com/Thysrael/Horizon.git"
ARCHIVE_URL = "https://github.com/Thysrael/Horizon/archive/refs/heads/main.zip"
EXPECTED_REMOTES = {REPOSITORY_URL.lower(), "git@github.com:thysrael/horizon.git"}
LEGACY_GENERATED_FILES = (
    "configure_horizon.py", "capture_x_session.py", "capture-x-session.ps1", "run_horizon.py", "run-horizon.ps1",
)
LEGACY_DATA_FILES = ("x_cookies_local.json", "x-login.log", "setup-server.json", "setup-server.log")
OBSOLETE_ROLE_KEYWORD = "\u0063\u0072\u0065\u0061\u0074\u006f\u0072"


def read_json(path: Path, default: dict | None = None) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else (default or {})
    except (OSError, ValueError):
        return default or {}


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def key_ready(config: dict, env_path: Path) -> bool:
    env_name = config.get("ai", {}).get("api_key_env", "")
    if not env_name:
        return True
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith(env_name + "="):
            value = line.split("=", 1)[1].strip()
            lowered = value.lower()
            placeholders = ("your_", "your-", "your key", "your-key", "api_key_here", "replace", "changeme", "xxx")
            if not value or any(marker in lowered for marker in placeholders):
                return False
            prefixes = {
                "deepseek": ("sk-",), "openai": ("sk-",), "gemini": ("AIza",),
                "anthropic": ("sk-ant-",), "ali": ("sk-",),
            }.get(config.get("ai", {}).get("provider", ""))
            return not prefixes or value.startswith(prefixes)
    return False


def find_uv() -> str | None:
    command = shutil.which("uv")
    if command:
        return command
    candidates = [Path.home() / ".local/bin/uv", Path.home() / ".cargo/bin/uv"]
    if sys.platform == "win32":
        candidates.insert(0, Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/uv.exe")
    elif sys.platform == "darwin":
        candidates.extend([Path("/opt/homebrew/bin/uv"), Path("/usr/local/bin/uv")])
    return next((str(path) for path in candidates if path.is_file()), None)


def ensure_uv() -> str | None:
    existing = find_uv()
    if existing:
        return existing
    if sys.platform == "win32":
        winget = shutil.which("winget")
        if not winget:
            return None
        result = subprocess.run([winget, "install", "--id=astral-sh.uv", "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"])
        return find_uv() if result.returncode == 0 else None
    brew = shutil.which("brew")
    if sys.platform == "darwin" and brew:
        result = subprocess.run([brew, "install", "uv"])
        return find_uv() if result.returncode == 0 else None
    try:
        with tempfile.TemporaryDirectory(prefix="uv-installer-") as temporary_name:
            installer = Path(temporary_name) / "install.sh"
            urllib.request.urlretrieve("https://astral.sh/uv/install.sh", installer)
            result = subprocess.run(["/bin/sh", str(installer), "--no-modify-path"])
        return find_uv() if result.returncode == 0 else None
    except OSError:
        return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def update_stage(state_path: Path, stage: str, **details) -> dict:
    state = read_json(state_path)
    state.update({"stage": stage, "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **details})
    write_json(state_path, state)
    return state


def launch_provider_window(provider_script: Path, setup_script: Path, vault: Path, horizon: Path) -> bool:
    status_path = horizon / "data" / "provider-setup-status.json"
    arguments = [
        str(provider_script), "--horizon-path", str(horizon), "--status-path", str(status_path),
        "--resume-script", str(setup_script), "--vault-path", str(vault),
    ]
    if sys.platform == "win32":
        command = "$Host.UI.RawUI.WindowTitle = 'Horizon AI 服务配置'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Clear-Host; "
        command += "& " + " ".join(ps_quote(item) for item in [sys.executable, *arguments])
        command += "; if ($LASTEXITCODE -ne 0) { Read-Host '配置未完成，按回车关闭窗口' }"
        subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
    elif sys.platform == "darwin":
        shell_command = "printf '\\033]0;Horizon AI 服务配置\\007'; clear; " + " ".join(shlex.quote(item) for item in [sys.executable, *arguments])
        error_json = json.dumps({"status": "error", "message": "配置窗口已关闭"}, ensure_ascii=False)
        trap = f"trap 'test -f {shlex.quote(str(status_path))} || printf %s {shlex.quote(error_json)} > {shlex.quote(str(status_path))}' EXIT HUP INT TERM; "
        subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script {json.dumps(trap + shell_command, ensure_ascii=False)}'], check=True)
    else:
        terminal = next((shutil.which(name) for name in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm") if shutil.which(name)), None)
        if not terminal:
            return False
        shell_command = " ".join(shlex.quote(item) for item in [sys.executable, *arguments])
        subprocess.Popen([terminal, "-e", "/bin/sh", "-lc", shell_command])
    return True


def install_horizon(target: Path) -> str:
    git = shutil.which("git")
    if git:
        subprocess.run([git, "clone", "--depth", "1", REPOSITORY_URL, str(target)], check=True)
        return "git-clone"
    with tempfile.TemporaryDirectory(prefix="obsidian-solo-os-") as temporary_name:
        temporary = Path(temporary_name)
        archive = temporary / "horizon.zip"
        urllib.request.urlretrieve(ARCHIVE_URL, archive)
        extract = temporary / "extract"
        with zipfile.ZipFile(archive) as package:
            extract_root = extract.resolve()
            for member in package.infolist():
                destination = (extract / member.filename).resolve()
                if destination != extract_root and extract_root not in destination.parents:
                    raise RuntimeError("Horizon 压缩包包含无效路径")
            package.extractall(extract)
        roots = [item for item in extract.iterdir() if item.is_dir()]
        if len(roots) != 1:
            raise RuntimeError("下载的 Horizon 压缩包结构无效")
        shutil.copytree(roots[0], target)
    return "github-archive"


def verify_and_update_horizon(horizon: Path) -> dict:
    pyproject = horizon / "pyproject.toml"
    readme = horizon / "README.md"
    if not pyproject.is_file() or not readme.is_file() or "Horizon" not in readme.read_text(encoding="utf-8-sig", errors="ignore")[:5000]:
        raise RuntimeError("现有目录不是可识别的 Horizon 项目")
    result = {"source": "verified-archive", "commit": None, "updated": False}
    git = shutil.which("git")
    if not git or not (horizon / ".git").is_dir():
        return result
    remote = subprocess.run([git, "-C", str(horizon), "remote", "get-url", "origin"], capture_output=True, text=True, errors="replace")
    remote_url = remote.stdout.strip().lower()
    if remote.returncode or remote_url not in EXPECTED_REMOTES:
        raise RuntimeError("现有 Horizon 的 GitHub 来源不匹配")
    status = subprocess.run([git, "-C", str(horizon), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, errors="replace")
    if status.returncode == 0 and not status.stdout.strip():
        fetched = subprocess.run([git, "-C", str(horizon), "fetch", "--depth", "1", "origin", "main"])
        merged = subprocess.run([git, "-C", str(horizon), "merge", "--ff-only", "origin/main"]) if fetched.returncode == 0 else fetched
        result["updated"] = merged.returncode == 0
    commit = subprocess.run([git, "-C", str(horizon), "rev-parse", "HEAD"], capture_output=True, text=True, errors="replace")
    result.update({"source": "verified-git", "commit": commit.stdout.strip() if commit.returncode == 0 else None})
    return result


def clean_legacy_runtime(horizon: Path, env_path: Path) -> list[str]:
    cleaned = []
    for name in LEGACY_GENERATED_FILES:
        path = horizon / name
        if path.is_file():
            content = path.read_text(encoding="utf-8-sig", errors="ignore")
            definite_x_helper = name.startswith(("capture_x_", "capture-x-"))
            generated_marker = any(marker in content for marker in ("obsidian-solo-os", "HORIZON_X_BROWSER_EXECUTABLE", "x-browser-profile", "provider-setup-status"))
            if definite_x_helper or generated_marker:
                path.unlink()
                cleaned.append(name)
    data = horizon / "data"
    for name in LEGACY_DATA_FILES:
        path = data / name
        if path.is_file():
            path.unlink()
            cleaned.append(f"data/{name}")
    for profile in data.glob("x-browser-profile-*"):
        if profile.is_dir():
            shutil.rmtree(profile)
            cleaned.append(f"data/{profile.name}")
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8-sig").splitlines()
        filtered = [line for line in lines if not line.startswith(("HORIZON_X_BROWSER_EXECUTABLE=", "APIFY_TOKEN=", "GITHUB_TOKEN="))]
        if filtered != lines:
            env_path.write_text("\n".join(filtered).rstrip() + "\n", encoding="utf-8")
            cleaned.append("legacy-auth-settings")
    return cleaned


def enable_public_sources(config: dict, defaults: dict) -> None:
    sources = config.setdefault("sources", {})
    default_sources = defaults["sources"]
    sources.pop("twitter", None)
    for name in ("hackernews", "reddit", "telegram", "ossinsight", "gdelt", "google_news"):
        source = sources.setdefault(name, default_sources[name])
        source["enabled"] = True
    for name in ("github", "rss"):
        entries = sources.get(name) or default_sources[name]
        for entry in entries:
            entry["enabled"] = True
        sources[name] = entries
    config.get("filtering", {}).get("category_groups", {}).pop("voices", None)


def migrate_generic_profile(config: dict, defaults: dict) -> None:
    ossinsight = config.setdefault("sources", {}).setdefault("ossinsight", defaults["sources"]["ossinsight"])
    keywords = [item for item in ossinsight.get("keywords", []) if str(item).casefold() != OBSOLETE_ROLE_KEYWORD]
    for item in defaults["sources"]["ossinsight"]["keywords"]:
        if item not in keywords:
            keywords.append(item)
    ossinsight["keywords"] = keywords


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-path", required=True)
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument("--skip-provider-setup", action="store_true")
    parser.add_argument("--skip-first-report", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--background-resume", action="store_true")
    parser.add_argument("--reopen-provider", action="store_true")
    args = parser.parse_args()
    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"Obsidian 仓库不存在：{vault}")
    if not (vault / ".obsidian").is_dir():
        raise RuntimeError("Obsidian 仓库尚未初始化")
    skill_root = Path(__file__).resolve().parent.parent
    config_template = skill_root / "assets" / "horizon-profile" / "config.general.json"
    provider_script = skill_root / "scripts" / "configure_ai_provider.py"
    runner_script = skill_root / "scripts" / "run_horizon.py"
    setup_script = Path(__file__).resolve()
    horizon = vault / ".horizon-system"
    if args.plan_only:
        print(json.dumps({"status": "planned", "vaultPath": str(vault), "horizonPath": str(horizon)}, ensure_ascii=False))
        return

    created, missing, cleaned = [], [], []
    install_method = "existing"
    if not horizon.exists():
        install_method = install_horizon(horizon)
        created.append("horizon-runtime")
    source = verify_and_update_horizon(horizon)
    data = horizon / "data"
    data.mkdir(parents=True, exist_ok=True)
    setup_state_path = data / "solo-os-setup-state.json"
    provider_status_path = data / "provider-setup-status.json"
    existing_stage = read_json(setup_state_path).get("stage")
    if not args.background_resume and existing_stage in {"dependencies-running", "first-report-running"}:
        print(json.dumps({
            "status": "in-progress", "stage": existing_stage, "vaultPath": str(vault), "horizonPath": str(horizon),
        }, ensure_ascii=False, indent=2))
        return
    update_stage(setup_state_path, "runtime-installed", vaultPath=str(vault), horizonPath=str(horizon), error=None)
    config_path = data / "config.json"
    env_path = horizon / ".env"
    if not config_path.exists():
        shutil.copy2(config_template, config_path)
        created.append("horizon-config")
    if not env_path.exists():
        example = horizon / ".env.example"
        shutil.copy2(example, env_path) if example.exists() else env_path.touch()
        created.append("horizon-env")
    if sys.platform != "win32":
        env_path.chmod(0o600)

    cleaned.extend(clean_legacy_runtime(horizon, env_path))
    config = read_json(config_path)
    defaults = read_json(config_template)
    enable_public_sources(config, defaults)
    migrate_generic_profile(config, defaults)
    write_json(config_path, config)
    if not key_ready(config, env_path):
        provider_status = read_json(provider_status_path)
        if provider_status.get("status") == "error" and not args.reopen_provider:
            update_stage(setup_state_path, "error", error=provider_status.get("message", "服务商配置未完成"), recoverable=True)
            print(json.dumps({"status": "needs-input", "stage": "error", "missing": ["ai-provider"], "recoverable": True}, ensure_ascii=False, indent=2))
            return
        if args.skip_provider_setup:
            missing.append("ai-provider")
        else:
            state = read_json(setup_state_path)
            launches = int(state.get("providerWindowLaunches", 0))
            if args.reopen_provider and launches >= 2:
                update_stage(setup_state_path, "error", error="服务商配置窗口已重开一次", recoverable=False)
                print(json.dumps({"status": "needs-input", "stage": "error", "missing": ["ai-provider"], "recoverable": False}, ensure_ascii=False, indent=2))
                return
            provider_status_path.unlink(missing_ok=True)
            if launch_provider_window(provider_script, setup_script, vault, horizon):
                update_stage(setup_state_path, "provider-window-open", providerWindowLaunches=launches + 1, error=None)
                print(json.dumps({
                    "status": "awaiting-provider", "stage": "provider-window-open", "vaultPath": str(vault),
                    "horizonPath": str(horizon), "message": "请在 Horizon AI 服务配置窗口完成服务商和 API Key 输入。",
                }, ensure_ascii=False, indent=2))
                return
            missing.append("ai-provider")
        config = read_json(config_path)
    else:
        if read_json(provider_status_path).get("status") != "ready":
            write_json(provider_status_path, {"status": "ready", "recovered": True, "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        update_stage(setup_state_path, "provider-ready", error=None)

    dependency_status = "skipped"
    uv = find_uv()
    if not args.skip_dependencies and not uv:
        uv = ensure_uv()
    if args.skip_dependencies:
        dependency_status = "skipped"
    elif not uv:
        missing.append("runtime")
        dependency_status = "missing"
        update_stage(setup_state_path, "error", error="Horizon 运行环境安装失败", recoverable=True)
    else:
        update_stage(setup_state_path, "dependencies-running")
        synced = subprocess.run([uv, "sync"], cwd=horizon)
        dependency_status = "ready" if synced.returncode == 0 else "failed"
        if synced.returncode:
            missing.append("dependencies")
            update_stage(setup_state_path, "error", error="Horizon 依赖安装失败", recoverable=True)
        else:
            update_stage(setup_state_path, "dependencies-ready", error=None)

    state_path = data / "solo-os-state.json"
    state = read_json(state_path)
    imported_reports = [path for path in (vault / "00_输入" / "原始资料" / "资讯日报").rglob("*.md") if path.name.lower() != "readme.md"]
    report_ready = bool(state.get("firstReportAt")) or bool(imported_reports)
    first_report_status = "existing" if report_ready else "skipped"
    if not missing and not report_ready and not args.skip_first_report:
        update_stage(setup_state_path, "first-report-running")
        run = subprocess.run([sys.executable, str(runner_script), "--horizon-path", str(horizon), "--vault-path", str(vault), "--uv-path", str(uv)])
        if run.returncode:
            missing.append("first-report")
            first_report_status = "failed"
            update_stage(setup_state_path, "error", error="首份报告生成失败", recoverable=True)
        else:
            state["firstReportAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            write_json(state_path, state)
            first_report_status = "ready"
            update_stage(setup_state_path, "first-report-ready", error=None)

    final_stage = "complete" if not missing else read_json(setup_state_path).get("stage", "error")
    if not missing:
        update_stage(setup_state_path, "complete", error=None)

    print(json.dumps({
        "status": "ready" if not missing else "needs-input",
        "stage": final_stage,
        "platform": sys.platform,
        "vaultPath": str(vault),
        "horizonPath": str(horizon),
        "source": source,
        "installMethod": install_method,
        "githubAuth": "anonymous-60-per-hour",
        "dependencyStatus": dependency_status,
        "firstReportStatus": first_report_status,
        "missing": missing,
        "created": created,
        "cleaned": cleaned,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
