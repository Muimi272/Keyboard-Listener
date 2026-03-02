import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image, ImageDraw
from pyhooked import Hook, KeyboardEvent

CONFIG_FILE = "config.json"
ICON_FILE = "icon.png"
DEFAULT_CONFIG = {
    "BATCH_THRESHOLD": 10,
    "DATA_FILE": "data.json",
    "VERSION": "1.1",
}
VK_MAP = {
    8: "Backspace",
    9: "Tab",
    13: "Enter",
    16: "Shift",
    17: "Ctrl",
    18: "Alt",
    20: "CapsLock",
    27: "ESC",
    32: "Space",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "Left",
    38: "Up",
    39: "Right",
    40: "Down",
    44: "PrintScreen",
    45: "Insert",
    46: "Delete",
    48: "0",
    49: "1",
    50: "2",
    51: "3",
    52: "4",
    53: "5",
    54: "6",
    55: "7",
    56: "8",
    57: "9",
    65: "A",
    66: "B",
    67: "C",
    68: "D",
    69: "E",
    70: "F",
    71: "G",
    72: "H",
    73: "I",
    74: "J",
    75: "K",
    76: "L",
    77: "M",
    78: "N",
    79: "O",
    80: "P",
    81: "Q",
    82: "R",
    83: "S",
    84: "T",
    85: "U",
    86: "V",
    87: "W",
    88: "X",
    89: "Y",
    90: "Z",
    91: "Windows",
    92: "Sleep",
    93: "ContextMenu",
    96: "Num0",
    97: "Num1",
    98: "Num2",
    99: "Num3",
    100: "Num4",
    101: "Num5",
    102: "Num6",
    103: "Num7",
    104: "Num8",
    105: "Num9",
    106: "NumMultiply",
    107: "NumAdd",
    109: "NumSubtract",
    110: "NumDecimal",
    111: "NumDivide",
    112: "F1",
    113: "F2",
    114: "F3",
    115: "F4",
    116: "F5",
    117: "F6",
    118: "F7",
    119: "F8",
    120: "F9",
    121: "F10",
    122: "F11",
    123: "F12",
    144: "NumLock",
    145: "ScrollLock",
    160: "LShift",
    161: "RShift",
    162: "LCtrl",
    163: "RCtrl",
    164: "LAlt",
    165: "RAlt",
    186: ";",
    187: "=",
    188: ",",
    189: "-",
    190: ".",
    191: "/",
    192: "`",
    219: "[",
    220: "\\",
    221: "]",
    222: "'",
}
key_counts = {}
total_press = 0
is_paused = False
is_running = True
BATCH_THRESHOLD = DEFAULT_CONFIG["BATCH_THRESHOLD"]
DATA_FILE = DEFAULT_CONFIG["DATA_FILE"]
version = DEFAULT_CONFIG["VERSION"]
hk = None
tray_icon = None
app_root = None
window = None
status_label = None
total_label = None
threshold_label = None
data_file_label = None
keys_tree = None
window_update_job = None
tk_icon_image = None
keys_render_cache = []
dashboard_rebuild_pending = False

def get_resource_path(file_name):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, file_name)

def apply_window_icon(target_window):
    global tk_icon_image
    icon_path = get_resource_path(ICON_FILE)
    if not os.path.exists(icon_path):
        return
    try:
        tk_icon_image = tk.PhotoImage(file=icon_path)
        target_window.iconphoto(True, tk_icon_image)
    except Exception as e:
        print(f"Failed to apply window icon: {e}")

def ensure_config_file():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

