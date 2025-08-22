import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import threading
import sys
import subprocess
import os
import JMRParser

skipped_line_message = [None]
def ui_warning_callback(msg):
    if skipped_line_message[0] is None:
        skipped_line_message[0] = msg

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "9", "normal"), height=3)
        label.pack(ipadx=5, ipady=5)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class FuriganaApp(tk.Tk):
    @staticmethod
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def __init__(self):
        super().__init__()
        self.title("Furigana Parser")
        self.geometry("560x280") # increase to 560x340 if online translation button is turned back on

        script_dir = FuriganaApp.get_base_dir()  # Corrected line

        self.input_file = os.path.join(script_dir, "Input.txt")
        self.output_folder = script_dir
        self.manual_file = os.path.join(script_dir, "Translation Sheet.xlsx")
        self.output_basename = "Output"

        self.use_offline = tk.BooleanVar(value=True)
        self.use_online = tk.BooleanVar(value=False)
        self.use_spreadsheet = tk.BooleanVar(value=False)

        # Create the status label early with “Loading...” text

        threading.Thread(target=self.background_init, daemon=True).start()

        self.create_widgets()

    def background_init(self):
        # Run the heavy initialization function
        JMRParser.heavy_initialization()
        
        # After it finishes, schedule a function on the main thread to update the UI
        self.after(0, self.set_ready_status)

    def set_ready_status(self):
        self.status_label.config(text="Ready", fg="blue")

    def create_widgets(self):
        # Input file
        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=10, pady=(16, 0))
        tk.Label(input_frame, text="Input file:").pack(side="left")
        self.input_entry = tk.Entry(input_frame)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        tk.Button(input_frame, text="Browse", command=self.browse_input).pack(side="right")
        self.input_entry.insert(0, self.input_file)

        # Output folder and base name on same row
        output_frame = tk.Frame(self)
        output_frame.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(output_frame, text="Output Name:").pack(side="left")
        self.output_basename_entry = tk.Entry(output_frame, width=20)
        self.output_basename_entry.pack(side="left", padx=(5, 5))
        self.output_basename_entry.insert(0, self.output_basename)

        tk.Label(output_frame, text="Folder:").pack(side="left", padx=(10, 0))
        self.output_folder_entry = tk.Entry(output_frame)
        self.output_folder_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        tk.Button(output_frame, text="Browse", command=self.browse_output_folder).pack(side="left")
        self.output_folder_entry.insert(0, self.output_folder)

        # Manual translation
        manual_frame = tk.Frame(self)
        manual_frame.pack(fill="x", padx=10, pady=(10, 0))

        label_manual = tk.Label(manual_frame, text="Manual Translation:  ⓘ", fg="black", cursor="question_arrow")
        label_manual.pack(side="left")

        self.manual_entry = tk.Entry(manual_frame)
        self.manual_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))

        # Tooltip text with the info that was previously in parentheses
        tooltip_text = (
            "Expects same format as output xlsx;\n"
            "Japanese must match input text by row\n"
            "unmatched Japanese lines are skipped"
        )

        ToolTip(label_manual, tooltip_text)

        tk.Button(manual_frame, text="Browse", command=self.browse_manual).pack(side="right")

        # Translation options and process button
        options_process_frame = tk.Frame(self)
        options_process_frame.pack(fill="x", padx=10, pady=(5, 0))

        option_frame = tk.LabelFrame(options_process_frame, text="Process JSON Options")
        option_frame.pack(side="left", fill="y")
        tk.Checkbutton(option_frame, text="Use Offline Translation", variable=self.use_offline).pack(anchor="w", padx=10, pady=2)
        # hiding the online translation button because it doesn't work. It used to work, I think Libre blocked me.
        # tk.Checkbutton(option_frame, text="Use Online Translation (Slow)", variable=self.use_online).pack(anchor="w", padx=10, pady=2)
        tk.Checkbutton(option_frame, text="Output .xlsx with JSON for Manual Translation", variable=self.use_spreadsheet).pack(anchor="w", padx=10, pady=2)

        process_frame = tk.Frame(options_process_frame)
        process_frame.pack(side="right", anchor="s")
        tk.Button(process_frame, text="Process to Word", command=self.run_process_word, width=16).pack(padx=5, pady=(0, 5))
        tk.Button(process_frame, text="Process to JSON", command=self.run_process, width=16).pack(padx=5, pady=(0, 5))

        # Progress bar and status - note we already packed status_label, so skip here to avoid duplication
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill="x", padx=10, pady=(5, 2))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", expand=True)

        # Place status label below progress bar, centered
        self.status_label = tk.Label(self, text="Loading translation packages...", fg="orange")
        self.status_label.pack(pady=2)
        self.warning_label = tk.Label(self, text="", fg="red")
        self.warning_label.pack(pady=2)

    def update_progress(self, current, total):
        self.status_label.config(text=f"Processing line {current + 1} of {total}")
        self.update_idletasks()

    def browse_input(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            self.input_file = file_path
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file_path)

    def browse_manual(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if file_path:
            self.manual_file = file_path
            self.manual_entry.delete(0, tk.END)
            self.manual_entry.insert(0, file_path)

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder_entry.delete(0, tk.END)
            self.output_folder_entry.insert(0, folder)

    def run_process(self):
        if not self.validate_inputs():
            return

        self.status_label.config(text="Processing... Please wait.", fg="blue")
        self.progress_var.set(0)
        self.update()

        thread = threading.Thread(target=self.process_task)
        thread.start()

    def run_process_word(self):
        if not self.validate_inputs():
            return

        self.status_label.config(text="Processing to Word... Please wait.", fg="blue")
        self.progress_var.set(0)
        self.update()

        thread = threading.Thread(target=self.process_task_word)
        thread.start()

    def validate_inputs(self):
        if not self.input_entry.get():
            messagebox.showerror("Error", "Please select an input text file.")
            return False
        if not self.output_folder_entry.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return False
        if not self.output_basename_entry.get():
            messagebox.showerror("Error", "Please enter an output base name.")
            return False
        return True

    def process_task(self):
        try:
            input_path = self.input_entry.get()
            output_folder = self.output_folder_entry.get()
            base_name = self.output_basename_entry.get()
            manual_path = self.manual_entry.get() or None
            use_offline = self.use_offline.get()
            use_online = self.use_online.get()
            export_spreadsheet = self.use_spreadsheet.get()

            output_json_path = os.path.join(output_folder, base_name + ".json")

            def progress_callback(current, total):
                percent = (current + 1) / total * 100
                self.progress_var.set(percent)
                self.status_label.config(text=f"Processing line {current + 1} of {total}")
                self.update_idletasks()

            JMRParser.process_lines_with_options(
                input_path=input_path,
                output_path=output_json_path,
                manual_xlsx=manual_path,
                use_offline=use_offline,
                use_online=use_online,
                export_spreadsheet=export_spreadsheet,
                progress_callback=progress_callback,
                ui_warning_callback=ui_warning_callback
            )

            warning_text = skipped_line_message[0] if skipped_line_message[0] else ""

            if export_spreadsheet:
                self.status_label.config(text=f"Done! JSON and spreadsheet exported.", fg="blue")
            else:
                self.status_label.config(text=f"Done! JSON exported.", fg="blue")
            self.warning_label.config(text=warning_text)
            self.progress_var.set(100)
        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.progress_var.set(0)
            self.warning_label.config(text="")

    def process_task_word(self):
        try:
            input_path = self.input_entry.get()
            output_folder = self.output_folder_entry.get()
            base_name = self.output_basename_entry.get()

            output_docx_path = os.path.join(output_folder, base_name + ".docx")
            JMRParser.create_docx_with_eq_fields(input_path, output_docx_path)

            self.status_label.config(text="Done! Word document exported.", fg="blue")
            self.progress_var.set(100)
        except Exception as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.progress_var.set(0)

if __name__ == "__main__":
    def ensure_required_packages():
        required = [
            "argostranslate",
            "pykakasi",
            "openpyxl",
            "requests",
            "python-docx"
        ]

        for package in required:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                print(f"Installing missing package: {package}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    app = FuriganaApp()
    app.mainloop()
