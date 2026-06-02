"""마우스 클릭/이동 히트맵 생성기.

선택한 모니터에서 마우스 클릭(및 선택적으로 이동) 위치를 수집하고,
화면 캡처 위에 가우시안 블러 히트맵을 겹쳐 이미지로 저장한다.

단축키: 시작 Ctrl+F1 · 일시정지 Ctrl+F2 · 정지 Ctrl+F3 · 저장 Ctrl+F4
        클릭 취소 Ctrl+Z · 클릭 복원 Ctrl+Y
"""

import os
import threading
import logging
import tempfile
import shutil

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
from scipy.ndimage import gaussian_filter
from pynput import mouse, keyboard
import matplotlib.pyplot as plt
from screeninfo import get_monitors
import pyautogui

class SettingsWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("마우스 히트맵 설정 (Actual Screenshot Size)")

        # 임시 디렉토리
        self.temp_dir = os.path.join(tempfile.gettempdir(), "my_heatmap_app")
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            messagebox.showwarning("경고", f"임시 디렉토리 생성 실패:\n{e}")

        # 로깅 설정
        self.log_file_path = os.path.join(self.temp_dir, "error.log")
        logging.basicConfig(
            filename=self.log_file_path,
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s'
        )
        logging.info("Program started. Logging to: %s", self.log_file_path)

        self.monitors = get_monitors()

        # 설정 변수
        self.alpha_var = tk.DoubleVar(value=0.5)
        self.colormap_alpha_var = tk.DoubleVar(value=1.0)
        self.record_clicks_var = tk.BooleanVar(value=True)
        self.record_movement_var = tk.BooleanVar(value=False)

        # 클릭/이동 데이터
        self.click_positions = []
        self.move_positions = []
        self.lock = threading.Lock()

        # Undo/Redo 스택
        self.undo_stack = []
        self.redo_stack = []

        # GUI 구성
        self.create_widgets()

        # 마우스 리스너
        self.listener = None

        # 키보드 단축키
        self.hotkeys = {
            '<ctrl>+<f1>': self.start_heatmap,
            '<ctrl>+<f2>': self.pause_heatmap,
            '<ctrl>+<f3>': self.stop_heatmap,
            '<ctrl>+<f4>': self.save_heatmap,
            '<ctrl>+z': self.undo_click,
            '<ctrl>+y': self.redo_click
        }

        # 키보드 리스너
        self.keyboard_listener = keyboard.GlobalHotKeys(self.hotkeys)
        try:
            self.keyboard_listener.start()
        except Exception as e:
            logging.error("Keyboard listener start failed: %s", e)
            messagebox.showerror("오류", f"키보드 리스너 시작 실패:\n{e}")

        # 초기 안내
        messagebox.showinfo("안내",
            "본 프로그램은 마우스/키보드 이벤트를 감지하고,\n"
            "화면을 캡처하여 히트맵을 생성합니다.\n"
            "백신/권한 문제 시 예외 설정 또는 관리자 권한 실행을 고려하세요."
        )

    def create_widgets(self):
        tk.Label(self, text="마우스 데이터를 캡처할 모니터:").grid(row=0, column=0, sticky='w')
        self.input_monitor_combo = ttk.Combobox(self, values=self.get_monitor_names(), state='readonly')
        self.input_monitor_combo.current(0)
        self.input_monitor_combo.grid(row=0, column=1, sticky='w')

        tk.Label(self, text="히트맵 투명도 (0.0 ~ 1.0):").grid(row=1, column=0, sticky='w')
        self.alpha_scale = tk.Scale(self, variable=self.alpha_var, from_=0.0, to=1.0,
                                    resolution=0.01, orient=tk.HORIZONTAL)
        self.alpha_scale.grid(row=1, column=1, sticky='we')

        tk.Label(self, text="컬러맵 선택:").grid(row=2, column=0, sticky='w')
        cmap_list = plt.colormaps()
        self.cmap_combo = ttk.Combobox(self, values=cmap_list, state='readonly')
        self.cmap_combo.current(cmap_list.index('jet'))
        self.cmap_combo.grid(row=2, column=1, sticky='w')

        tk.Label(self, text="컬러맵 알파값 (0.0 ~ 1.0):").grid(row=3, column=0, sticky='w')
        self.colormap_alpha_scale = tk.Scale(self, variable=self.colormap_alpha_var,
                                             from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL)
        self.colormap_alpha_scale.grid(row=3, column=1, sticky='we')

        self.record_clicks_check = tk.Checkbutton(self, text="마우스 클릭 기록",
                                                  variable=self.record_clicks_var)
        self.record_clicks_check.grid(row=4, column=0, columnspan=2, sticky='w')

        self.record_movement_check = tk.Checkbutton(self, text="마우스 이동 경로 기록",
                                                    variable=self.record_movement_var)
        self.record_movement_check.grid(row=5, column=0, columnspan=2, sticky='w')

        shortcut_label = tk.Label(self, text=(
            "단축키:\n"
            "히트맵 시작: Ctrl+F1\n"
            "히트맵 일시정지: Ctrl+F2\n"
            "히트맵 정지: Ctrl+F3\n"
            "히트맵 저장: Ctrl+F4\n"
            "Undo(클릭 취소): Ctrl+Z\n"
            "Redo(클릭 복원): Ctrl+Y"
        ))
        shortcut_label.grid(row=6, column=0, columnspan=2, pady=5)

        self.start_button = tk.Button(self, text="히트맵 시작", command=self.start_heatmap)
        self.start_button.grid(row=7, column=0, pady=10)
        self.pause_button = tk.Button(self, text="히트맵 일시정지", command=self.pause_heatmap, state='disabled')
        self.pause_button.grid(row=7, column=1, pady=10)
        self.stop_button = tk.Button(self, text="히트맵 정지", command=self.stop_heatmap, state='disabled')
        self.stop_button.grid(row=8, column=0, pady=10)
        self.save_button = tk.Button(self, text="히트맵 저장", command=self.save_heatmap, state='disabled')
        self.save_button.grid(row=8, column=1, pady=10)

    def get_monitor_names(self):
        return [f"모니터 {idx}: ({m.width}x{m.height}) at ({m.x},{m.y})" for idx, m in enumerate(self.monitors)]

    def start_heatmap(self):
        input_monitor_idx = self.input_monitor_combo.current()
        self.input_monitor = self.monitors[input_monitor_idx]

        if self.listener:
            messagebox.showwarning("경고", "히트맵이 이미 시작되었습니다.")
            return

        if not self.click_positions:
            self.click_positions = []
        if not self.move_positions:
            self.move_positions = []

        self.listener = mouse.Listener(
            on_click=self.on_click if self.record_clicks_var.get() else None,
            on_move=self.on_move if self.record_movement_var.get() else None
        )
        try:
            self.listener.start()
        except Exception as e:
            logging.error("Mouse listener start failed: %s", e)
            messagebox.showerror("오류", f"마우스 리스너 시작 실패:\n{e}")
            return

        self.start_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')
        self.save_button.config(state='normal')

        msg = "마우스 데이터 수집을 시작합니다.\n"
        if self.record_clicks_var.get():
            msg += " - 마우스 클릭 기록 활성화\n"
        if self.record_movement_var.get():
            msg += " - 마우스 이동 경로 기록 활성화"
        messagebox.showinfo("시작", msg)
        logging.info("Heatmap started (clicks=%s, move=%s)",
                     self.record_clicks_var.get(), self.record_movement_var.get())

    def pause_heatmap(self):
        if self.listener:
            try:
                self.listener.stop()
                self.listener.join()
                self.listener = None
                self.start_button.config(state='normal')
                self.pause_button.config(state='disabled')
                self.stop_button.config(state='normal')
                self.save_button.config(state='normal')
                messagebox.showinfo("일시정지", "마우스 데이터 수집을 일시정지했습니다.")
                logging.info("Heatmap paused.")
            except Exception as e:
                logging.error("Pause heatmap failed: %s", e)
                messagebox.showerror("오류", f"일시정지 실패:\n{e}")
        else:
            messagebox.showwarning("경고", "히트맵이 시작되지 않았습니다.")

    def stop_heatmap(self):
        if self.listener:
            try:
                self.listener.stop()
                self.listener.join()
                self.listener = None
            except Exception as e:
                logging.error("Stop heatmap failed: %s", e)

        self.click_positions.clear()
        self.move_positions.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()

        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.save_button.config(state='disabled')

        messagebox.showinfo("정지", "마우스 데이터 수집을 정지하고 데이터를 초기화합니다.")
        logging.info("Heatmap stopped and data cleared.")

    def on_click(self, x, y, button, pressed):
        if pressed:
            if (self.input_monitor.x <= x < self.input_monitor.x + self.input_monitor.width and
               self.input_monitor.y <= y < self.input_monitor.y + self.input_monitor.height):
                relative_x = x - self.input_monitor.x
                relative_y = y - self.input_monitor.y
                with self.lock:
                    self.undo_stack.append((relative_x, relative_y))
                    self.redo_stack.clear()

                    self.click_positions.append((relative_x, relative_y))
                    if len(self.click_positions) > 5000:
                        self.click_positions.pop(0)

    def on_move(self, x, y):
        if (self.input_monitor.x <= x < self.input_monitor.x + self.input_monitor.width and
           self.input_monitor.y <= y < self.input_monitor.y + self.input_monitor.height):
            relative_x = x - self.input_monitor.x
            relative_y = y - self.input_monitor.y
            with self.lock:
                self.move_positions.append((relative_x, relative_y))
                if len(self.move_positions) > 5000:
                    self.move_positions.pop(0)

    def undo_click(self):
        with self.lock:
            if self.undo_stack:
                last_click = self.undo_stack.pop()
                self.redo_stack.append(last_click)
                for i in range(len(self.click_positions) - 1, -1, -1):
                    if self.click_positions[i] == last_click:
                        self.click_positions.pop(i)
                        break

    def redo_click(self):
        with self.lock:
            if self.redo_stack:
                redo_item = self.redo_stack.pop()
                self.undo_stack.append(redo_item)
                self.click_positions.append(redo_item)
                if len(self.click_positions) > 5000:
                    self.click_positions.pop(0)

    def save_heatmap(self):
        with self.lock:
            if not self.click_positions and not self.move_positions:
                messagebox.showwarning("경고", "저장할 히트맵 데이터가 없습니다.")
                return

        # (핵심 변경) 먼저 screenshot 찍기 -> 실제 크기 얻기
        bbox = (
            self.input_monitor.x,
            self.input_monitor.y,
            self.input_monitor.x + self.input_monitor.width,
            self.input_monitor.y + self.input_monitor.height
        )
        screenshot = pyautogui.screenshot(region=bbox)
        screenshot = screenshot.convert('RGBA')
        actual_w, actual_h = screenshot.size  # 실제 스크린샷 픽셀 크기

        # 그 다음 heatmap_data도 (actual_h, actual_w)로 생성
        with self.lock:
            heatmap_data = np.zeros((actual_h, actual_w), dtype=np.float32)

            # 클릭 누적
            if self.record_clicks_var.get():
                for pos in self.click_positions:
                    x, y = int(pos[0]), int(pos[1])
                    # x, y 범위 체크 (actual_w, actual_h)
                    if 0 <= x < actual_w and 0 <= y < actual_h:
                        heatmap_data[y, x] += 1

            # 이동 누적
            if self.record_movement_var.get():
                for pos in self.move_positions:
                    x, y = int(pos[0]), int(pos[1])
                    if 0 <= x < actual_w and 0 <= y < actual_h:
                        heatmap_data[y, x] += 0.2

            # 가우시안 블러
            heatmap_blurred = gaussian_filter(heatmap_data, sigma=30)
            if np.max(heatmap_blurred) > 0:
                heatmap_normalized = heatmap_blurred / np.max(heatmap_blurred)
            else:
                heatmap_normalized = heatmap_blurred

            cmap = plt.get_cmap(self.cmap_combo.get())
            heatmap_colored = cmap(heatmap_normalized)

            user_alpha = self.colormap_alpha_var.get()
            heatmap_colored[..., 3] = user_alpha

            heatmap_colored = (heatmap_colored * 255).astype(np.uint8)
            heatmap_image = Image.fromarray(heatmap_colored, mode='RGBA')

        # 크기 동일: screenshot.size == heatmap_image.size
        # alpha_composite 가능
        try:
            combined_image = Image.alpha_composite(screenshot, heatmap_image)
        except Exception as e:
            logging.error("alpha_composite failed: %s", e)
            messagebox.showerror("오류", f"히트맵 합성 중 오류:\n{e}")
            return

        try:
            file = filedialog.asksaveasfile(mode='wb',
                defaultextension='.png',
                filetypes=[('PNG files', '*.png'),
                           ('JPEG files', '*.jpg'),
                           ('BMP files', '*.bmp'),
                           ('All files', '*.*')],
                title='히트맵 이미지 저장'
            )
            if file:
                combined_image.save(file, format='PNG')
                file_name = file.name
                file.close()
                messagebox.showinfo("저장 완료", f"히트맵 이미지가 저장되었습니다:\n{file_name}")
                logging.info("Heatmap saved to: %s", file_name)
            else:
                logging.info("Save canceled by user.")
        except Exception as e:
            logging.error("Save heatmap failed: %s", e)
            messagebox.showerror("오류", f"이미지 저장에 실패했습니다.\n{e}")

    def on_closing(self):
        self.stop_heatmap()
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                self.keyboard_listener.join()
            except Exception as e:
                logging.error("Keyboard listener stop failed: %s", e)
        self.destroy()

        # temp 디렉터리 정리
        try:
            if os.path.isdir(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logging.info("Temporary directory removed: %s", self.temp_dir)
        except Exception as e:
            logging.warning("Failed to remove temp directory (%s): %s",
                            self.temp_dir, e)

def main():
    root = SettingsWindow()
    root.protocol("WM_DELETE_WINDOW", root.on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
