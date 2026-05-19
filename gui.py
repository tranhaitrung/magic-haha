from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
import tkinter.ttk as ttk


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def _data_dir() -> Path:
    """Writable directory for logs, inbox, output, etc.

    When frozen as an exe the install dir may not be writable (e.g. Program
    Files), so redirect to %APPDATA%\\fb-scanner on Windows.
    """
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", Path.home())) if sys.platform == "win32" else Path.home()
        return base / "fb-scanner"
    return Path(__file__).parent


BASE_DIR = _base_dir()
CONFIG_PATH = BASE_DIR / "config.json"
DATA_DIR = _data_dir()


# ---------------------------------------------------------------------------
# Scan worker — runs in background thread, sends messages via queue
# ---------------------------------------------------------------------------

def _run_scan(excel_path: Path, profile_path: str | None, msg_queue: queue.Queue) -> None:
    try:
        from src.config_loader import load_config
        from src.logging_setup import setup_logging
        from src.orchestrator import ensure_local_directories, process_single_input_file

        config = load_config(str(CONFIG_PATH))

        # When frozen as exe the install dir is often read-only; redirect all
        # writable paths to DATA_DIR (%APPDATA%\fb-scanner on Windows).
        if DATA_DIR != Path(__file__).parent:
            p = config.paths
            p.log_dir        = DATA_DIR / "logs"
            p.inbox_dir      = DATA_DIR / "inbox"
            p.processing_dir = DATA_DIR / "processing"
            p.output_dir     = DATA_DIR / "output"
            p.archive_dir    = DATA_DIR / "archive"
            p.error_dir      = DATA_DIR / "error"

        logger = setup_logging(config.paths.log_dir)
        ensure_local_directories(config)

        inbox_file = config.paths.inbox_dir / excel_path.name
        if excel_path.resolve() != inbox_file.resolve():
            shutil.copy2(str(excel_path), str(inbox_file))

        # Patch orchestrator to emit progress messages
        import src.orchestrator as orch_mod

        original_process = orch_mod.process_single_input_file

        def patched_process(input_file, cfg, lgr, profile_path=None):
            from src.excel_reader import read_channel_tasks
            from src.channel_scanner import ChannelScanner
            from src.models import ScanStatus, FileProcessResult
            from src.redirect_resolver import clear_resolve_cache
            from src.result_writer import write_results_to_csv
            import src.orchestrator as o

            processing_file = o._unique_target_file(cfg.paths.processing_dir / input_file.name)
            shutil.move(str(input_file), str(processing_file))

            output_file = None
            total = success = failed = 0

            try:
                tasks = read_channel_tasks(processing_file)
                total = len(tasks)
                msg_queue.put(("total", total))
                msg_queue.put(("log", f"Đọc được {total} kênh từ file Excel"))

                scanner = ChannelScanner(config=cfg, logger=lgr, profile_path=profile_path)
                results = []
                consecutive_login = 0
                force_stop = False

                with scanner:
                    for idx, task in enumerate(tasks, start=1):
                        msg_queue.put(("progress", (idx, total, task.channel_url)))
                        result = scanner.scan_channel(task)
                        results.append(result)

                        status = result.scan_status.value
                        shopee = result.has_shopee_affiliate
                        eco = result.has_eco_link
                        msg_queue.put(("log", f"[{idx}/{total}] {status} | shopee={shopee} eco={eco} | {task.channel_url}"))

                        if result.scan_status == ScanStatus.SUCCESS:
                            success += 1
                        else:
                            failed += 1

                        if result.scan_status == ScanStatus.LOGIN_REQUIRED:
                            consecutive_login += 1
                            if consecutive_login >= cfg.scan.consecutive_login_fail_limit:
                                msg_queue.put(("log", "⚠️ Quá nhiều lần login thất bại — dừng scan"))
                                force_stop = True
                                break
                        else:
                            consecutive_login = 0

                        if result.scan_status == ScanStatus.CAPTCHA:
                            msg_queue.put(("log", "⚠️ Phát hiện CAPTCHA — dừng scan"))
                            force_stop = True
                            break

                if force_stop:
                    msg_queue.put(("log", "Scan dừng sớm"))

                output_file = write_results_to_csv(results, cfg.paths.output_dir, processing_file.stem)
                archive_file = o._unique_target_file(cfg.paths.archive_dir / processing_file.name)
                shutil.move(str(processing_file), str(archive_file))
                clear_resolve_cache()

            except Exception as exc:
                failed += 1
                msg_queue.put(("log", f"❌ Lỗi: {exc}"))
                error_file = o._unique_target_file(cfg.paths.error_dir / processing_file.name)
                if processing_file.exists():
                    shutil.move(str(processing_file), str(error_file))
                clear_resolve_cache()

            return FileProcessResult(
                input_file=input_file,
                output_file=output_file,
                total_channels=total,
                success_channels=success,
                failed_channels=failed,
            )

        result = patched_process(inbox_file, config, logger, profile_path=profile_path)

        msg_queue.put(("done", result))

    except Exception as exc:
        msg_queue.put(("error", str(exc)))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class ScannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("FB Affiliate Scanner")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self._excel_path: Path | None = None
        self._profile_path: str | None = None
        self._msg_queue: queue.Queue = queue.Queue()
        self._scan_thread: threading.Thread | None = None
        self._total_channels = 0

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}

        # Title
        title = tk.Label(
            self,
            text="FB Affiliate Scanner",
            font=("Segoe UI", 16, "bold"),
            bg="#1877f2",
            fg="white",
            anchor="w",
        )
        title.pack(fill="x")

        subtitle = tk.Label(
            self,
            text="Quét link affiliate Shopee / Eco từ kênh Facebook",
            font=("Segoe UI", 9),
            bg="#1877f2",
            fg="#d0e8ff",
            anchor="w",
            padx=16,
            pady=4,
        )
        subtitle.pack(fill="x")

        # File section
        file_frame = tk.LabelFrame(self, text="File Excel đầu vào", bg="#f5f5f5", font=("Segoe UI", 9))
        file_frame.pack(fill="x", **pad)

        self._file_label = tk.Label(
            file_frame,
            text="Chưa chọn file...",
            bg="white",
            anchor="w",
            relief="sunken",
            width=52,
            font=("Segoe UI", 9),
        )
        self._file_label.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

        tk.Button(
            file_frame,
            text="Chọn file...",
            command=self._pick_file,
            width=12,
            font=("Segoe UI", 9),
        ).grid(row=0, column=1, padx=(0, 8), pady=8)

        # Profile section (optional, collapsible)
        self._profile_var = tk.BooleanVar(value=False)
        profile_check = tk.Checkbutton(
            self,
            text="Dùng tài khoản Facebook đã đăng nhập (Chrome profile)",
            variable=self._profile_var,
            command=self._toggle_profile,
            bg="#f5f5f5",
            font=("Segoe UI", 9),
        )
        profile_check.pack(anchor="w", padx=16)

        self._profile_frame = tk.Frame(self, bg="#f5f5f5")

        self._profile_entry = tk.Entry(
            self._profile_frame,
            width=48,
            font=("Segoe UI", 9),
        )
        self._profile_entry.pack(side="left", padx=(16, 4), pady=4)

        tk.Button(
            self._profile_frame,
            text="Chọn...",
            command=self._pick_profile,
            width=8,
            font=("Segoe UI", 9),
        ).pack(side="left")

        # Progress section
        progress_frame = tk.LabelFrame(self, text="Tiến trình", bg="#f5f5f5", font=("Segoe UI", 9))
        progress_frame.pack(fill="x", **pad)

        self._status_label = tk.Label(
            progress_frame,
            text="Chờ bắt đầu...",
            bg="#f5f5f5",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=8, pady=(6, 2))

        self._progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=440)
        self._progress_bar.pack(fill="x", padx=8, pady=(0, 8))

        # Log area
        log_frame = tk.LabelFrame(self, text="Log hoạt động", bg="#f5f5f5", font=("Segoe UI", 9))
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._log_text = tk.Text(
            log_frame,
            height=14,
            state="disabled",
            font=("Consolas", 8),
            bg="#1e1e1e",
            fg="#d4d4d4",
            relief="flat",
            wrap="word",
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # Bottom buttons
        btn_frame = tk.Frame(self, bg="#f5f5f5")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        self._start_btn = tk.Button(
            btn_frame,
            text="▶  Bắt đầu Scan",
            command=self._start_scan,
            bg="#1877f2",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=18,
            relief="flat",
            cursor="hand2",
        )
        self._start_btn.pack(side="left")

        self._open_btn = tk.Button(
            btn_frame,
            text="📂  Mở thư mục kết quả",
            command=self._open_output,
            font=("Segoe UI", 9),
            width=20,
            state="disabled",
            relief="flat",
            cursor="hand2",
        )
        self._open_btn.pack(side="left", padx=(12, 0))

        # Window size
        self.geometry("520x560")

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if path:
            self._excel_path = Path(path)
            self._file_label.config(text=self._excel_path.name)

    def _toggle_profile(self) -> None:
        if self._profile_var.get():
            self._profile_frame.pack(fill="x", before=self._progress_frame_ref() or self._profile_frame)
        else:
            self._profile_frame.pack_forget()

    def _profile_frame_ref(self):
        return None

    def _pick_profile(self) -> None:
        path = filedialog.askdirectory(title="Chọn thư mục Chrome profile")
        if path:
            self._profile_entry.delete(0, tk.END)
            self._profile_entry.insert(0, path)

    def _start_scan(self) -> None:
        if not self._excel_path or not self._excel_path.exists():
            messagebox.showwarning("Thiếu file", "Vui lòng chọn file Excel trước khi scan.")
            return

        profile = None
        if self._profile_var.get():
            profile = self._profile_entry.get().strip() or None

        self._start_btn.config(state="disabled", text="⏳ Đang scan...")
        self._open_btn.config(state="disabled")
        self._progress_bar["value"] = 0
        self._status_label.config(text="Đang khởi động...")
        self._log_append(f"▶ Bắt đầu scan: {self._excel_path.name}\n")

        self._scan_thread = threading.Thread(
            target=_run_scan,
            args=(self._excel_path, profile, self._msg_queue),
            daemon=True,
        )
        self._scan_thread.start()

    def _open_output(self) -> None:
        output_dir = BASE_DIR / "data" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(output_dir)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(output_dir)])
        else:
            subprocess.Popen(["xdg-open", str(output_dir)])

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_append(self, text: str) -> None:
        self._log_text.config(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    # ------------------------------------------------------------------
    # Queue polling — called every 100ms from main thread
    # ------------------------------------------------------------------

    def _poll_queue(self) -> None:
        try:
            while True:
                msg_type, payload = self._msg_queue.get_nowait()

                if msg_type == "total":
                    self._total_channels = payload
                    self._progress_bar["maximum"] = payload

                elif msg_type == "log":
                    self._log_append(str(payload))

                elif msg_type == "progress":
                    idx, total, url = payload
                    self._progress_bar["value"] = idx
                    short_url = url if len(url) <= 50 else url[:47] + "..."
                    self._status_label.config(text=f"Đang scan kênh {idx}/{total}: {short_url}")

                elif msg_type == "done":
                    result = payload
                    self._on_scan_done(result)

                elif msg_type == "error":
                    self._log_append(f"❌ Lỗi nghiêm trọng: {payload}")
                    self._start_btn.config(state="normal", text="▶  Bắt đầu Scan")
                    self._status_label.config(text="❌ Scan thất bại")
                    if "Chrome" in payload or "chrome" in payload.lower():
                        messagebox.showerror(
                            "Không tìm thấy Chrome",
                            payload + "\n\nTải Chrome tại: https://www.google.com/chrome",
                        )

        except queue.Empty:
            pass

        self.after(100, self._poll_queue)

    def _on_scan_done(self, result) -> None:
        total = result.total_channels
        success = result.success_channels
        failed = result.failed_channels
        output = result.output_file

        self._progress_bar["value"] = total
        self._status_label.config(text=f"✅ Hoàn thành — {success} thành công / {failed} thất bại / {total} tổng")
        self._log_append(f"\n✅ Scan xong!")
        self._log_append(f"   Tổng kênh  : {total}")
        self._log_append(f"   Thành công : {success}")
        self._log_append(f"   Thất bại   : {failed}")
        if output:
            self._log_append(f"   File kết quả: {Path(output).name}")

        self._start_btn.config(state="normal", text="▶  Bắt đầu Scan")
        self._open_btn.config(state="normal")

        messagebox.showinfo(
            "Scan hoàn thành",
            f"Đã scan {total} kênh\n✅ Thành công: {success}\n❌ Thất bại: {failed}\n\nNhấn 'Mở thư mục kết quả' để xem file CSV.",
        )


# ---------------------------------------------------------------------------

def main() -> None:
    app = ScannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
