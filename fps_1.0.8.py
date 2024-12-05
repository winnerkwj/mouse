import tkinter as tk
import time
import threading
import win32gui
import win32process
import psutil

# FPS Monitor 클래스 정의
class FPSMonitor:
    def __init__(self, root):
        self.root = root  # tkinter root 윈도우
        self.root.title("FPS Monitor")  # 윈도우 타이틀
        
        # GUI 초기화
        self.start_button = tk.Button(root, text="Start", command=self.start_monitoring)
        self.start_button.pack()
        
        self.stop_button = tk.Button(root, text="Stop", command=self.stop_monitoring)
        self.stop_button.pack()
        
        self.label = tk.Label(root, text="FPS: N/A")
        self.label.pack()
        
        self.monitoring = False  # FPS 모니터링 활성화 상태

    def start_monitoring(self):
        """
        시작 버튼 클릭 시 호출되는 메서드로, 모니터링 상태를 True로 설정하고,
        FPS를 측정하는 스레드를 시작한다.
        """
        if not self.monitoring:
            self.monitoring = True
            self.thread = threading.Thread(target=self.monitor_fps)
            self.thread.start()

    def stop_monitoring(self):
        """
        정지 버튼 클릭 시 호출되는 메서드로, 모니터링 상태를 False로 설정한다.
        """
        self.monitoring = False

    def get_foreground_process(self):
        """
        현재 포그라운드 창의 프로세스를 반환하는 메서드
        """
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid)

    def monitor_fps(self):
        """
        FPS를 측정하는 메서드로, 약 1초 간격으로 FPS를 계산하고 tkinter 라벨에 업데이트한다.
        """
        prev_time = time.time()
        frame_count = 0
        while self.monitoring:
            current_process = self.get_foreground_process()
            if "explorer.exe" in current_process.name().lower():
                # Windows 탐색기일 경우, 측정하지 않음
                time.sleep(0.5)
                continue
            
            frame_count += 1
            current_time = time.time()
            elapsed_time = current_time - prev_time
            
            if elapsed_time >= 1.0:
                fps = frame_count / elapsed_time  # FPS 계산
                self.label.config(text=f"FPS: {fps:.2f}")
                frame_count = 0
                prev_time = current_time
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = FPSMonitor(root)
    root.mainloop()
