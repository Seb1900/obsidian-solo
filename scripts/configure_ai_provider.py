import argparse
import getpass
import json
import subprocess
import sys
import time
from pathlib import Path


PROVIDERS = (
    {"id": "deepseek", "name": "DeepSeek", "model": "deepseek-chat", "env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com"},
    {"id": "openai", "name": "OpenAI", "model": "gpt-4o-mini", "env": "OPENAI_API_KEY", "base_url": None},
    {"id": "gemini", "name": "Google Gemini", "model": "gemini-2.0-flash", "env": "GOOGLE_API_KEY", "base_url": None},
    {"id": "ali", "name": "通义千问", "model": "qwen-plus", "env": "DASHSCOPE_API_KEY", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "anthropic", "name": "Anthropic Claude", "model": "claude-sonnet-4-20250514", "env": "ANTHROPIC_API_KEY", "base_url": None},
    {"id": "doubao", "name": "豆包", "model": "doubao-pro-32k", "env": "DOUBAO_API_KEY", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"id": "minimax", "name": "MiniMax", "model": "MiniMax-M2.7", "env": "MINIMAX_API_KEY", "base_url": "https://api.minimax.io/v1"},
    {"id": "ollama", "name": "Ollama（本机模型）", "model": "llama3.1", "env": "", "base_url": "http://localhost:11434/v1"},
)
PROVIDER_ENV_NAMES = tuple(provider["env"] for provider in PROVIDERS if provider["env"])
WINDOWS_CONTROL_HANDLER = None


