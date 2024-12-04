import sys
import time
import threading
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from scipy.ndimage import gaussian_filter
from pynput import mouse, keyboard
import ctypes
import matplotlib.pyplot as plt

class HeatmapWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('마우스 클릭 히트맵')
        self.overrideredirect(True)  # 윈도우 프레임 제거
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.attributes('-topmost', True)
        self.lift()

        # 윈도우를 완전히 투명하게 설정
        self.attributes('-alpha', 0.0)

        # 윈도우를 마우스 이벤트가 통과하도록 설정
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        WS_EX_TRANSPARENT = 0x20
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            extended_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        )

        # 레이어드 윈도우 속성 설정 (투명색을 검은색으로 설정)
        LWA_COLORKEY = 0x1
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0x000000, 0, LWA_COLORKEY)

        self.click_positions = []
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        # 캔버스 생성 (배경색을 검은색으로 설정하여 투명색과 일치)
        self.canvas = tk.Canvas(
            self,
            width=self.screen_width,
            height=self.screen_height,
            highlightthickness=0,
            bg='black'  # 투명색과 일치하는 배경색 설정
        )
        self.canvas.pack()

        # 히트맵 이미지를 저장할 변수
        self.heatmap_photo = None

        # 업데이트 쓰레드 시작
        self.update_thread = threading.Thread(target=self.update_heatmap)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_heatmap(self):
        while True:
            try:
                if self.click_positions:
                    # 히트맵 데이터 생성
                    heatmap_data = np.zeros(
                        (self.screen_height, self.screen_width),
                        dtype=np.float32
                    )
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

                    # 컬러맵 적용하여 이미지 생성 (RGBA 모드)
                    cmap = plt.get_cmap('jet')
                    heatmap_colored = (cmap(heatmap_normalized) * 255).astype(np.uint8)
                    heatmap_image = Image.fromarray(heatmap_colored, mode='RGBA')

                    # 히트맵 이미지에 투명도 적용
                    alpha = 128  # 투명도 값 (0-255)
                    heatmap_image.putalpha(alpha)

                    # 이미지 변환하여 캔버스에 표시
                    self.heatmap_photo = ImageTk.PhotoImage(heatmap_image)

                    # 캔버스 초기화 후 이미지 추가
                    self.canvas.delete('heatmap')
                    self.canvas.create_image(0, 0, image=self.heatmap_photo, anchor='nw', tags='heatmap')

                # 업데이트 주기 조절
                time.sleep(0.1)
            except Exception as e:
                print(f"예외 발생: {e}")

    def close(self):
        self.destroy()

def main():
    window = HeatmapWindow()

    # 마우스 클릭 이벤트 핸들러
    def on_click(x, y, button, pressed):
        if pressed:
            window.click_positions.append((x, y))
            # 클릭 데이터 제한 (예: 최대 500개)
            if len(window.click_positions) > 500:
                window.click_positions.pop(0)

    # 마우스 리스너 시작
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    # 키보드 이벤트 핸들러
    def on_press(key):
        if key == keyboard.Key.esc:
            print("프로그램을 종료합니다.")
            mouse_listener.stop()
            window.close()
            return False  # 키보드 리스너 종료

    # 키보드 리스너 시작
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    window.mainloop()

if __name__ == '__main__':
    main()
