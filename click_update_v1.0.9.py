"""마우스 사용량 트래커.

좌/우/휠 클릭 횟수와 마우스 이동 거리·스크롤 거리를 실시간으로 집계하고,
'리셋' 시 결과를 바탕화면에 텍스트 파일로 저장한다.

전역 단축키:
    s : 측정 시작/정지 토글
"""

import os
import math
import datetime
import threading
import tkinter as tk

from pynput.mouse import Listener, Button
from pynput import keyboard

DPI = 96             # 이동 픽셀 -> 물리 거리 환산에 쓰는 화면 DPI
MM_TO_CM = 0.1       # mm -> cm
INCH_TO_MM = 25.4    # inch -> mm
SCROLL_STEP_MM = 15  # 스크롤 한 칸의 추정 이동 거리(mm)


class MouseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("---마우스---")
        self.root.attributes("-topmost", True)

        self.click_counts = {Button.left: 0, Button.right: 0, Button.middle: 0}
        self.total_distance_mm = 0.0
        self.total_scroll_mm = 0.0
        self.last_position = None
        self.is_running = False

        self.setup_ui()

        # 마우스/키보드 리스너는 GUI를 막지 않도록 데몬 스레드에서 돌린다.
        threading.Thread(target=self._run_mouse_listener, daemon=True).start()
        threading.Thread(target=self._run_keyboard_listener, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def setup_ui(self):
        self.left_click_label = tk.Label(self.root, text="좌클릭: 0", font=("Arial", 8))
        self.left_click_label.pack(pady=0)
        self.right_click_label = tk.Label(self.root, text="우클릭: 0", font=("Arial", 8))
        self.right_click_label.pack(pady=0)
        self.middle_click_label = tk.Label(self.root, text="휠 클릭: 0", font=("Arial", 8))
        self.middle_click_label.pack(pady=0)
        self.distance_label = tk.Label(self.root, text="이동 거리: 0.00 cm", font=("Arial", 8))
        self.distance_label.pack(pady=0)
        self.scroll_label = tk.Label(self.root, text="스크롤 거리: 0.00 cm", font=("Arial", 8))
        self.scroll_label.pack(pady=0)
        self.reset_button = tk.Button(self.root, text="리셋", font=("Arial", 8), command=self.reset_counts)
        self.reset_button.pack(pady=10)

    def update_labels(self):
        self.left_click_label.config(text=f"좌클릭: {self.click_counts[Button.left]}")
        self.right_click_label.config(text=f"우클릭: {self.click_counts[Button.right]}")
        self.middle_click_label.config(text=f"휠 클릭: {self.click_counts[Button.middle]}")

    def update_distance_label(self):
        self.distance_label.config(text=f"이동 거리: \n {self.total_distance_mm * MM_TO_CM:.2f} cm")
        self.scroll_label.config(text=f"스크롤 거리: \n {self.total_scroll_mm * MM_TO_CM:.2f} cm")

    def reset_counts(self):
        """결과를 파일로 저장한 뒤 모든 집계를 0으로 되돌린다."""
        self.save_results()
        self.click_counts = {Button.left: 0, Button.right: 0, Button.middle: 0}
        self.total_distance_mm = 0.0
        self.total_scroll_mm = 0.0
        self.last_position = None
        self.is_running = False
        self.update_labels()
        self.update_distance_label()

    def save_results(self):
        """측정 결과를 바탕화면에 타임스탬프 텍스트 파일로 저장한다."""
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"MouseTrackerResults_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        file_path = os.path.join(desktop_path, filename)
        results = (
            f"좌클릭: {self.click_counts[Button.left]}\n"
            f"우클릭: {self.click_counts[Button.right]}\n"
            f"휠 클릭: {self.click_counts[Button.middle]}\n"
            f"이동 거리: {self.total_distance_mm * MM_TO_CM:.2f} cm\n"
            f"스크롤 거리: {self.total_scroll_mm * MM_TO_CM:.2f} cm\n"
        )
        try:
            # 인코딩은 원본 동작과 동일하게 OS 기본값(한국어 Windows=cp949)을 따른다.
            with open(file_path, "w") as file:
                file.write(results)
        except OSError as e:
            # 저장 실패는 조용히 넘기지 않는다.
            print(f"결과 저장 실패: {e}")

    def on_click(self, x, y, button, pressed):
        if self.is_running and pressed:
            self.click_counts[button] += 1
            self.root.after(0, self.update_labels)

    def on_move(self, x, y):
        if not self.is_running:
            return
        if self.last_position is not None:
            distance_pixels = math.hypot(x - self.last_position[0], y - self.last_position[1])
            self.total_distance_mm += distance_pixels / DPI * INCH_TO_MM
        self.last_position = (x, y)
        self.root.after(0, self.update_distance_label)

    def on_scroll(self, x, y, dx, dy):
        if self.is_running:
            self.total_scroll_mm += abs(dy) * SCROLL_STEP_MM
            self.root.after(0, self.update_distance_label)

    def toggle_running(self):
        self.is_running = not self.is_running
        # 키보드 리스너 스레드에서 호출되므로 UI 갱신은 메인 스레드로 넘긴다.
        self.root.after(0, self.update_distance_label)

    def _run_mouse_listener(self):
        with Listener(on_click=self.on_click, on_move=self.on_move, on_scroll=self.on_scroll) as listener:
            listener.join()

    def _run_keyboard_listener(self):
        def on_press(key):
            # 특수키는 key.char 속성이 없으므로 getattr로 안전하게 접근한다.
            if getattr(key, "char", None) == "s":
                self.toggle_running()

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()


if __name__ == "__main__":
    root = tk.Tk()
    app = MouseTrackerApp(root)
    root.mainloop()