def load_config():
    global BATCH_THRESHOLD, DATA_FILE, version
    ensure_config_file()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        loaded_threshold = config_data.get(
            "BATCH_THRESHOLD", DEFAULT_CONFIG["BATCH_THRESHOLD"]
        )
        loaded_data_file = config_data.get("DATA_FILE", DEFAULT_CONFIG["DATA_FILE"])
        loaded_version = config_data.get("VERSION", DEFAULT_CONFIG["VERSION"])

        if not isinstance(loaded_threshold, int) or loaded_threshold <= 0:
            loaded_threshold = DEFAULT_CONFIG["BATCH_THRESHOLD"]

        if not isinstance(loaded_data_file, str) or not loaded_data_file.strip():
            loaded_data_file = DEFAULT_CONFIG["DATA_FILE"]

        if not isinstance(loaded_version, str) or not loaded_version.strip():
            loaded_version = DEFAULT_CONFIG["VERSION"]

        BATCH_THRESHOLD = loaded_threshold
        DATA_FILE = loaded_data_file
        version = loaded_version
        print(
            "Loaded config: "
            f"BATCH_THRESHOLD={BATCH_THRESHOLD}, DATA_FILE={DATA_FILE}, VERSION={version}"
        )
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {CONFIG_FILE}: {e}. Using default config.")
        BATCH_THRESHOLD = DEFAULT_CONFIG["BATCH_THRESHOLD"]
        DATA_FILE = DEFAULT_CONFIG["DATA_FILE"]
        version = DEFAULT_CONFIG["VERSION"]
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}. Using default config.")
        BATCH_THRESHOLD = DEFAULT_CONFIG["BATCH_THRESHOLD"]
        DATA_FILE = DEFAULT_CONFIG["DATA_FILE"]
        version = DEFAULT_CONFIG["VERSION"]

def save_to_file():
    save_data = {"key_counts": key_counts, "total_press": total_press}
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=0)
        print(f"\n Data has saved in {DATA_FILE}")
    except Exception as e:
        print(f"\n Error saving data: {e}")

def load_from_file():
    global key_counts, total_press
    if not os.path.exists(DATA_FILE):
        print(f"No existing data file found: {DATA_FILE}. Starting fresh.")
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            save_data = json.load(f)

        loaded_key_counts = save_data.get("key_counts", {})
        loaded_total_press = save_data.get("total_press", 0)

        if isinstance(loaded_key_counts, dict) and isinstance(loaded_total_press, int):
            key_counts = loaded_key_counts
            total_press = loaded_total_press
            print(f"Loaded data from {DATA_FILE}: total_press={total_press}")
        else:
            print(f"Invalid data format in {DATA_FILE}. Starting fresh.")
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {DATA_FILE}: {e}. Starting fresh.")
    except Exception as e:
        print(f"Error loading data from {DATA_FILE}: {e}. Starting fresh.")
        
def vk_to_key_name(vk_code):
    return VK_MAP.get(vk_code, f"Unknown({vk_code})")

def handle_events(args):
    global total_press, key_counts
    if not is_running or is_paused:
        return
    if isinstance(args, KeyboardEvent) and args.event_type == "key down":
        key_name = vk_to_key_name(args.key_code)
        key_counts[key_name] = key_counts.get(key_name, 0) + 1
        total_press += 1

        if total_press % BATCH_THRESHOLD == 0:
            save_to_file()

        if args.key_code == 27:
            exit_program()

def hook_worker():
    try:
        hk.hook()
    except Exception as e:
        print(f"Hook error: {e}")

def _window_exists(target_window):
    if target_window is None:
        return False
    try:
        return bool(target_window.winfo_exists())
    except tk.TclError:
        return False

def _cancel_window_refresh():
    global window_update_job
    if window_update_job is not None and app_root is not None:
        try:
            app_root.after_cancel(window_update_job)
        except Exception:
            pass
        window_update_job = None

def _find_first_widget_of_type(root_widget, widget_type):
    if root_widget is None:
        return None
    try:
        children = root_widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, widget_type):
            return child
        found = _find_first_widget_of_type(child, widget_type)
        if found is not None:
            return found
    return None

def _rebuild_dashboard_window():
    global window, keys_tree, keys_render_cache, dashboard_rebuild_pending
    global status_label, total_label, threshold_label, data_file_label
    try:
        if _window_exists(window):
            try:
                window.destroy()
            except Exception:
                pass
        window = None
        keys_tree = None
        status_label = None
        total_label = None
        threshold_label = None
        data_file_label = None
        keys_render_cache = []
        if app_root is not None:
            open_window()
    finally:
        dashboard_rebuild_pending = False

def _create_fallback_icon():
    image = Image.new("RGBA", (64, 64), (20, 20, 20, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 54, 54), outline=(200, 200, 200), width=3)
    draw.line((18, 32, 46, 32), fill=(200, 200, 200), width=3)
    return image

