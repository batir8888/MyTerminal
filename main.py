import tkinter as tk
import shlex

root = None
text_area = None
prompt_marker = None
history = []
history_index = 0

def print_prompt():
    global prompt_marker
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, "$ ")
    text_area.config(state=tk.DISABLED)
    prompt_marker = text_area.index(tk.INSERT)
    text_area.config(state=tk.NORMAL)
    text_area.see(tk.END)

def get_current_command():
    if not prompt_marker:
        return ""
    return text_area.get(prompt_marker, tk.END).strip()

def execute_command(cmd_str):
    global history, history_index
    if not cmd_str:
        print_newline()
        return

    history.append(cmd_str)
    history_index = len(history)

    try:
        parts = shlex.split(cmd_str)
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "exit":
            root.destroy()
            return
        elif cmd in ["ls", "cd"]:
            output = f"{cmd} called with args: {args}\n"
        else:
            output = f"Command '{cmd}' not found.\n"

    except ValueError as e:
        output = f"Parse error: {e}\n"

    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, "\n" + output)
    text_area.config(state=tk.DISABLED)
    print_prompt()

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

def main():
    global root, text_area
    root = tk.Tk()
    root.title("VFS")
    root.geometry("700x500")

    text_area = tk.Text(root, wrap=tk.WORD, font=("Courier", 12))
    text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    text_area.bind("<Return>", on_enter)
    text_area.bind("<Key>", on_key_press)

    text_area.config(state=tk.DISABLED)
    print_prompt()

    root.mainloop()

if __name__ == "__main__":
    main()