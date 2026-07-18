import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path


MANIFEST_VERSION = 8
LEGACY_ROOTS = (
    "00_INPUT", "01_TOPICS", "02_SCRIPTS", "03_PRODUCTION", "04_PUBLISHED", "05_PROJECTS",
    "06_KNOWLEDGE", "07_SKILLS", "08_REVIEWS", "09_SYSTEM", "ASSETS", "Templates",
    "01_UNDERSTAND", "02_CONTENT_ENGINE", "03_BUILD", "04_OUTPUT", "05_SYSTEM", "06_FEEDBACK",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, default: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else default
    except (OSError, ValueError):
        return default


def safe_candidate(root: Path, relative: Path, source: Path) -> str:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)


def manifest_files(manifest: dict) -> dict:
    files = manifest.get("files", {})
    return files if isinstance(files, dict) else {}


def remove_empty_legacy_directories(vault: Path) -> list[str]:
    removed = []
    for root_name in LEGACY_ROOTS:
        root = vault / root_name
        if not root.is_dir():
            continue
        directories = sorted((path for path in root.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True)
        for directory in [*directories, root]:
            try:
                directory.rmdir()
                removed.append(directory.relative_to(vault).as_posix())
            except OSError:
                pass
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-path", required=True)
    args = parser.parse_args()
    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"Obsidian 仓库不存在：{vault}")
    if not (vault / ".obsidian").is_dir():
        raise RuntimeError("Obsidian 仓库尚未初始化")
    template = Path(__file__).resolve().parent.parent / "assets" / "vault-template"
    legacy_path = Path(__file__).resolve().parent.parent / "assets" / "legacy-template-hashes.json"
    manifest_path = vault / "06_系统" / ".solo-os-manifest.json"
    old_manifest_path = vault / "09_SYSTEM" / ".solo-os-manifest.json"
    current_manifest = load_json(manifest_path, {})
    old_manifest = load_json(old_manifest_path, {})
    previous_files = manifest_files(old_manifest)
    previous_files.update(manifest_files(current_manifest))
    previous = {**old_manifest, **current_manifest, "files": previous_files}
    legacy = load_json(legacy_path, {})
    candidate_root = vault / "06_系统" / "升级候选" / time.strftime("%Y%m%d-%H%M%S")
    created, updated, skipped, conflicts, removed, preserved_legacy = [], [], [], [], [], []
    managed = {}
    template_keys = {
        source.relative_to(template).as_posix()
        for source in template.rglob("*")
        if source.is_file()
    }

    for source in sorted(template.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(template)
        relative_key = relative.as_posix()
        target = vault / relative
        source_hash = digest(source)
        old_record = previous.get("files", {}).get(relative_key, {})
        old_hash = old_record.get("installedHash") if isinstance(old_record, dict) else None
        legacy_hash = legacy.get(relative_key)

        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            created.append(relative_key)
            managed[relative_key] = {"installedHash": source_hash, "templateVersion": MANIFEST_VERSION}
            continue

        current_hash = digest(target)
        if current_hash == source_hash:
            skipped.append(relative_key)
            managed[relative_key] = {"installedHash": source_hash, "templateVersion": MANIFEST_VERSION}
        elif current_hash in {old_hash, legacy_hash}:
            shutil.copy2(source, target)
            updated.append(relative_key)
            managed[relative_key] = {"installedHash": source_hash, "templateVersion": MANIFEST_VERSION}
        else:
            candidate = safe_candidate(candidate_root, relative, source)
            conflicts.append({"path": relative_key, "candidate": candidate})
            if isinstance(old_record, dict) and old_record.get("installedHash"):
                managed[relative_key] = old_record

    cleanup_records = {
        relative_key: {"installedHash": installed_hash, "source": "legacy-catalog"}
        for relative_key, installed_hash in legacy.items()
        if isinstance(relative_key, str) and isinstance(installed_hash, str)
    }
    cleanup_records.update(previous_files)
    if isinstance(cleanup_records, dict):
        for relative_key, record in cleanup_records.items():
            if relative_key in template_keys or not isinstance(record, dict):
                continue
            parts = Path(relative_key).parts
            if not parts or Path(relative_key).is_absolute() or ".." in parts:
                continue
            target = vault.joinpath(*parts)
            installed_hash = record.get("installedHash")
            if not target.exists():
                continue
            if target.is_file() and installed_hash and digest(target) == installed_hash:
                target.unlink()
                removed.append(relative_key)
                parent = target.parent
                while parent != vault:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            else:
                preserved_legacy.append(relative_key)
                managed[relative_key] = record

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "templateVersion": MANIFEST_VERSION,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": managed,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if old_manifest_path.is_file() and old_manifest_path != manifest_path:
        old_manifest_path.unlink()
        parent = old_manifest_path.parent
        while parent != vault:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    removed_directories = remove_empty_legacy_directories(vault)
    if not conflicts and candidate_root.exists():
        candidate_root.rmdir()

    print(json.dumps({
        "status": "ready" if not conflicts and not preserved_legacy else "ready-with-conflicts",
        "vaultPath": str(vault),
        "templateVersion": MANIFEST_VERSION,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "removedObsoleteManagedFiles": removed,
        "removedObsoleteDirectories": removed_directories,
        "preservedLegacyFiles": preserved_legacy,
        "conflicts": conflicts,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
