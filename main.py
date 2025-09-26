import base64
import json
import os
import shlex
import sys
import tkinter as tk
from typing import Dict, Any, Tuple, List
import numpy

root = None
text_area: tk.Text = None
input_entry: tk.Entry = None
history = []
history_index = 0
vfs_path = ""
script_path = ""

# ---------- VFS (in-memory) ----------
# Формат узла:
# dir: {"type":"dir","children":{name:node,...}}
# file text: {"type":"file","encoding":"utf8","data":"..."}
# file bin:  {"type":"file","encoding":"base64","data":"..."}
VFS: Dict[str, Any] = {}
CWD: List[str] = []

def load_vfs_from_json(path: str):
    global VFS, CWD
    with open(path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    VFS = normalize_vfs(spec)
    CWD = []

def normalize_vfs(spec: Dict[str, Any]) -> Dict[str, Any]:
    if "type" in spec:
        return spec
    return {"type":"dir","children":_normalize_children(spec)}

def _normalize_children(tree: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for name, val in tree.items():
        if isinstance(val, dict):
            node = {"type":"dir","children":_normalize_children(val)}
        elif isinstance(val, str):
            node = {"type":"file","encoding":"utf8","data":val}
        elif isinstance(val, bytes):
            node = {"type":"file","encoding":"base64","data":base64.b64encode(val).decode("ascii")}
        else:
            raise ValueError(f"Unsupported VFS value for '{name}'")
        out[name] = node
    return out

def _node_by_stack(stack):
    node = VFS
    for comp in stack:
        node = node["children"][comp]
    return node

def resolve(path: str):
    stack = [] if path.startswith("/") else list(CWD)
    parts = [p for p in path.split("/") if p]
    node = _node_by_stack(stack)

    for part in parts:
        if part == ".":
            continue
        if part == "..":
            if stack:
                stack.pop()
            node = _node_by_stack(stack)
            continue
        if node.get("type") != "dir":
            raise TypeError("Not a directory")
        children = node.get("children", {})
        if part not in children:
            raise KeyError("No such file or directory")
        stack.append(part)
        node = children[part]
    return stack, node


def list_dir(target: Dict[str, Any]) -> List[Tuple[str, str]]:
    if target.get("type") != "dir":
        raise TypeError("Not a directory")
    items = []
    for name, node in target.get("children", {}).items():
        items.append((name, node.get("type")))
    items.sort(key=lambda x: (x[1] != "dir", x[0].lower()))
    return items

def read_file(node: Dict[str, Any]) -> str:
    if node.get("type") != "file":
        raise TypeError("Not a file")
    enc = node.get("encoding", "utf8")
    data = node.get("data", "")
    if enc == "utf8":
        return data
    elif enc == "base64":
        # не распаковываем содержимое, только подтверждаем размер
        try:
            raw = base64.b64decode(data, validate=True)
            return f"<binary {len(raw)} bytes>"
        except Exception:
            return "<binary invalid base64>"
    else:
        return f"<unknown encoding: {enc}>"

def print_debug_info():
    append_output(f"[DEBUG] VFS path: {vfs_path or '<not set>'}\n")
    append_output(f"[DEBUG] Startup script: {script_path or '<not set>'}\n")
    append_output("[DEBUG] --- Configuration loaded ---\n\n")

def append_output(s: str):
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, s)
    text_area.see(tk.END)
    text_area.config(state=tk.DISABLED)

def execute_command(cmd_str, is_from_script=False):
    global history_index, CWD

    if not cmd_str:
        if not is_from_script:
            append_output("\n")
        return False

    if not is_from_script:
        history.append(cmd_str)
        history_index = len(history)

    try:
        parts = shlex.split(cmd_str)
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "exit":
            if not is_from_script:
                root.destroy()
            return True

        elif cmd in ["ls", "cd"]:
            output = f"{cmd} called with args: {args}\n"
        else:
            output = f"Command '{cmd}' not found.\n"

    except ValueError as e:
        output = f"Parse error: {e}\n"

    if not is_from_script:
        append_output(f"$ {cmd_str}\n")
    append_output(output)
    return False

def on_enter(event=None):
    cmd_str = input_entry.get().strip()
    input_entry.delete(0, tk.END)
    execute_command(cmd_str)
    return "break"

def on_history_up(event=None):
    global history_index
    if not history:
        return "break"
    history_index = max(0, history_index - 1)
    input_entry.delete(0, tk.END)
    input_entry.insert(0, history[history_index])
    return "break"

def on_history_down(event=None):
    global history_index
    if not history:
        return "break"
    history_index = min(len(history), history_index + 1)
    input_entry.delete(0, tk.END)
    if history_index < len(history):
        input_entry.insert(0, history[history_index])
    return "break"

def run_startup_script():
    if not script_path or not os.path.isfile(script_path):
        return
    append_output(f"[SCRIPT] Executing: {script_path}\n")
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\r\n')
        if not line or line.startswith("#"):
            continue
        append_output(f"$ {line}\n")
        should_exit = execute_command(line, is_from_script=True)
        if should_exit:
            root.after(100, root.destroy)
            return

def parse_cli_args():
    global vfs_path, script_path
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--vfs" and i + 1 < len(args):
            vfs_path = args[i + 1]
            i += 2
        elif args[i] == "--script" and i + 1 < len(args):
            script_path = args[i + 1]
            i += 2
        else:
            i += 1

def check_vfs_exists(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.R_OK)

class NoVfsException(Exception):
    pass

def main():
    global root, text_area, input_entry
    parse_cli_args()
    if not vfs_path or not check_vfs_exists(vfs_path):
        raise NoVfsException(f"VFS file not found by this path {vfs_path}")

    # Загрузка VFS целиком в память
    load_vfs_from_json(vfs_path)

    root = tk.Tk()
    root.title(os.path.splitext(os.path.basename(vfs_path))[0] if vfs_path else "VFS")
    root.geometry("700x500")

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    text_area = tk.Text(root, wrap=tk.WORD, font=("Courier", 12), state=tk.DISABLED)
    text_area.grid(row=0, column=0, sticky="nsew")
    scrollbar = tk.Scrollbar(root, command=text_area.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    text_area.config(yscrollcommand=scrollbar.set)

    input_frame = tk.Frame(root)
    input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
    input_frame.columnconfigure(0, weight=1)

    input_entry = tk.Entry(input_frame, font=("Courier", 12))
    input_entry.grid(row=0, column=0, sticky="ew")
    run_btn = tk.Button(input_frame, text="Run", command=on_enter)
    run_btn.grid(row=0, column=1, padx=(5,0))

    input_entry.bind("<Return>", on_enter)
    input_entry.bind("<Up>", on_history_up)
    input_entry.bind("<Down>", on_history_down)

    print_debug_info()

    if script_path:
        root.after(500, run_startup_script)

    input_entry.focus_set()
    root.mainloop()

if __name__ == "__main__":
    main()
