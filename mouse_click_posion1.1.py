import sys
import time
import threading
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from scipy.ndimage import gaussian_filter
from pynput import mouse
import ctypes
import matplotlib.pyplot as plt
from screeninfo import get_monitors

class HeatmapWindow(tk.Tk):
    def __init__(self, monitor):
        super().__init__()
        self.title('마우스 클릭 히트맵')
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.5)
        self.attributes('-transparentcolor', 'white')
        self.overrideredirect(True)  # 윈도우 테두리 제거

        # 윈도우 위치 및 크기 설정 (오른쪽 모니터)
        self.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")

        # 마우스 클릭 통과 설정
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE = -20
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            -20,
            extended_style | 0x00000020  # WS_EX_TRANSPARENT = 0x20
        )

        self.click_positions = []
        self.screen_width = monitor.width
        self.screen_height = monitor.height

        # 캔버스 생성
        self.canvas = tk.Canvas(self, width=self.screen_width, height=self.screen_height)
        self.canvas.pack()

        # 업데이트 쓰레드 시작
        self.update_thread = threading.Thread(target=self.update_heatmap)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_heatmap(self):
        while True:
            if self.click_positions:
                # 히트맵 데이터 생성
                heatmap_data = np.zeros((self.screen_height, self.screen_width), dtype=np.float32)
                for pos in self.click_positions:
                    x, y = int(pos[0]), int(pos[1])
                    if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
                        heatmap_data[y, x] += 1

                # 가우시안 블러 적용
                heatmap_blurred = gaussian_filter(heatmap_data, sigma=30)

                # 히트맵 정규화
                if np.max(heatmap_blurred) > 0:
                    heatmap_normalized = heatmap_blurred / np.max(heatmap_blurred)
                else:
                    heatmap_normalized = heatmap_blurred

                # 컬러맵 적용하여 이미지 생성
                cmap = plt.get_cmap('jet')
                heatmap_colored = (cmap(heatmap_normalized) * 255).astype(np.uint8)
                heatmap_image = Image.fromarray(heatmap_colored)

                # 이미지 변환하여 캔버스에 표시
                heatmap_photo = ImageTk.PhotoImage(heatmap_image)
                self.canvas.create_image(0, 0, image=heatmap_photo, anchor='nw')

                # 메모리 누수 방지
                self.canvas.image = heatmap_photo

            time.sleep(0.1)  # 100ms마다 업데이트

def main():
    monitors = sorted(get_monitors(), key=lambda m: m.x)
    if len(monitors) < 2:
        print("두 개 이상의 모니터가 필요합니다.")
        sys.exit()

    left_monitor = monitors[0]
    right_monitor = monitors[1]

    window = HeatmapWindow(right_monitor)

    def on_click(x, y, button, pressed):
        if pressed:
            if left_monitor.x <= x < left_monitor.x + left_monitor.width and \
               left_monitor.y <= y < left_monitor.y + left_monitor.height:
                relative_x = x - left_monitor.x
                relative_y = y - left_monitor.y
                window.click_positions.append((relative_x, relative_y))
                if len(window.click_positions) > 1000:
                    window.click_positions.pop(0)

    listener = mouse.Listener(on_click=on_click)
    listener.start()

    window.mainloop()

if __name__ == '__main__':
    main()
