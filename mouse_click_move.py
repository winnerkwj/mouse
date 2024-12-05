import threading
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
from scipy.ndimage import gaussian_filter
from pynput import mouse, keyboard
import matplotlib.pyplot as plt
from screeninfo import get_monitors
import pyautogui  # 화면 캡처를 위한 모듈

class SettingsWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("마우스 히트맵 설정")

        self.monitors = get_monitors()

        # 설정 변수들
        self.input_monitor_var = tk.IntVar(value=0)
        self.alpha_var = tk.DoubleVar(value=0.5)
        self.cmap_var = tk.StringVar(value='jet')
        self.colormap_alpha_var = tk.DoubleVar(value=1.0)  # 컬러맵 알파값 변수
        self.record_clicks_var = tk.BooleanVar(value=True)  # 마우스 클릭 기록 여부
        self.record_movement_var = tk.BooleanVar(value=False)  # 마우스 이동 기록 여부

        # 클릭 위치 및 이동 위치 데이터와 락 객체
        self.click_positions = []
        self.move_positions = []  # 마우스 이동 위치를 저장할 리스트
        self.lock = threading.Lock()

        # GUI 구성
        self.create_widgets()

        # 마우스 리스너
        self.listener = None

        # 키보드 핫키 설정
        self.hotkeys = {
            '<ctrl>+<f1>': self.start_heatmap,
            '<ctrl>+<f2>': self.pause_heatmap,
            '<ctrl>+<f3>': self.stop_heatmap,
            '<ctrl>+<f4>': self.save_heatmap
        }

        # 키보드 리스너 시작
        self.keyboard_listener = keyboard.GlobalHotKeys(self.hotkeys)
        self.keyboard_listener.start()

    def create_widgets(self):
        # 입력 모니터 선택
        tk.Label(self, text="마우스 데이터를 캡처할 모니터:").grid(row=0, column=0, sticky='w')
        self.input_monitor_combo = ttk.Combobox(self, values=self.get_monitor_names(), state='readonly')
        self.input_monitor_combo.current(0)
        self.input_monitor_combo.grid(row=0, column=1, sticky='w')

        # 투명도 설정
        tk.Label(self, text="히트맵 투명도 (0.0 ~ 1.0):").grid(row=1, column=0, sticky='w')
        self.alpha_scale = tk.Scale(self, variable=self.alpha_var, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL)
        self.alpha_scale.grid(row=1, column=1, sticky='we')

        # 컬러맵 선택
        tk.Label(self, text="컬러맵 선택:").grid(row=2, column=0, sticky='w')
        cmap_list = plt.colormaps()
        self.cmap_combo = ttk.Combobox(self, values=cmap_list, state='readonly')
        self.cmap_combo.current(cmap_list.index('jet'))
        self.cmap_combo.grid(row=2, column=1, sticky='w')

        # 컬러맵 알파값 설정
        tk.Label(self, text="컬러맵 알파값 (0.0 ~ 1.0):").grid(row=3, column=0, sticky='w')
        self.colormap_alpha_scale = tk.Scale(
            self,
            variable=self.colormap_alpha_var,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient=tk.HORIZONTAL
        )
        self.colormap_alpha_scale.grid(row=3, column=1, sticky='we')

        # 마우스 클릭 기록 체크박스 추가
        self.record_clicks_check = tk.Checkbutton(
            self,
            text="마우스 클릭 기록",
            variable=self.record_clicks_var
        )
        self.record_clicks_check.grid(row=4, column=0, columnspan=2, sticky='w')

        # 마우스 이동 경로 기록 체크박스 추가
        self.record_movement_check = tk.Checkbutton(
            self,
            text="마우스 이동 경로 기록",
            variable=self.record_movement_var
        )
        self.record_movement_check.grid(row=5, column=0, columnspan=2, sticky='w')

        # 단축키 정보 표시
        shortcut_label = tk.Label(self, text="단축키 정보:\n"
                                             "히트맵 시작: Ctrl+F1\n"
                                             "히트맵 일시정지: Ctrl+F2\n"
                                             "히트맵 정지: Ctrl+F3\n"
                                             "히트맵 저장: Ctrl+F4")
        shortcut_label.grid(row=6, column=0, columnspan=2, pady=5)

        # 시작 버튼
        self.start_button = tk.Button(self, text="히트맵 시작", command=self.start_heatmap)
        self.start_button.grid(row=7, column=0, pady=10)

        # 일시정지 버튼
        self.pause_button = tk.Button(self, text="히트맵 일시정지", command=self.pause_heatmap, state='disabled')
        self.pause_button.grid(row=7, column=1, pady=10)

        # 정지 버튼
        self.stop_button = tk.Button(self, text="히트맵 정지", command=self.stop_heatmap, state='disabled')
        self.stop_button.grid(row=8, column=0, pady=10)

        # 저장 버튼
        self.save_button = tk.Button(self, text="히트맵 저장", command=self.save_heatmap, state='disabled')
        self.save_button.grid(row=8, column=1, pady=10)

    def get_monitor_names(self):
        return [f"모니터 {idx}: ({m.width}x{m.height}) at ({m.x},{m.y})" for idx, m in enumerate(self.monitors)]

    def start_heatmap(self):
        input_monitor_idx = self.input_monitor_combo.current()

        self.input_monitor = self.monitors[input_monitor_idx]

        # 마우스 리스너가 이미 실행 중인 경우 중복 실행 방지
        if self.listener:
            messagebox.showwarning("경고", "히트맵이 이미 시작되었습니다.")
            return

        # 클릭 및 이동 위치 데이터 초기화 (정지가 아닌 경우 기존 데이터 유지)
        if not self.click_positions:
            self.click_positions = []
        if not self.move_positions:
            self.move_positions = []

        # 마우스 리스너 시작
        self.listener = mouse.Listener(
            on_click=self.on_click if self.record_clicks_var.get() else None,
            on_move=self.on_move if self.record_movement_var.get() else None
        )
        self.listener.start()

        # 버튼 상태 변경
        self.start_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')
        self.save_button.config(state='normal')

        message = "마우스 데이터 수집을 시작합니다.\n"
        if self.record_clicks_var.get():
            message += " - 마우스 클릭 기록 활성화\n"
        if self.record_movement_var.get():
            message += " - 마우스 이동 경로 기록 활성화"
        messagebox.showinfo("시작", message)

    def pause_heatmap(self):
        if self.listener:
            self.listener.stop()
            self.listener.join()
            self.listener = None

            # 버튼 상태 변경
            self.start_button.config(state='normal')
            self.pause_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.save_button.config(state='normal')

            messagebox.showinfo("일시정지", "마우스 데이터 수집을 일시정지했습니다.")
        else:
            messagebox.showwarning("경고", "히트맵이 시작되지 않았습니다.")

    def stop_heatmap(self):
        # 마우스 리스너 중지
        if self.listener:
            self.listener.stop()
            self.listener.join()
            self.listener = None

        # 클릭 및 이동 데이터 초기화
        self.click_positions = []
        self.move_positions = []

        # 버튼 상태 변경
        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.save_button.config(state='disabled')

        messagebox.showinfo("정지", "마우스 데이터 수집을 정지하고 데이터를 초기화합니다.")

    def on_click(self, x, y, button, pressed):
        if pressed:
            if self.input_monitor.x <= x < self.input_monitor.x + self.input_monitor.width and \
               self.input_monitor.y <= y < self.input_monitor.y + self.input_monitor.height:
                relative_x = x - self.input_monitor.x
                relative_y = y - self.input_monitor.y
                with self.lock:
                    self.click_positions.append((relative_x, relative_y))
                    # 클릭 데이터 제한 (예: 최대 1000개)
                    if len(self.click_positions) > 1000:
                        self.click_positions.pop(0)

    def on_move(self, x, y):
        if self.input_monitor.x <= x < self.input_monitor.x + self.input_monitor.width and \
           self.input_monitor.y <= y < self.input_monitor.y + self.input_monitor.height:
            relative_x = x - self.input_monitor.x
            relative_y = y - self.input_monitor.y
            with self.lock:
                self.move_positions.append((relative_x, relative_y))
                # 이동 데이터 제한 (예: 최대 5000개)
                if len(self.move_positions) > 5000:
                    self.move_positions.pop(0)

    def save_heatmap(self):
        with self.lock:
            if not self.click_positions and not self.move_positions:
                messagebox.showwarning("경고", "저장할 히트맵 데이터가 없습니다.")
                return

            # 히트맵 생성
            screen_width = self.input_monitor.width
            screen_height = self.input_monitor.height

            # 히트맵 데이터 생성
            heatmap_data = np.zeros((screen_height, screen_width), dtype=np.float32)

            # 클릭 위치 데이터 추가
            if self.record_clicks_var.get():
                for pos in self.click_positions:
                    x, y = int(pos[0]), int(pos[1])
                    if 0 <= x < screen_width and 0 <= y < screen_height:
                        heatmap_data[y, x] += 1

            # 마우스 이동 위치 데이터 추가
            if self.record_movement_var.get():
                for pos in self.move_positions:
                    x, y = int(pos[0]), int(pos[1])
                    if 0 <= x < screen_width and 0 <= y < screen_height:
                        heatmap_data[y, x] += 0.2  # 이동 위치의 가중치를 낮게 설정

            # 가우시안 블러 적용
            heatmap_blurred = gaussian_filter(heatmap_data, sigma=30)

            # 히트맵 정규화
            if np.max(heatmap_blurred) > 0:
                heatmap_normalized = heatmap_blurred / np.max(heatmap_blurred)
            else:
                heatmap_normalized = heatmap_blurred

            # 컬러맵 적용하여 이미지 생성 (알파 채널 포함)
            cmap = plt.get_cmap(self.cmap_combo.get())
            heatmap_colored = cmap(heatmap_normalized)

            # 사용자가 설정한 알파값 가져오기
            user_alpha = self.colormap_alpha_var.get()

            # 알파 채널을 사용자가 지정한 값으로 설정
            heatmap_colored[..., 3] = user_alpha

            heatmap_colored = (heatmap_colored * 255).astype(np.uint8)
            heatmap_image = Image.fromarray(heatmap_colored, mode='RGBA')

            # 입력 모니터 화면 캡처
            bbox = (
                self.input_monitor.x,
                self.input_monitor.y,
                self.input_monitor.x + self.input_monitor.width,
                self.input_monitor.y + self.input_monitor.height
            )
            screenshot = pyautogui.screenshot(region=bbox)

            # 히트맵 이미지를 화면 캡처에 오버레이
            combined_image = Image.alpha_composite(
                screenshot.convert('RGBA'),
                heatmap_image
            )

        # 저장할 파일 경로 선택
        file_path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG files', '*.png'), ('JPEG files', '*.jpg'), ('All files', '*.*')],
            title='히트맵 이미지 저장'
        )
        if file_path:
            combined_image.save(file_path)
            messagebox.showinfo("저장 완료", f"히트맵 이미지가 저장되었습니다:\n{file_path}")

    def on_closing(self):
        self.stop_heatmap()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener.join()
            self.keyboard_listener = None
        self.destroy()

def main():
    root = SettingsWindow()
    root.protocol("WM_DELETE_WINDOW", root.on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
