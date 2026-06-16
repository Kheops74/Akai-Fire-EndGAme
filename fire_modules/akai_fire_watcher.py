import ctypes
from pathlib import Path
import sys
import time


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
PIPE_PATH = BASE_DIR / "_sendkey_pipe.txt"

user32 = ctypes.WinDLL("user32", use_last_error=True)

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002

SPECIAL_KEYS = {
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "TAB": 0x09,
    "BS": 0x08,
    "BACKSPACE": 0x08,
    "DEL": 0x2E,
    "DELETE": 0x2E,
    "INS": 0x2D,
    "INSERT": 0x2D,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "HOME": 0x24,
    "END": 0x23,
    "PGUP": 0x21,
    "PGDN": 0x22,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "SPACE": 0x20,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}

MOD_PREFIXES = {
    "^": "ctrl",
    "%": "alt",
    "+": "shift",
}

MOD_VKS = {
    "ctrl": VK_CONTROL,
    "alt": VK_MENU,
    "shift": VK_SHIFT,
}

RAW_MOD_TOKENS = {
    "__VK_CTRL__": ("ctrl", "tap"),
    "__VK_CTRL_DOWN__": ("ctrl", "down"),
    "__VK_CTRL_UP__": ("ctrl", "up"),
    "__VK_SHIFT__": ("shift", "tap"),
    "__VK_SHIFT_DOWN__": ("shift", "down"),
    "__VK_SHIFT_UP__": ("shift", "up"),
    "__VK_ALT__": ("alt", "tap"),
    "__VK_ALT_DOWN__": ("alt", "down"),
    "__VK_ALT_UP__": ("alt", "up"),
}


def key_down(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)


def key_up(vk_code):
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def tap_vk(vk_code):
    key_down(vk_code)
    time.sleep(0.02)
    key_up(vk_code)


def strip_sequence_prefix(raw):
    if raw.startswith("__SEQ__"):
        sep = raw.find("|")
        if sep != -1:
            return raw[sep + 1 :]
    return raw


def parse_shortcut(raw):
    raw = strip_sequence_prefix(raw)

    if raw in RAW_MOD_TOKENS:
        modifier, action = RAW_MOD_TOKENS[raw]
        return None, [], raw, modifier, action

    mods = []
    idx = 0
    while idx < len(raw) and raw[idx] in MOD_PREFIXES:
        mods.append(MOD_PREFIXES[raw[idx]])
        idx += 1

    token = raw[idx:]
    return token, mods, raw, None, None


def resolve_vk(token):
    if not token:
        return None, []

    if token == "~":
        return SPECIAL_KEYS["ENTER"], []

    if token.startswith("{") and token.endswith("}"):
        name = token[1:-1].upper()
        if name in SPECIAL_KEYS:
            return SPECIAL_KEYS[name], []
        return None, []

    if len(token) == 1:
        scan = user32.VkKeyScanW(ord(token))
        if scan == -1:
            return None, []

        vk_code = scan & 0xFF
        shifts = (scan >> 8) & 0xFF
        extra_mods = []
        if shifts & 1:
            extra_mods.append("shift")
        if shifts & 2:
            extra_mods.append("ctrl")
        if shifts & 4:
            extra_mods.append("alt")
        return vk_code, extra_mods

    upper = token.upper()
    if upper in SPECIAL_KEYS:
        return SPECIAL_KEYS[upper], []

    return None, []


def send_shortcut(raw):
    token, mods, cleaned, raw_modifier, raw_action = parse_shortcut(raw)

    if token is None:
        print(f"CUSTOM Envoi: key={cleaned} mod={raw_modifier} action={raw_action}")
        if raw_action == "down":
            key_down(MOD_VKS[raw_modifier])
        elif raw_action == "up":
            key_up(MOD_VKS[raw_modifier])
        else:
            tap_vk(MOD_VKS[raw_modifier])
        print("Envoye.")
        return

    vk_code, extra_mods = resolve_vk(token)
    if vk_code is None:
        print(f"CUSTOM Ignore: unsupported key={cleaned}")
        return

    all_mods = []
    for mod in mods + extra_mods:
        if mod not in all_mods:
            all_mods.append(mod)

    print(f"CUSTOM Envoi: key={cleaned} mod={all_mods}")
    try:
        for mod in all_mods:
            key_down(MOD_VKS[mod])
            time.sleep(0.01)

        tap_vk(vk_code)
    finally:
        for mod in reversed(all_mods):
            key_up(MOD_VKS[mod])
            time.sleep(0.01)

    print("Envoye.")


def main():
    print("=== Akai Fire Key Watcher V2 CUSTOM ===")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"PIPE_PATH: {PIPE_PATH}")
    print(f"Fichier existe: {PIPE_PATH.exists()}")
    print("En attente...")

    last_mtime_ns = None

    while True:
        try:
            if not PIPE_PATH.exists():
                time.sleep(0.05)
                continue

            stat = PIPE_PATH.stat()
            if stat.st_mtime_ns != last_mtime_ns and stat.st_size > 0:
                raw = PIPE_PATH.read_text(encoding="utf-8", errors="ignore").strip()
                last_mtime_ns = stat.st_mtime_ns
                if raw:
                    print(f"Lu: {raw}")
                    send_shortcut(raw)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"Watcher error: {exc}")

        time.sleep(0.02)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