def install_windows_close_handler(status_path: str | None) -> None:
    global WINDOWS_CONTROL_HANDLER
    if sys.platform != "win32" or not status_path:
        return
    import ctypes

    handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    def handle(control_type: int) -> bool:
        if control_type in (2, 5, 6):
            try:
                Path(status_path).write_text(json.dumps({
                    "status": "error", "message": "用户关闭了配置窗口", "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
            return False
        return False

    WINDOWS_CONTROL_HANDLER = handler_type(handle)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(WINDOWS_CONTROL_HANDLER, True)


def validate_key_shape(provider_id: str, value: str) -> None:
    expected_prefixes = {
        "deepseek": ("sk-",),
        "openai": ("sk-",),
        "gemini": ("AIza",),
        "anthropic": ("sk-ant-",),
        "ali": ("sk-",),
    }
    prefixes = expected_prefixes.get(provider_id)
    if prefixes and not value.startswith(prefixes):
        raise ValueError("这个密钥与所选服务商不匹配，请检查服务商和密钥")


def _windows_clipboard() -> str:
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    opened = False
    for _ in range(20):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.025)
    if not opened:
        return ""
    try:
        user32.GetClipboardData.restype = ctypes.c_void_p
        handle = user32.GetClipboardData(13)
        if not handle:
            return ""
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return ""
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _masked_windows(prompt: str) -> str:
    import msvcrt

    print(prompt, end="", flush=True)
    value = []
    while True:
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            print(flush=True)
            return "".join(value)
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\b":
            if value:
                value.pop()
                print("\b \b", end="", flush=True)
            continue
        if char == "\x16":
            pasted = _windows_clipboard().strip()
            if pasted:
                value.extend(pasted)
                print("*" * len(pasted), end="", flush=True)
            continue
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        if ord(char) >= 32:
            value.append(char)
            print("*", end="", flush=True)


def _masked_posix(prompt: str) -> str:
    import termios
    import tty

    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    value = []
    print(prompt, end="", flush=True)
    try:
        tty.setraw(descriptor)
        while True:
            char = sys.stdin.read(1)
            if char in ("\r", "\n"):
                print(flush=True)
                return "".join(value)
            if char == "\x03":
                raise KeyboardInterrupt
            if char in ("\x7f", "\b"):
                if value:
                    value.pop()
                    print("\b \b", end="", flush=True)
                continue
            if ord(char) >= 32:
                value.append(char)
                print("*", end="", flush=True)
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)


def masked_input(prompt: str) -> str:
    if not sys.stdin.isatty():
        return getpass.getpass(prompt)
    return _masked_windows(prompt) if sys.platform == "win32" else _masked_posix(prompt)


def set_env(path: Path, name: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    output, replaced = [], False
    for line in lines:
        variable = line.split("=", 1)[0] if "=" in line else ""
        if variable in PROVIDER_ENV_NAMES:
            if variable != name:
                continue
            if not replaced:
                output.append(f"{name}={value}")
                replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{name}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    if sys.platform != "win32":
        path.chmod(0o600)


def choose_provider(provider_id: str | None) -> dict:
    if provider_id:
        provider = next((item for item in PROVIDERS if item["id"] == provider_id), None)
        if not provider:
            raise ValueError(f"不支持的服务商：{provider_id}")
        return provider
    print("\n请选择 Horizon 使用的 AI 服务商：", flush=True)
    for index, provider in enumerate(PROVIDERS, 1):
        print(f"  {index}. {provider['name']}", flush=True)
    while True:
        value = input("输入序号：").strip()
        if value.isdigit() and 1 <= int(value) <= len(PROVIDERS):
            return PROVIDERS[int(value) - 1]
        print("请输入列表中的有效序号。", flush=True)


def configure() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-path", required=True)
    parser.add_argument("--provider")
    parser.add_argument("--status-path")
    parser.add_argument("--pause-after-success", action="store_true")
    parser.add_argument("--resume-script")
    parser.add_argument("--vault-path")
    args = parser.parse_args()
    install_windows_close_handler(args.status_path)
    root = Path(args.horizon_path).expanduser().resolve()
    config_path = root / "data" / "config.json"
    env_path = root / ".env"
    if not config_path.is_file():
        raise FileNotFoundError(f"找不到 Horizon 配置：{config_path}")

    while True:
        provider = choose_provider(args.provider)
        if not provider["env"]:
            break
        print("可使用 Ctrl+V 或 Command+V 粘贴，星号数量会随输入变化。", flush=True)
        api_key = masked_input(f"请输入 {provider['name']} API 密钥：").strip()
        try:
            if not api_key:
                raise ValueError("API 密钥不能为空")
            validate_key_shape(provider["id"], api_key)
            set_env(env_path, provider["env"], api_key)
            break
        except ValueError as exc:
            print(f"\n{exc}", flush=True)
            if args.provider:
                raise
            action = input("按回车重新输入，输入 B 返回服务商列表：").strip().lower()
            if action == "b":
                continue
            while True:
                api_key = masked_input(f"请重新输入 {provider['name']} API 密钥：").strip()
                try:
                    if not api_key:
                        raise ValueError("API 密钥不能为空")
                    validate_key_shape(provider["id"], api_key)
                    set_env(env_path, provider["env"], api_key)
                    break
                except ValueError as retry_exc:
                    print(f"\n{retry_exc}", flush=True)
            break

    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    config["ai"].update({
        "provider": provider["id"],
        "model": provider["model"],
        "api_key_env": provider["env"],
        "base_url": provider["base_url"],
    })
    temp = config_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(config_path)
    print(f"\n配置完成：{provider['name']} / {provider['model']}", flush=True)
    if args.status_path:
        status_path = Path(args.status_path)
        temporary_status = status_path.with_suffix(status_path.suffix + ".tmp")
        temporary_status.write_text(json.dumps({
            "status": "ready", "provider": provider["id"], "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, ensure_ascii=False), encoding="utf-8")
        temporary_status.replace(status_path)
    if args.resume_script and args.vault_path:
        command = [sys.executable, args.resume_script, "--vault-path", args.vault_path, "--skip-provider-setup", "--background-resume"]
        options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
        if sys.platform == "win32":
            options["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            options["start_new_session"] = True
        subprocess.Popen(command, **options)
        print("Horizon 将在后台继续安装并生成首份报告。", flush=True)
    if args.pause_after_success:
        time.sleep(2)


def main() -> None:
    try:
        configure()
    except KeyboardInterrupt:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--status-path")
        known, _ = parser.parse_known_args()
        if known.status_path:
            Path(known.status_path).write_text(json.dumps({"status": "error", "message": "用户取消"}, ensure_ascii=False), encoding="utf-8")
        print("\n配置已取消。", flush=True)
        raise SystemExit(130)
    except Exception as exc:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--status-path")
        known, _ = parser.parse_known_args()
        if known.status_path:
            Path(known.status_path).write_text(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), encoding="utf-8")
        print(f"\n配置未完成：{exc}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
