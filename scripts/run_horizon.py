import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-path", required=True)
    parser.add_argument("--vault-path")
    parser.add_argument("--uv-path")
    parser.add_argument("--hours", type=int)
    args = parser.parse_args()
    horizon = Path(args.horizon_path).expanduser().resolve()
    vault = Path(args.vault_path).expanduser().resolve() if args.vault_path else horizon.parent
    summaries = horizon / "data" / "summaries"
    destination_root = vault / "00_输入" / "原始资料" / "资讯日报"
    started = datetime.now()
    uv = args.uv_path or shutil.which("uv")
    if not uv:
        candidates = [Path.home() / ".local/bin/uv", Path.home() / ".cargo/bin/uv"]
        if sys.platform == "win32":
            candidates.insert(0, Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/uv.exe")
        uv = next((str(path) for path in candidates if path.is_file()), None)
    if not uv:
        raise FileNotFoundError("Horizon 运行环境不可用")
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1", "TERM": "dumb"})
    environment.pop("GITHUB_TOKEN", None)
    command = [uv, "run", "horizon"]
    if args.hours:
        command.extend(["--hours", str(args.hours)])
    process = subprocess.Popen(command, cwd=horizon, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    assert process.stdout is not None
    output_encoding = sys.stdout.encoding or "utf-8"
    for line in process.stdout:
        print(line.encode(output_encoding, errors="replace").decode(output_encoding), end="", flush=True)
    if process.wait() != 0:
        raise RuntimeError("Horizon 运行失败")
    candidates = sorted(summaries.rglob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    recent = [path for path in candidates if datetime.fromtimestamp(path.stat().st_mtime) >= started - timedelta(seconds=2)]
    if not recent:
        raise RuntimeError("Horizon 没有生成新的 Markdown 日报")
    destination = destination_root / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in recent:
        target = destination / source.name
        shutil.copy2(source, target)
        copied.append(str(target))
    print(json.dumps({"status": "ready", "importedTo": str(destination), "copied": copied}, ensure_ascii=False))


if __name__ == "__main__":
    main()