def _attach_hover_tooltip(widget, text):
    tooltip = {"window": None}
    def show(_event=None):
        if tooltip["window"] is not None:
            return
        try:
            x = widget.winfo_rootx() + widget.winfo_width() - 10
            y = widget.winfo_rooty() - 28
        except Exception:
            return
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tip,
            text=text,
            bg="#151b28",
            fg="#d8e0ec",
            padx=8,
            pady=4,
            font=("Segoe UI", 9),
            highlightthickness=1,
            highlightbackground="#232d3f",
        )
        label.pack()
        tooltip["window"] = tip
        
    def hide(_event=None):
        tip = tooltip.get("window")
        if tip is None:
            return
        try:
            tip.destroy()
        except Exception:
            pass
        tooltip["window"] = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)

def _block_treeview_heading_click(event):
    widget = event.widget
    try:
        if widget.identify_region(event.x, event.y) == "heading":
            return "break"
    except Exception:
        return None
    return None

def create_icon(paused):
    icon_path = get_resource_path(ICON_FILE)
    if os.path.exists(icon_path):
        try:
            image = Image.open(icon_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
        except Exception:
            image = _create_fallback_icon()
    else:
        image = _create_fallback_icon()
    if paused:
        draw = ImageDraw.Draw(image)
        dot_size = 16
        x1 = image.width - dot_size - 2
        y1 = image.height - dot_size - 2
        x2 = image.width - 2
        y2 = image.height - 2
        draw.ellipse([x1, y1, x2, y2], fill=(255, 0, 0, 255))

    return image.convert("RGB")


def toggle_pause():
    global is_paused
    is_paused = not is_paused
    if tray_icon is not None:
        tray_icon.icon = create_icon(is_paused)
        tray_icon.update_menu()
    schedule_window_refresh()

def open_config_file():
    ensure_config_file()
    try:
        os.startfile(CONFIG_FILE)
    except Exception as e:
        print(f"Failed to open {CONFIG_FILE}: {e}")

def refresh_window_data():
    global keys_render_cache, keys_tree, dashboard_rebuild_pending
    if not _window_exists(window):
        return
    state_text = "Paused" if is_paused else "Counting"
    if status_label is not None:
        status_label.config(
            text=f"Status: {state_text}",
            fg="#ef4444" if is_paused else "#22c55e",
        )
    if total_label is not None:
        total_label.config(text=f"Total key presses: {total_press}")
    if threshold_label is not None:
        threshold_label.config(text=f"Batch save threshold: {BATCH_THRESHOLD}")
    if data_file_label is not None:
        data_file_label.config(text=f"Data file: {DATA_FILE}")
    if keys_tree is None:
        keys_tree = _find_first_widget_of_type(window, ttk.Treeview)
    if keys_tree is None:
        if app_root is not None and not dashboard_rebuild_pending:
            dashboard_rebuild_pending = True
            app_root.after(0, _rebuild_dashboard_window)
        return
    sorted_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
    try:
        was_list_empty = len(keys_tree.get_children("")) == 0
    except Exception:
        was_list_empty = True
    if (not was_list_empty) and (sorted_keys == keys_render_cache):
        return
    try:
        top_fraction, bottom_fraction = keys_tree.yview()
    except Exception:
        top_fraction, bottom_fraction = 0.0, 1.0
    follow_bottom = (not was_list_empty) and (bottom_fraction >= 0.995)
    try:
        keys_tree.delete(*keys_tree.get_children(""))
    except Exception:
        pass
    for index, (key, count) in enumerate(sorted_keys, start=1):
        keys_tree.insert("", "end", values=(key, count))
    if follow_bottom:
        keys_tree.yview_moveto(1.0)
    else:
        keys_tree.yview_moveto(0.0 if was_list_empty else top_fraction)
    keys_render_cache = list(sorted_keys)

def schedule_window_refresh():
    global window_update_job
    _cancel_window_refresh()
    if app_root is None or not _window_exists(window):
        return
    refresh_window_data()
    window_update_job = app_root.after(1000, schedule_window_refresh)

def open_window():
    global window
    global status_label, total_label, threshold_label, data_file_label, keys_tree
    if _window_exists(window):
        window.deiconify()
        window.lift()
        window.focus_force()
        return
    window = tk.Toplevel(app_root)
    window.title("Keyboard Listener Dashboard")
    window.geometry("700x640")
    window.configure(bg="#0b0f17")
    window.minsize(720, 520)
    window.resizable(False, False)
    apply_window_icon(window)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Dashboard.Vertical.TScrollbar",
        troughcolor="#0f1420",
        background="#2d3b53",
        darkcolor="#2d3b53",
        lightcolor="#2d3b53",
        bordercolor="#0f1420",
        arrowcolor="#90a3bf",
        relief="flat",
    )
    style.map(
        "Dashboard.Vertical.TScrollbar",
        background=[("active", "#3a4c6d"), ("pressed", "#4a628b")],
        arrowcolor=[("active", "#d8e0ec")],
    )
    style.map(
        "Dashboard.Treeview.Heading",
        background=[("active", "#151b28"), ("pressed", "#151b28")],
        foreground=[("active", "#8ea0b8"), ("pressed", "#8ea0b8")],
    )

    main_frame = tk.Frame(window, bg="#0b0f17", padx=24, pady=22)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_label = tk.Label(
        main_frame,
        text="KEYBOARD LISTENER",
        font=("Segoe UI", 20, "bold"),
        bg="#0b0f17",
        fg="#f7f9fc",
    )
    title_label.pack(anchor="w")
    subtitle_label = tk.Label(
        main_frame,
        text="Live activity overview",
        font=("Segoe UI", 11),
        bg="#0b0f17",
        fg="#8ea0b8",
    )
    subtitle_label.pack(anchor="w", pady=(4, 16))
    summary_card = tk.Frame(
        main_frame,
        bg="#151b28",
        highlightthickness=1,
        highlightbackground="#232d3f",
        padx=16,
        pady=14,
    )
    summary_card.pack(fill=tk.X)
    summary_grid = tk.Frame(summary_card, bg="#151b28")
    summary_grid.pack(fill=tk.X)
    summary_grid.columnconfigure(0, weight=1)
    summary_grid.columnconfigure(1, weight=1)
    status_label = tk.Label(
        summary_grid,
        text="",
        font=("Segoe UI", 11, "bold"),
        bg="#151b28",
        fg="#22c55e",
        anchor="w",
    )
    status_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    total_label = tk.Label(
        summary_grid,
        text="",
        font=("Segoe UI", 11),
        bg="#151b28",
        fg="#d8e0ec",
        anchor="w",
    )
    total_label.grid(row=1, column=0, sticky="ew", pady=(0, 6), padx=(0, 12))
    threshold_label = tk.Label(
        summary_grid,
        text="",
        font=("Segoe UI", 11),
        bg="#151b28",
        fg="#d8e0ec",
        anchor="w",
    )
    threshold_label.grid(row=1, column=1, sticky="ew", pady=(0, 6))
    data_file_label = tk.Label(
        summary_grid,
        text="",
        font=("Segoe UI", 11),
        bg="#151b28",
        fg="#d8e0ec",
        anchor="w",
    )
    data_file_label.grid(row=2, column=0, columnspan=2, sticky="ew")
    keys_title = tk.Label(
        main_frame,
        text="Top Key Presses",
        font=("Segoe UI", 13, "bold"),
        bg="#0b0f17",
        fg="#f7f9fc",
    )
    keys_title.pack(anchor="w", pady=(20, 10))
    keys_frame = tk.Frame(
        main_frame,
        bg="#151b28",
        highlightthickness=1,
        highlightbackground="#232d3f",
        highlightcolor="#232d3f",
        padx=14,
        pady=10,
    )
    keys_frame.pack(fill=tk.BOTH, expand=True)
    keys_frame.columnconfigure(0, weight=1)
    keys_frame.columnconfigure(1, weight=0)
    keys_frame.columnconfigure(2, weight=1)
    keys_center = tk.Frame(keys_frame, bg="#151b28")
    keys_center.grid(row=0, column=1, sticky="n")
    scrollbar = ttk.Scrollbar(
        keys_center,
        orient="vertical",
        style="Dashboard.Vertical.TScrollbar",
    )
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    style.configure(
        "Dashboard.Treeview",
        background="#151b28",
        fieldbackground="#151b28",
        foreground="#d8e0ec",
        borderwidth=0,
        relief="flat",
        lightcolor="#151b28",
        darkcolor="#151b28",
        bordercolor="#151b28",
        rowheight=24,
        font=("Consolas", 11),
    )
    style.configure(
        "Dashboard.Treeview.Heading",
        background="#151b28",
        foreground="#8ea0b8",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
    )
    style.map(
        "Dashboard.Treeview",
        background=[("selected", "#27364f")],
        foreground=[("selected", "#ffffff")],
        relief=[("active", "flat")],
        borderwidth=[("active", 0)],
        bordercolor=[("focus", "#151b28")],
        lightcolor=[("focus", "#151b28")],
        darkcolor=[("focus", "#151b28")],
    )

    keys_tree = ttk.Treeview(
        keys_center,
        columns=("key", "count"),
        show="headings",
        style="Dashboard.Treeview",
        takefocus=False,
    )
    keys_tree.heading("key", text="Key", anchor="center")
    keys_tree.heading("count", text="Count", anchor="center")
    keys_tree.column("key", anchor="center", width=320, stretch=True)
    keys_tree.column("count", anchor="center", width=320, stretch=True)
    keys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    keys_tree.bind("<Button-1>", _block_treeview_heading_click, add=True)
    scrollbar.config(command=keys_tree.yview)
    keys_tree.configure(yscrollcommand=scrollbar.set)
    footer_frame = tk.Frame(main_frame, bg="#0b0f17")
    footer_frame.pack(fill=tk.X, pady=(10, 0))
    version_label = tk.Label(
        footer_frame,
        text=f"Version: {version}",
        font=("Segoe UI", 10),
        bg="#0b0f17",
        fg="#8ea0b8",
        anchor="e",
    )
    version_label.pack(side=tk.RIGHT)
    _attach_hover_tooltip(version_label, "Made by Muimi")
    refresh_window_data()
    schedule_window_refresh()
    def close_window():
        global window, keys_tree, keys_render_cache
        _cancel_window_refresh()
        keys_tree = None
        keys_render_cache = []
        if window is None:
            return
        try:
            window.destroy()
        finally:
            window = None
    window.protocol("WM_DELETE_WINDOW", close_window)

