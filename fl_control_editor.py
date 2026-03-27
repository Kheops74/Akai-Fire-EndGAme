from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import shutil
import sys
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = BASE_DIR / "fire_modules" / "fl_control_config.py"
BACKUP_DIR = BASE_DIR / "backups" / "fl_control_config"

SWAPPABLE_COUNT = 10
FIXED_KEYS = (
    "row2_11",
    "row2_12",
    "row2_13",
    "row3_11",
    "row3_12",
    "row3_13",
)

SECTION_DEFS = (
    ("Playlist A", "ROW2_SHORTCUTS_A", 1),
    ("Playlist B", "ROW2_SHORTCUTS_B", 1),
    ("Piano Roll A", "ROW3_SHORTCUTS_A", 1),
    ("Piano Roll B", "ROW3_SHORTCUTS_B", 1),
)

FIXED_LABELS = {
    "row2_11": "Row2 Pad11",
    "row2_12": "Row2 Pad12",
    "row2_13": "Row2 Pad13",
    "row3_11": "Row3 Pad11",
    "row3_12": "Row3 Pad12",
    "row3_13": "Row3 Pad13",
}

DEFAULT_DATA = {
    "sections": {
        "ROW2_SHORTCUTS_A": [
            ("p", False, False, False, "Draw", 0xFF6600),
            ("b", False, False, False, "Paint", 0x00CCCC),
            ("d", False, False, False, "Delete", 0xFF0000),
            ("t", False, False, False, "Mute", 0xFF4488),
            ("s", False, False, False, "Slip", 0xFF8800),
            ("c", False, False, False, "Slice", 0x0066FF),
            ("e", False, False, False, "Select", 0xFFFF00),
            ("z", False, False, False, "Zoom", 0xAA00FF),
            ("y", False, False, False, "Playback", 0xFF4488),
            ("", False, False, False, "PL-A10", 0x220022),
        ],
        "ROW2_SHORTCUTS_B": [
            ("", False, False, False, "PL-B1", 0x442200),
            ("", False, False, False, "PL-B2", 0x442200),
            ("", False, False, False, "PL-B3", 0x442200),
            ("", False, False, False, "PL-B4", 0x442200),
            ("", False, False, False, "PL-B5", 0x442200),
            ("", False, False, False, "PL-B6", 0x442200),
            ("", False, False, False, "PL-B7", 0x442200),
            ("", False, False, False, "PL-B8", 0x442200),
            ("", False, False, False, "PL-B9", 0x442200),
            ("", False, False, False, "PL-B10", 0x442200),
        ],
        "ROW3_SHORTCUTS_A": [
            ("p", False, False, False, "Draw", 0xFF6600),
            ("b", False, False, False, "Paint", 0x00CCCC),
            ("d", False, False, False, "Delete", 0xFF0000),
            ("t", False, False, False, "Mute", 0xFF4488),
            ("n", False, False, False, "PaintD", 0xAA00FF),
            ("c", False, False, False, "Slice", 0x0066FF),
            ("e", False, False, False, "Select", 0xFFFF00),
            ("z", False, False, False, "Zoom", 0xAA00FF),
            ("y", False, False, False, "Playback", 0xFF4488),
            ("", False, False, False, "PR-A10", 0x220022),
        ],
        "ROW3_SHORTCUTS_B": [
            ("", False, False, False, "PR-B1", 0x442200),
            ("", False, False, False, "PR-B2", 0x442200),
            ("", False, False, False, "PR-B3", 0x442200),
            ("", False, False, False, "PR-B4", 0x442200),
            ("", False, False, False, "PR-B5", 0x442200),
            ("", False, False, False, "PR-B6", 0x442200),
            ("", False, False, False, "PR-B7", 0x442200),
            ("", False, False, False, "PR-B8", 0x442200),
            ("", False, False, False, "PR-B9", 0x442200),
            ("", False, False, False, "PR-B10", 0x442200),
        ],
    },
    "fixed": {
        "row2_11": ("", False, False, False, "", 0x000000),
        "row2_12": ("", False, False, False, "", 0x000000),
        "row2_13": ("", False, False, False, "", 0x000000),
        "row3_11": ("", False, False, False, "", 0x000000),
        "row3_12": ("", False, False, False, "", 0x000000),
        "row3_13": ("", False, False, False, "", 0x000000),
    },
}


