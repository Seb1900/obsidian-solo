import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-path", required=True)
    args = parser.parse_args()
    data = Path(args.vault_path).expanduser().resolve() / ".horizon-system" / "data"
    state = read_json(data / "solo-os-setup-state.json")
    provider = read_json(data / "provider-setup-status.json")
    stage = state.get("stage", "not-started")
    if stage == "provider-window-open" and provider.get("status") == "ready":
        stage = "provider-ready"
    print(json.dumps({
        "status": "ready" if stage == "complete" else ("error" if stage == "error" else "in-progress"),
        "stage": stage,
        "updatedAt": state.get("updatedAt"),
        "recoverable": state.get("recoverable"),
        "error": state.get("error") if stage == "error" else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
