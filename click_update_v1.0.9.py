import tkinter as tk
from pynput.mouse import Listener, Button
from pynput import keyboard
import threading
import math
import os
import datetime

# 상수 정의
DPI = 96  # 마우스의 DPI 설정
MM_TO_CM = 0.1  # 밀리미터를 센티미터로 변환하는 상수

class MouseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("---마우스---")
        self.root.attributes("-topmost", True)  # 윈도우를 항상 위에 표시

        # 클릭 횟수와 이동 거리 초기화
        self.click_counts = {Button.left: 0, Button.right: 0, Button.middle: 0}
        self.total_distance = 0
        self.total_scroll_distance = 0
        self.last_position = None
        # self.new_measurement_distance = 0  # 새로 측정된 이동 거리 초기화
        # self.is_measuring = False  # 새로 측정된 거리 측정 활성화 여부
        self.is_running = False  # 전체 측정 활성화 여부

        # UI 구성 설정
        self.setup_ui()
        
        # 마우스 이벤트 리스너를 별도의 스레드에서 시작
        self.listener_thread = threading.Thread(target=self.start_listener, daemon=True)
        self.listener_thread.start()

        # 전역 키보드 리스너를 별도의 스레드에서 시작
        self.keyboard_listener_thread = threading.Thread(target=self.start_keyboard_listener, daemon=True)
        self.keyboard_listener_thread.start()
        
        # 윈도우 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """UI 요소를 설정하는 함수"""
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

        # self.new_measurement_label = tk.Label(self.root, text="측정 거리: 0.00 cm ", font=("Arial", 12))
        # self.new_measurement_label.pack(pady=1)

        self.reset_button = tk.Button(self.root, text="리셋", font=("Arial", 8), command=self.reset_counts)
        self.reset_button.pack(pady=10)

    def update_labels(self):
        """클릭 횟수 라벨을 업데이트하는 함수"""
        self.left_click_label.config(text=f"좌클릭: {self.click_counts[Button.left]}")
        self.right_click_label.config(text=f"우클릭: {self.click_counts[Button.right]}")
        self.middle_click_label.config(text=f"휠 클릭: {self.click_counts[Button.middle]}")

    def update_distance_label(self):
        """이동 거리 라벨을 업데이트하는 함수"""
        self.distance_label.config(text=f"이동 거리: \n {self.total_distance * MM_TO_CM:.2f} cm")
        self.scroll_label.config(text=f"스크롤 거리: \n {self.total_scroll_distance * MM_TO_CM:.2f} cm")
        # self.new_measurement_label.config(text=f"새로 측정된 거리: \n {self.new_measurement_distance * MM_TO_CM:.2f} cm \n 시작/종료 단축키:s \n 거리측정 단축키 : m ")

    def reset_counts(self):
        """클릭 횟수와 이동 거리 데이터를 초기화하고 결과를 텍스트 파일로 저장하는 함수"""
        # 측정된 결과값 저장
        self.save_results()

        # 데이터 초기화
        self.click_counts = {Button.left: 0, Button.right: 0, Button.middle: 0}
        self.total_distance = 0
        self.total_scroll_distance = 0
        # self.new_measurement_distance = 0  # 새로 측정된 거리도 초기화
        self.last_position = None
        self.is_measuring = False  # 측정 비활성화
        self.is_running = False  # 측정 비활성화
        self.update_labels()
        self.update_distance_label()

    def save_results(self):
        """측정된 결과값을 바탕화면에 텍스트 파일로 저장하는 함수"""
        # 바탕화면 경로 가져오기
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

        # 파일명 생성
        filename = f"MouseTrackerResults_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = os.path.join(desktop_path, filename)

        # 결과값 작성
        results = (
            f"좌클릭: {self.click_counts[Button.left]}\n"
            f"우클릭: {self.click_counts[Button.right]}\n"
            f"휠 클릭: {self.click_counts[Button.middle]}\n"
            f"이동 거리: {self.total_distance * MM_TO_CM:.2f} cm\n"
            f"스크롤 거리: {self.total_scroll_distance * MM_TO_CM:.2f} cm\n"
            # f"새로 측정된 거리: {self.new_measurement_distance * MM_TO_CM:.2f} cm\n"
        )

        # 파일에 기록
        with open(file_path, "w") as file:
            file.write(results)

    def on_click(self, x, y, button, pressed):
        """마우스 클릭 이벤트 처리 함수"""
        if self.is_running:
            if pressed:
                self.click_counts[button] += 1
                self.root.after(0, self.update_labels)

    def on_move(self, x, y):
        """마우스 이동 이벤트 처리 함수"""
        if self.is_running:
            if self.last_position is not None:
                # 두 점 사이의 거리를 계산
                distance_pixels = math.sqrt((x - self.last_position[0]) ** 2 + (y - self.last_position[1]) ** 2)
                # 픽셀 단위 거리를 센티미터로 변환하여 총 거리 누적
                self.total_distance += distance_pixels / DPI * 25.4
                # if self.is_measuring:
                #     self.new_measurement_distance += distance_pixels / DPI * 25.4  # 새로 측정된 거리 누적
            self.last_position = (x, y)
            self.root.after(0, self.update_distance_label)

    def on_scroll(self, x, y, dx, dy):
        """마우스 스크롤 이벤트 처리 함수"""
        if self.is_running:
            # 스크롤 한 번에 해당하는 거리 (필요에 따라 조정 가능)
            scroll_step_mm = 15  
            self.total_scroll_distance += abs(dy) * scroll_step_mm
            self.root.after(0, self.update_distance_label)

    def start_listener(self):
        """마우스 이벤트 리스너를 시작하는 함수"""
        with Listener(on_click=self.on_click, on_move=self.on_move, on_scroll=self.on_scroll) as listener:
            listener.join()

    def on_closing(self):
        """윈도우 닫기 이벤트 처리 함수"""
        self.listener_thread.join(0)  # 리스너 스레드를 정지
        self.root.destroy()

    # def start_new_measurement(self):
    #     """새로운 마우스 이동 거리 측정을 시작하는 함수"""
    #     if self.is_running:
    #         # self.new_measurement_distance = 0  # 새로 측정된 거리 초기화
    #         self.is_measuring = True  # 측정 활성화
    #         self.update_distance_label()

    #  def toggle_measurement(self):
    #     """새로운 측정된 거리 측정을 시작하거나 멈추는 함수"""
    #     if self.is_running:
    #         self.is_measuring = not self.is_measuring  # 측정 활성화/비활성화 토글
    #         self.update_distance_label()

    # def clear_new_measurement(self):
    #     """새로운 측정된 거리를 초기화하는 함수"""
    #     if self.is_running:
    #         self.new_measurement_distance = 0
    #         self.update_distance_label()

    def toggle_running(self):
        """프로그램 시작/정지 토글 함수"""
        self.is_running = not self.is_running  # 실행 상태 토글
        self.update_distance_label()

    def start_keyboard_listener(self):
        """전역 키보드 리스너를 시작하는 함수"""
        def on_press(key):
            try:
                if key.char == 's':
                    self.toggle_running()
                elif key.char == 'm':
                    self.start_new_measurement()
                elif key.char == 'p':
                    self.toggle_measurement()
                elif key.char == 'r':
                    self.clear_new_measurement()
            except AttributeError:
                pass

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

if __name__ == "__main__":
    # Tkinter 루프 시작
    root = tk.Tk()
    app = MouseTrackerApp(root)
    root.mainloop()