def normalize_shortcut(entry, fallback_label, fallback_color):
    if not isinstance(entry, (list, tuple)):
        return ("", False, False, False, fallback_label, fallback_color)

    key = str(entry[0]) if len(entry) > 0 and entry[0] is not None else ""
    ctrl = bool(entry[1]) if len(entry) > 1 else False
    shift = bool(entry[2]) if len(entry) > 2 else False
    alt = bool(entry[3]) if len(entry) > 3 else False
    label = fallback_label
    if len(entry) > 4 and entry[4] not in (None, ""):
        label = str(entry[4])
    color = fallback_color
    if len(entry) > 5:
        try:
            color = int(entry[5]) & 0xFFFFFF
        except Exception:
            color = fallback_color
    return (key, ctrl, shift, alt, label, color)


def load_config_from_path(config_path):
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    spec = importlib.util.spec_from_file_location("fl_control_config_editor", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load config module.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = {"sections": {}, "fixed": {}}
    for _, attr_name, row_pad_start in SECTION_DEFS:
        entries = getattr(module, attr_name, [])
        normalized = []
        for idx in range(SWAPPABLE_COUNT):
            fallback_label = f"{attr_name[-1]}{idx + row_pad_start}"
            fallback_color = 0x220022 if attr_name.endswith("_A") else 0x442200
            entry = entries[idx] if idx < len(entries) else None
            normalized.append(normalize_shortcut(entry, fallback_label, fallback_color))
        data["sections"][attr_name] = normalized

    fixed_entries = getattr(module, "FIXED_SENDKEYS", {})
    for key in FIXED_KEYS:
        data["fixed"][key] = normalize_shortcut(fixed_entries.get(key), "", 0x000000)

    return data


def load_config():
    return load_config_from_path(CONFIG_PATH)


def clone_data(data):
    return {
        "sections": {
            attr_name: [tuple(entry) for entry in entries]
            for attr_name, entries in data["sections"].items()
        },
        "fixed": {
            key: tuple(entry)
            for key, entry in data["fixed"].items()
        },
    }


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def list_backup_files():
    ensure_backup_dir()
    return sorted(BACKUP_DIR.glob("fl_control_config_*.py"), reverse=True)


def create_backup():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    ensure_backup_dir()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / f"fl_control_config_{stamp}.py"
    shutil.copy2(CONFIG_PATH, backup_path)
    return backup_path


def validate_shortcut_entry(entry_name, entry):
    key, ctrl, shift, alt, _, _ = entry
    modifier_count = int(ctrl) + int(shift) + int(alt)

    if key == "":
        if modifier_count <= 1:
            return None
        return (
            f"{entry_name}: combinaison invalide.\n"
            "Sans touche, un seul modificateur est autorise: Ctrl seul, Shift seul ou Alt seul."
        )

    return None


def format_shortcut(entry):
    key, ctrl, shift, alt, label, color = entry
    return (
        f"    ({key!r}, {ctrl}, {shift}, {alt}, {label!r}, 0x{color:06X}),"
    )


def build_config_text(data):
    lines = [
        "#   name=AKAI FL Studio Fire - FL Control Config",
        "#   Central file for FL Control shortcuts",
        "",
        "SWAPPABLE_PAD_COUNT = 10",
        "FIXED_SENDKEY_PAD_NUMBERS = (11, 12, 13)",
        "",
        "# Format:",
        "# (key, ctrl, shift, alt, label, color)",
        "",
        "# ==========================================",
        "# PLAYLIST - ROW 2 - PAGE A (pads 1-10)",
        "# ==========================================",
        "ROW2_SHORTCUTS_A = [",
    ]
    lines.extend(format_shortcut(entry) for entry in data["sections"]["ROW2_SHORTCUTS_A"])
    lines.extend([
        "]",
        "",
        "# ==========================================",
        "# PLAYLIST - ROW 2 - PAGE B (pads 1-10)",
        "# ==========================================",
        "ROW2_SHORTCUTS_B = [",
    ])
    lines.extend(format_shortcut(entry) for entry in data["sections"]["ROW2_SHORTCUTS_B"])
    lines.extend([
        "]",
        "",
        "# ==========================================",
        "# PIANO ROLL - ROW 3 - PAGE A (pads 1-10)",
        "# ==========================================",
        "ROW3_SHORTCUTS_A = [",
    ])
    lines.extend(format_shortcut(entry) for entry in data["sections"]["ROW3_SHORTCUTS_A"])
    lines.extend([
        "]",
        "",
        "# ==========================================",
        "# PIANO ROLL - ROW 3 - PAGE B (pads 1-10)",
        "# ==========================================",
        "ROW3_SHORTCUTS_B = [",
    ])
    lines.extend(format_shortcut(entry) for entry in data["sections"]["ROW3_SHORTCUTS_B"])
    lines.extend([
        "]",
        "",
        "# ==========================================",
        "# FIXED SENDKEYS - ROW 2 / ROW 3 (pads 11-13)",
        "# ==========================================",
        "FIXED_SENDKEYS = {",
    ])
    for key in FIXED_KEYS:
        entry = data["fixed"][key]
        value = f"({entry[0]!r}, {entry[1]}, {entry[2]}, {entry[3]}, {entry[4]!r}, 0x{entry[5]:06X})"
        lines.append(f"    {key!r}: {value},")
    lines.extend([
        "}",
        "",
        "# Pads API fixes, gardes dans le code principal:",
        "# Row 2: pad 14 = Escape, pad 15 = Up, pad 16 = Enter",
        "# Row 3: pad 14 = Left,   pad 15 = Down, pad 16 = Right",
        "",
    ])
    return "\n".join(lines)


class ShortcutRow:
    def __init__(self, parent, title, entry):
        self.title = title
        self.key_var = tk.StringVar(value=entry[0])
        self.ctrl_var = tk.BooleanVar(value=entry[1])
        self.shift_var = tk.BooleanVar(value=entry[2])
        self.alt_var = tk.BooleanVar(value=entry[3])
        self.label_var = tk.StringVar(value=entry[4])
        self.color_var = tk.StringVar(value=f"{entry[5]:06X}")

        self.frame = ttk.Frame(parent, padding=(6, 4))
        self.frame.columnconfigure(5, weight=1)

        ttk.Label(self.frame, text=title, width=12).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.frame, textvariable=self.key_var, width=12).grid(row=0, column=1, padx=4, sticky="w")
        ttk.Checkbutton(self.frame, text="Ctrl", variable=self.ctrl_var).grid(row=0, column=2, padx=2)
        ttk.Checkbutton(self.frame, text="Shift", variable=self.shift_var).grid(row=0, column=3, padx=2)
        ttk.Checkbutton(self.frame, text="Alt", variable=self.alt_var).grid(row=0, column=4, padx=2)
        ttk.Entry(self.frame, textvariable=self.label_var, width=20).grid(row=0, column=5, padx=4, sticky="ew")

        color_box = ttk.Frame(self.frame)
        color_box.grid(row=0, column=6, padx=4, sticky="e")
        self.color_entry = ttk.Entry(color_box, textvariable=self.color_var, width=8)
        self.color_entry.grid(row=0, column=0, padx=(0, 4))
        ttk.Button(color_box, text="Color", command=self.choose_color).grid(row=0, column=1)

    def choose_color(self):
        current = "#" + self.color_var.get().strip().lstrip("#").upper().zfill(6)[:6]
        _, color = colorchooser.askcolor(color=current, title=self.title)
        if color:
            self.color_var.set(color.lstrip("#").upper())

    def grid(self, row):
        self.frame.grid(row=row, column=0, sticky="ew")

    def get_value(self):
        raw_color = self.color_var.get().strip().lstrip("#")
        if raw_color == "":
            raw_color = "000000"
        if len(raw_color) > 6:
            raise ValueError(f"{self.title}: color too long")
        try:
            color = int(raw_color, 16) & 0xFFFFFF
        except ValueError as exc:
            raise ValueError(f"{self.title}: invalid color") from exc

        return (
            self.key_var.get().strip(),
            self.ctrl_var.get(),
            self.shift_var.get(),
            self.alt_var.get(),
            self.label_var.get().strip(),
            color,
        )


class EditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FL Control Config Editor")
        self.root.geometry("980x720")
        self.root.minsize(920, 620)

        self.status_var = tk.StringVar(value=f"Config: {CONFIG_PATH}")
        self.backup_var = tk.StringVar()
        self.rows = {"sections": {}, "fixed": {}}

        self.build_ui()
        self.load_into_form()
        self.refresh_backup_list()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(
            header,
            text="Edit keys, modifiers, labels and pad colors for FL Control.",
        ).pack(side="left")

        backup_bar = ttk.Frame(main)
        backup_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(backup_bar, text="Backups:").pack(side="left")
        self.backup_combo = ttk.Combobox(
            backup_bar,
            textvariable=self.backup_var,
            state="readonly",
            width=42,
        )
        self.backup_combo.pack(side="left", padx=(6, 8))
        ttk.Button(backup_bar, text="Refresh", command=self.refresh_backup_list).pack(side="left")
        ttk.Button(backup_bar, text="Load Backup", command=self.load_selected_backup).pack(side="left", padx=(8, 0))
        ttk.Button(backup_bar, text="Restore Backup", command=self.restore_selected_backup).pack(side="left", padx=(8, 0))

        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True)

        for title, attr_name, pad_start in SECTION_DEFS:
            frame = ttk.Frame(notebook, padding=10)
            frame.columnconfigure(0, weight=1)
            notebook.add(frame, text=title)
            rows = []
            for idx in range(SWAPPABLE_COUNT):
                row = ShortcutRow(frame, f"Pad {idx + pad_start}", ("", False, False, False, "", 0))
                row.grid(idx)
                rows.append(row)
            self.rows["sections"][attr_name] = rows

        fixed_frame = ttk.Frame(notebook, padding=10)
        fixed_frame.columnconfigure(0, weight=1)
        notebook.add(fixed_frame, text="Fixed 11-13")
        for idx, key in enumerate(FIXED_KEYS):
            row = ShortcutRow(fixed_frame, FIXED_LABELS[key], ("", False, False, False, "", 0))
            row.grid(idx)
            self.rows["fixed"][key] = row

        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Reload", command=self.load_into_form).pack(side="left")
        ttk.Button(actions, text="Reset Defaults", command=self.reset_defaults).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Create Backup", command=self.create_manual_backup).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Save", command=self.save).pack(side="right")

    def _apply_data_to_form(self, data):
        for attr_name, rows in self.rows["sections"].items():
            values = data["sections"][attr_name]
            for row, value in zip(rows, values):
                row.key_var.set(value[0])
                row.ctrl_var.set(value[1])
                row.shift_var.set(value[2])
                row.alt_var.set(value[3])
                row.label_var.set(value[4])
                row.color_var.set(f"{value[5]:06X}")

        for key, row in self.rows["fixed"].items():
            value = data["fixed"][key]
            row.key_var.set(value[0])
            row.ctrl_var.set(value[1])
            row.shift_var.set(value[2])
            row.alt_var.set(value[3])
            row.label_var.set(value[4])
            row.color_var.set(f"{value[5]:06X}")

    def load_into_form(self):
        try:
            data = load_config()
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            return

        self._apply_data_to_form(data)

        self.status_var.set(f"Loaded: {CONFIG_PATH}")
        self.refresh_backup_list()

    def collect_form_data(self):
        data = {"sections": {}, "fixed": {}}
        for attr_name, rows in self.rows["sections"].items():
            data["sections"][attr_name] = [row.get_value() for row in rows]
        for key, row in self.rows["fixed"].items():
            data["fixed"][key] = row.get_value()
        return data

    def validate_form_data(self, data):
        errors = []

        for title, attr_name, pad_start in SECTION_DEFS:
            entries = data["sections"][attr_name]
            for idx, entry in enumerate(entries):
                entry_name = f"{title} - Pad {idx + pad_start}"
                error = validate_shortcut_entry(entry_name, entry)
                if error:
                    errors.append(error)

        for key in FIXED_KEYS:
            entry_name = FIXED_LABELS[key]
            error = validate_shortcut_entry(entry_name, data["fixed"][key])
            if error:
                errors.append(error)

        return errors

    def refresh_backup_list(self):
        backups = list_backup_files()
        names = [path.name for path in backups]
        self.backup_combo["values"] = names
        if names:
            if self.backup_var.get() not in names:
                self.backup_var.set(names[0])
        else:
            self.backup_var.set("")

    def _get_selected_backup_path(self):
        name = self.backup_var.get().strip()
        if not name:
            raise ValueError("No backup selected.")
        path = BACKUP_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Backup not found: {path}")
        return path

    def create_manual_backup(self):
        try:
            backup_path = create_backup()
        except Exception as exc:
            messagebox.showerror("Backup error", str(exc))
            return

        self.refresh_backup_list()
        self.backup_var.set(backup_path.name)
        self.status_var.set(f"Backup created: {backup_path.name}")
        messagebox.showinfo("Backup created", backup_path.name)

    def load_selected_backup(self):
        try:
            backup_path = self._get_selected_backup_path()
            data = load_config_from_path(backup_path)
        except Exception as exc:
            messagebox.showerror("Backup load error", str(exc))
            return

        self._apply_data_to_form(data)
        self.status_var.set(f"Loaded backup in editor: {backup_path.name}")

    def restore_selected_backup(self):
        try:
            backup_path = self._get_selected_backup_path()
            data = load_config_from_path(backup_path)
        except Exception as exc:
            messagebox.showerror("Backup restore error", str(exc))
            return

        if not messagebox.askyesno(
            "Restore backup",
            f"Replace current config with:\n{backup_path.name}\n\nA new backup of the current config will be created first.",
        ):
            return

        try:
            current_backup = create_backup()
            CONFIG_PATH.write_text(build_config_text(data), encoding="utf-8", newline="\n")
        except Exception as exc:
            messagebox.showerror("Restore error", str(exc))
            return

        self._apply_data_to_form(data)
        self.refresh_backup_list()
        self.status_var.set(f"Restored backup: {backup_path.name}")
        messagebox.showinfo(
            "Backup restored",
            f"Backup restored.\nCurrent config saved first as:\n{current_backup.name}",
        )

    def reset_defaults(self):
        if not messagebox.askyesno(
            "Reset defaults",
            "Load default values in the editor? Unsaved changes will be lost.",
        ):
            return

        self._apply_data_to_form(clone_data(DEFAULT_DATA))
        self.status_var.set("Defaults loaded in editor")

    def save(self):
        try:
            data = self.collect_form_data()
            errors = self.validate_form_data(data)
            if errors:
                raise ValueError("\n\n".join(errors[:8]))
            backup_path = create_backup()
            CONFIG_PATH.write_text(build_config_text(data), encoding="utf-8", newline="\n")
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))
            return

        self.refresh_backup_list()
        self.status_var.set(f"Saved: {CONFIG_PATH}")
        messagebox.showinfo("Saved", f"fl_control_config.py updated.\nBackup: {backup_path.name}")


def main():
    root = tk.Tk()
    ttk.Style(root).theme_use("vista")
    EditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
