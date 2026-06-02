"""포그라운드 창의 갱신 빈도를 대략적으로 표시하는 모니터.

주의: 실제 렌더링 프레임이 아니라 측정 루프의 반복 횟수를 세는 근사치다.
Windows 탐색기(explorer.exe)가 포그라운드일 때는 측정을 건너뛴다.
"""

import time
import threading
import tkinter as tk

import win32gui
import win32process
import psutil

POLL_INTERVAL = 0.1   # 측정 루프 주기(초)
REPORT_PERIOD = 1.0   # 표시 갱신 주기(초)


class FPSMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("FPS Monitor")

        self.start_button = tk.Button(root, text="Start", command=self.start_monitoring)
        self.start_button.pack()
        self.stop_button = tk.Button(root, text="Stop", command=self.stop_monitoring)
        self.stop_button.pack()
        self.label = tk.Label(root, text="FPS: N/A")
        self.label.pack()

        self.monitoring = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            # 데몬 스레드로 두어 창을 닫으면 함께 종료되게 한다.
            threading.Thread(target=self.monitor_fps, daemon=True).start()

    def stop_monitoring(self):
        self.monitoring = False

    def get_foreground_process_name(self):
        """포그라운드 창 프로세스 이름(소문자). 알 수 없으면 빈 문자열."""
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            return psutil.Process(pid).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            return ""

    def _set_label(self, text):
        # 백그라운드 스레드에서 호출되므로 UI 갱신은 메인 스레드로 넘긴다.
        self.root.after(0, lambda: self.label.config(text=text))

    def monitor_fps(self):
        prev_time = time.time()
        frame_count = 0
        while self.monitoring:
            if "explorer.exe" in self.get_foreground_process_name():
                time.sleep(0.5)
                continue

            frame_count += 1
            current_time = time.time()
            elapsed = current_time - prev_time
            if elapsed >= REPORT_PERIOD:
                self._set_label(f"FPS: {frame_count / elapsed:.2f}")
                frame_count = 0
                prev_time = current_time  # 측정에 쓴 타임스탬프를 그대로 재사용(원본과 동일, 드리프트 없음)
            time.sleep(POLL_INTERVAL)

    def on_closing(self):
        self.monitoring = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FPSMonitor(root)
    root.mainloop()
