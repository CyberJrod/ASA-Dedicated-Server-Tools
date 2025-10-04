#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ark: Survival Ascended INI Editor (Final Precision + Save Fix)
- Auto-loads Game.ini and GameUserSettings.ini from the script folder
- Spinboxes for numeric values (no sliders)
- Tooltips for stat multipliers (per-level + base stat)
- Preserves integer vs decimal formatting as typed
- FIX: Save buttons now correctly handle booleans and numbers
"""

import re
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ---------- Theme ----------
def init_tk_theme(root):
    style = ttk.Style()
    for theme in ("vista", "xpnative", "clam", "default"):
        try:
            style.theme_use(theme)
            break
        except Exception:
            continue
    return style

# ---------- Tooltip ----------
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, _e=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 30
        y = self.widget.winfo_rooty() + 20
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self.text, justify="left", background="#ffffe0",
            relief="solid", borderwidth=1, font=("Segoe UI", 9), wraplength=400
        ).pack(ipadx=1)

    def hide_tip(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

# ---------- Descriptions ----------
stat_descriptions = {
    0: "Health: Determines total damage a player or creature can take before death or knockout.",
    1: "Stamina: Duration a player/creature can sprint, jump, or perform actions before tiring.",
    2: "Torpidity: Resistance to becoming unconscious. Higher = harder to knock out.",
    3: "Oxygen: How long a player/creature can stay underwater (affects swim speed).",
    4: "Food: Represents hunger. Decreases over time and must be replenished.",
    5: "Water: Represents thirst. Decreases over time; staying hydrated prevents stamina loss.",
    6: "Temperature/Fortitude: Resistance to environmental temperature extremes.",
    7: "Weight: Determines how much weight can be carried.",
    8: "Melee Damage: Multiplies melee attack power.",
    9: "Movement Speed: Increases running/walking speed.",
}

stat_groups = {
    "PerLevelStatsMultiplier_Player": "Player stat multiplier per level.",
    "PerLevelStatsMultiplier_DinoWild": "Wild dino stat multiplier per level.",
    "PerLevelStatsMultiplier_DinoTamed": "Tamed dino stat multiplier per level.",
    "PerLevelStatsMultiplier_DinoTamed_Add": "Additional tamed dino multiplier (bonus per level).",
    "PerLevelStatsMultiplier_DinoTamed_Affinity": "Tamed dino multiplier from taming affinity.",
    "PlayerBaseStatMultipliers": "Player base stat multiplier (affects starting/base stat values).",
    "DinoBaseStatMultipliers": "Dino base stat multiplier (affects base stat values of wild/tamed dinos).",
}

descriptions = {
    "TamingSpeedMultiplier": "Higher = faster taming.",
    "XPMultiplier": "Higher = gain XP faster.",
    "HarvestAmountMultiplier": "Higher = gather more per hit.",
    "DifficultyOffset": "Higher = stronger wild dinos.",
    "MatingSpeedMultiplier": "Higher = faster mating.",
    "EggHatchSpeedMultiplier": "Higher = faster hatching.",
    "BabyMatureSpeedMultiplier": "Higher = babies grow faster.",
    "FuelConsumptionIntervalMultiplier": "Higher = slower fuel usage.",
    "bAllowCaveBuildingPvE": "Allow building in caves on PvE.",
    "ServerCrosshair": "Enable crosshair for aiming.",
    "ShowFloatingDamageText": "Show floating damage numbers.",
    "MapName": "Which map is loaded (e.g., TheIsland_WP).",
}

# ---------- Parsing ----------
SECTION_HEADER_PATTERN = re.compile(r"^\s*\[(.*?)\]\s*$")
KEY_VALUE_PATTERN = re.compile(r"^\s*([^=;#\s]+)\s*=\s*(.*?)\s*$")
TRUE_VALUES = {"true", "True", "TRUE"}
FALSE_VALUES = {"false", "False", "FALSE"}

def infer_type(value: str):
    v = value.strip()
    if v in TRUE_VALUES or v in FALSE_VALUES:
        return "bool"
    if re.fullmatch(r"-?\d+", v):
        return "int"
    if re.fullmatch(r"-?\d+\.\d+", v):
        return "float"
    return "str"

def load_ini(path: Path):
    data = {}
    if not path.exists():
        return data
    current_section = None
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        m_sec = SECTION_HEADER_PATTERN.match(line)
        if m_sec:
            current_section = m_sec.group(1)
            data.setdefault(current_section, {})
            continue
        m_kv = KEY_VALUE_PATTERN.match(line)
        if m_kv:
            key, val = m_kv.groups()
            data.setdefault(current_section or "ROOT", {})[key.strip()] = val.strip()
    return data

# ---------- UI ----------
class CollapsibleSection(ttk.Frame):
    def __init__(self, master, title):
        super().__init__(master)
        self._expanded = tk.BooleanVar(value=True)
        header = ttk.Frame(self); header.pack(fill="x")
        ttk.Checkbutton(header, text=title, variable=self._expanded,
                        command=self._toggle, style="Toolbutton").pack(side="left", padx=2, pady=3)
        self.body = ttk.Frame(self); self.body.pack(fill="both", expand=True)
    def _toggle(self):
        if self._expanded.get():
            self.body.pack(fill="both", expand=True)
        else:
            self.body.forget()

class ASAIniGUI:
    def __init__(self, root):
        self.root = root
        self.values = {"Game.ini": {}, "GameUserSettings.ini": {}}

        ttk.Label(root, text="Ark: Survival Ascended INI Editor", font=("Segoe UI", 16, "bold")).pack(pady=(10, 5))
        ttk.Label(
            root,
            text="INI files are automatically loaded from this folder (same directory as this script).",
            font=("Segoe UI", 10, "italic"), foreground="#444", anchor="center", justify="center"
        ).pack(pady=(0, 10))

        self._setup_buttons()
        self._setup_tabs()
        self._setup_log()

        # Auto-load if present
        for fn in ("Game.ini", "GameUserSettings.ini"):
            p = Path(fn)
            if p.exists():
                self._load_into_ui(fn, p)
                self._log(f"Loaded {fn}")

    def _setup_buttons(self):
        f = ttk.Frame(self.root); f.pack(fill="x", padx=10, pady=5)
        ttk.Button(f, text="Save Game.ini", command=self._save_game_ini).pack(side="left", padx=5)
        ttk.Button(f, text="Save GameUserSettings.ini", command=self._save_gus_ini).pack(side="left", padx=5)

    def _setup_tabs(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_game = self._make_scroll_tab(); self.nb.add(self.tab_game["container"], text="Game.ini")
        self.tab_gus = self._make_scroll_tab(); self.nb.add(self.tab_gus["container"], text="GameUserSettings.ini")

    def _setup_log(self):
        frame = ttk.Frame(self.root); frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(frame, text="Status Log").pack(anchor="w")
        self.log_box = scrolledtext.ScrolledText(frame, height=6, wrap="word"); self.log_box.pack(fill="x")

    def _make_scroll_tab(self):
        container = ttk.Frame(self.nb)
        canvas = tk.Canvas(container, highlightthickness=0)
        vs = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        frame = ttk.Frame(canvas)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
        return {"container": container, "frame": frame}

    def _log(self, msg):
        self.log_box.insert(tk.END, msg + "\n"); self.log_box.see(tk.END)

    # ---------- Load into UI ----------
    def _load_into_ui(self, which, path: Path):
        data = load_ini(path)
        if not data:
            messagebox.showwarning("Load failed", f"No valid settings found in {path.name}")
            return
        frame = self.tab_game["frame"] if which == "Game.ini" else self.tab_gus["frame"]
        for c in frame.winfo_children(): c.destroy()
        self.values[which].clear()

        for section, kvs in data.items():
            sec = CollapsibleSection(frame, f"[{section}]"); sec.pack(fill="x", expand=True, padx=5, pady=4)
            grid = ttk.Frame(sec.body); grid.pack(fill="x")
            self.values[which][section] = {}
            for r, (key, val) in enumerate(sorted(kvs.items())):
                ttk.Label(grid, text=key).grid(row=r, column=0, sticky="w", padx=4, pady=2)
                vtype = infer_type(val)

                # Tooltip text
                tip = descriptions.get(key)
                for prefix, group_desc in stat_groups.items():
                    if key.startswith(prefix):
                        idx = re.findall(r"\[(\d+)\]", key)
                        if idx:
                            idx = int(idx[0])
                            tip = f"{group_desc}\n\nIndex {idx}: {stat_descriptions.get(idx, '')}"
                        else:
                            tip = group_desc
                        break

                if tip:
                    info = ttk.Button(grid, text="ℹ️", width=2)
                    info.grid(row=r, column=2, sticky="w", padx=2)
                    info.configure(command=lambda k=key, t=tip: messagebox.showinfo(k, t))
                    Tooltip(info, tip)

                # Widgets (no sliders)
                if vtype == "bool":
                    var = tk.BooleanVar(value=(val in TRUE_VALUES))
                    ttk.Checkbutton(grid, variable=var).grid(row=r, column=1, sticky="w")
                elif vtype in ("int", "float"):
                    var = tk.StringVar(value=val)  # keep as string so we can preserve formatting
                    tk.Spinbox(grid, textvariable=var, width=12).grid(row=r, column=1, sticky="w")
                else:
                    var = tk.StringVar(value=val)
                    ttk.Entry(grid, textvariable=var, width=50).grid(row=r, column=1, sticky="w")

                self.values[which][section][key] = var

        self._log(f"Loaded {path.name} into {which}")

    # ---------- Save helpers ----------
    @staticmethod
    def _format_value(var):
        """Return the correct INI string for a Tk variable, preserving int vs decimal as typed."""
        # Booleans
        if isinstance(var, tk.BooleanVar):
            return "true" if var.get() else "false"

        # Strings (used for numbers & text)
        s = var.get().strip()

        # If it's a pure integer string -> write as int (no decimal)
        if re.fullmatch(r"-?\d+", s):
            return str(int(s))

        # If it's a decimal string -> keep exactly as typed (don't cast to float to avoid 5.50 -> 5.5)
        if re.fullmatch(r"-?\d+\.\d+", s):
            return s

        # Everything else (including comma lists, text)
        return s

    def _save_file(self, filename):
        try:
            if not self.values.get(filename):
                messagebox.showinfo("Nothing to save", f"No {filename} loaded.")
                return

            lines = []
            for section, kvs in self.values[filename].items():
                lines.append(f"[{section}]")
                for key, var in kvs.items():
                    lines.append(f"{key}={self._format_value(var)}")
                lines.append("")

            Path(filename).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            self._log(f"Saved {filename}")
        except Exception:
            self._log("Error while saving. See console for details.")
            traceback.print_exc()
            messagebox.showerror("Save Error", traceback.format_exc())

    def _save_game_ini(self):
        self._save_file("Game.ini")

    def _save_gus_ini(self):
        self._save_file("GameUserSettings.ini")

# ---------- Entry ----------
def main():
    root = tk.Tk()
    init_tk_theme(root)
    ASAIniGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
