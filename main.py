import sys
import os
import tkinter as tk
import shlex

root = None
text_area = None
prompt_marker = None
history = []
history_index = 0
vfs_path = ""
script_path = ""

def print_debug_info():
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, f"[DEBUG] VFS path: {vfs_path or '<not set>'}\n")
    text_area.insert(tk.END, f"[DEBUG] Startup script: {script_path or '<not set>'}\n")
    text_area.insert(tk.END, "[DEBUG] --- Configuration loaded ---\n\n")
    text_area.config(state=tk.DISABLED)

def print_prompt():
    global prompt_marker
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, "$ ")
    text_area.config(state=tk.DISABLED)

    text_area.mark_set(tk.INSERT, tk.END)
    prompt_marker = text_area.index(tk.INSERT)
    text_area.config(state=tk.NORMAL)
    text_area.see(tk.END)

def get_current_command():
    if not prompt_marker:
        return ""
    return text_area.get(prompt_marker, tk.END).strip()

def execute_command(cmd_str, is_from_script=False):
    if not cmd_str:
        if not is_from_script:
            print_newline()
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

    text_area.config(state=tk.NORMAL)
    if not is_from_script:
        text_area.insert(tk.END, "\n")
    text_area.insert(tk.END, output)
    text_area.config(state=tk.DISABLED)

    text_area.mark_set(tk.INSERT, tk.END)
    text_area.see(tk.END)

    if not is_from_script:
        print_prompt()

    return False

def print_newline():
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, "\n")
    text_area.config(state=tk.DISABLED)
    print_prompt()

def on_enter(event):
    cmd_str = get_current_command()
    execute_command(cmd_str)
    return "break"

def on_key_press(event):
    current_pos = text_area.index(tk.INSERT)
    if prompt_marker and text_area.compare(current_pos, "<", prompt_marker):
        text_area.mark_set(tk.INSERT, tk.END)
        return "break"
    if event.keysym == "BackSpace":
        if text_area.compare(current_pos, "==", prompt_marker):
            return "break"

def run_startup_script():
    if not script_path or not os.path.isfile(script_path):
        return

    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, f"[SCRIPT] Executing: {script_path}\n")
    text_area.config(state=tk.DISABLED)

    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\r\n')

        if not line or line.startswith("#"):
            continue

        text_area.config(state=tk.NORMAL)
        text_area.insert(tk.END, f"$ {line}\n")
        text_area.config(state=tk.DISABLED)

        should_exit = execute_command(line, is_from_script=True)
        if should_exit:
            root.after(100, root.destroy)
            return

        text_area.config(state=tk.NORMAL)
        text_area.config(state=tk.DISABLED)

    print_prompt()

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

def main():
    global root, text_area

    parse_cli_args()

    root = tk.Tk()
    root.title(os.path.splitext(os.path.basename(vfs_path))[0] if vfs_path else "VFS")
    root.geometry("700x500")

    text_area = tk.Text(root, wrap=tk.WORD, font=("Courier", 12))
    text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    text_area.bind("<Return>", on_enter)
    text_area.bind("<Key>", on_key_press)

    text_area.config(state=tk.DISABLED)

    print_debug_info()
    print_prompt()

    if script_path:
        root.after(500, run_startup_script)

    root.mainloop()

if __name__ == "__main__":
    main()