def request_open_window(icon=None, item=None):
    if app_root is not None:
        app_root.after(0, open_window)

def create_tray_icon():
    def pause_menu_text(_item):
        return "Resume Counting" if is_paused else "Pause Counting"
    menu = pystray.Menu(
        pystray.MenuItem(pause_menu_text, lambda icon, item: toggle_pause()),
        pystray.MenuItem("Open Dashboard", request_open_window),
        pystray.MenuItem("Open Config", lambda icon, item: open_config_file()),
        pystray.MenuItem("Exit", lambda icon, item: exit_program()),
    )
    return pystray.Icon(
        "KeyboardListener",
        create_icon(is_paused),
        "Keyboard Listener",
        menu,
    )

def close_all_windows():
    global window, keys_tree, keys_render_cache
    _cancel_window_refresh()
    if _window_exists(window):
        try:
            window.destroy()
        except tk.TclError:
            pass
    window = None
    keys_tree = None
    keys_render_cache = []
    if app_root is not None:
        app_root.quit()

def exit_program():
    global is_running
    if not is_running:
        return
    is_running = False
    save_to_file()
    try:
        hk.unhook()
    except Exception:
        pass
    if tray_icon is not None:
        tray_icon.stop()
    if app_root is not None:
        app_root.after(0, close_all_windows)

def main():
    global hk, tray_icon, app_root
    load_config()
    load_from_file()
    hk = Hook()
    hk.handler = handle_events
    threading.Thread(target=hook_worker, daemon=True).start()
    tray_icon = create_tray_icon()
    threading.Thread(target=tray_icon.run, daemon=True).start()
    app_root = tk.Tk()
    app_root.withdraw()
    apply_window_icon(app_root)
    app_root.mainloop()

if __name__ == "__main__":
    main()
