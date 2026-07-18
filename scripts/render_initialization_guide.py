import argparse
import json
import subprocess
import sys
from pathlib import Path


PLUGIN_NAMES = {
    "claudian": "Claudian",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-path", required=True)
    args = parser.parse_args()
    detector = Path(__file__).with_name("detect_environment.py")
    run = subprocess.run(
        [sys.executable, str(detector), "--start-path", args.start_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    environment = json.loads(run.stdout)
    obsidian = environment["obsidian"]
    codex = environment["codex"]
    actions = []
    if not obsidian["installed"]:
        actions.append("安装并打开 Obsidian。")
    elif not obsidian["selectedVault"] or not obsidian["selectedVaultInitialized"]:
        actions.append("在 Obsidian 中创建或打开准备使用的仓库。")
    missing_ids = set(obsidian.get("missingPlugins", []))
    missing = [name for plugin_id, name in PLUGIN_NAMES.items() if plugin_id in missing_ids]
    if missing:
        prefix = "打开“设置 -> 第三方插件”，"
        if not obsidian.get("communityPluginsEnabled"):
            prefix += "关闭受限模式，"
        actions.append(prefix + "安装并启用：" + "、".join(missing) + "。")
    cli_path = codex.get("preferredCliPath")
    if not cli_path:
        actions.append("未找到可用的 Codex CLI。请先自行安装 Codex CLI，再重新发送“初始化”。")
    message = "\n".join(f"{index}. {action}" for index, action in enumerate(actions, 1))
    if cli_path:
        cli_line = "可用 Codex CLI 路径：" + cli_path
        message = (message + "\n\n" + cli_line).strip()
    if actions:
        message += "\n\n完成缺少的插件安装后，可以回复“初始化完成”或直接要求搭建知识库。不要把 API Key 发到聊天里。"
    else:
        message = "插件检查通过。\n\n" + cli_line + "\n\n可以开始搭建知识库。"
    print(json.dumps({
        "status": "ready" if not actions else "needs-user-action",
        "connectionState": environment["connectionState"],
        "cliPath": cli_path,
        "actions": actions,
        "userMessage": message,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
