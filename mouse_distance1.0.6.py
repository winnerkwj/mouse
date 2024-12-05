import tkinter as tk
import math

class CanvasObject:
    """캔버스 객체의 기본 클래스."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.id = None

    def delete(self):
        """캔버스 객체 삭제"""
        if self.id:
            self.canvas.delete(self.id)

    def move(self, dx, dy):
        """객체 이동 (기본 구현은 없음)"""
        pass

    def get_coords(self):
        """객체의 현재 좌표를 반환 (기본 구현은 없음)"""
        return ()

class CanvasPoint(CanvasObject):
    """캔버스에서 점을 나타내는 클래스."""
    def __init__(self, canvas, x, y, color='red'):
        super().__init__(canvas)
        self.x = x
        self.y = y
        self.color = color
        self.draw()
        self.canvas.tag_bind(self.id, '<B1-Motion>', self.on_drag)
        self.canvas.tag_bind(self.id, '<Button-1>', self.on_click)

    def draw(self):
        """캔버스에 점 그리기"""
        self.id = self.canvas.create_oval(
            self.x - 5, self.y - 5, self.x + 5, self.y + 5,
            fill=self.color, outline=self.color
        )

    def move(self, dx, dy):
        """점 이동"""
        self.x += dx
        self.y += dy
        self.canvas.coords(self.id, self.x - 5, self.y - 5, self.x + 5, self.y + 5)
    
    def on_drag(self, event):
        """점 드래그 이벤트 처리"""
        dx = event.x - self.x
        dy = event.y - self.y
        self.move(dx, dy)

    def on_click(self, event):
        """점 클릭 이벤트 처리"""
        # 클릭 시 선택된 점을 하이라이트 (기본 구현은 없음)
        pass

    def get_coords(self):
        """점의 좌표 반환"""
        return (self.x, self.y)

class CanvasLine(CanvasObject):
    """캔버스에서 두 점 사이의 선을 나타내는 클래스."""
    def __init__(self, canvas, x1, y1, x2, y2, color='blue'):
        super().__init__(canvas)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.draw()
        self.canvas.tag_bind(self.id, '<B1-Motion>', self.on_drag)
        self.canvas.tag_bind(self.id, '<Button-1>', self.on_click)

    def draw(self):
        """캔버스에 선 그리기"""
        self.id = self.canvas.create_line(
            self.x1, self.y1, self.x2, self.y2,
            fill=self.color, width=2
        )

    def move(self, dx, dy):
        """선 이동"""
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy
        self.canvas.coords(self.id, self.x1, self.y1, self.x2, self.y2)

    def on_drag(self, event):
        """선 드래그 이벤트 처리"""
        dx = event.x - self.x1
        dy = event.y - self.y1
        self.move(dx, dy)

    def on_click(self, event):
        """선 클릭 이벤트 처리"""
        # 클릭 시 선의 상태를 관리 (기본 구현은 없음)
        pass

    def get_coords(self):
        """선의 좌표 반환"""
        return (self.x1, self.y1, self.x2, self.y2)

class CanvasText(CanvasObject):
    """캔버스에 텍스트를 나타내는 클래스."""
    def __init__(self, canvas, x, y, text):
        super().__init__(canvas)
        self.x = x
        self.y = y
        self.text = text
        self.draw()

    def draw(self):
        """캔버스에 텍스트 그리기"""
        self.id = self.canvas.create_text(
            self.x, self.y, text=self.text, fill='black', font=('Arial', 12)
        )

    def move(self, dx, dy):
        """텍스트 이동"""
        self.x += dx
        self.y += dy
        self.canvas.coords(self.id, self.x, self.y)

    def get_coords(self):
        """텍스트의 좌표 반환"""
        return (self.x, self.y)

class DistanceCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Distance Calculator")

        # 메인 윈도우를 매우 투명하게 설정
        self.root.attributes('-alpha', 0.1)
        self.root.geometry("+300+300")  # 초기 위치 설정

        # 제어 버튼을 위한 완전 불투명한 Toplevel 창 생성
        self.control_window = tk.Toplevel(self.root)
        self.control_window.title("Controls")
        self.control_window.geometry("200x400")
        self.control_window.attributes('-alpha', 1.0)  # 제어 창은 완전 불투명

        # 캔버스 생성 (완전 불투명한 배경)
        self.canvas_width = 500
        self.canvas_height = 500
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="#D3D3D3")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 클릭한 점 저장 및 작업 스택 초기화
        self.points = []
        self.actions = []
        self.redo_stack = []

        # 제어 위젯 초기화
        self.create_controls()

        # 캔버스 클릭 이벤트 바인딩
        self.canvas.bind("<Button-1>", self.on_click)

        # 초기 DPI 계산
        self.dpi = None
        self.pixels_per_mm = None
        self.update_dpi()

    def create_controls(self):
        """제어 버튼 및 입력창을 생성하는 메서드"""
        frame = tk.Frame(self.control_window)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 초기화 버튼
        self.reset_button = tk.Button(frame, text="Reset", command=self.reset)
        self.reset_button.pack(side=tk.TOP, pady=5)

        # Undo 버튼
        self.undo_button = tk.Button(frame, text="Undo", command=self.undo)
        self.undo_button.pack(side=tk.TOP, pady=5)

        # Redo 버튼
        self.redo_button = tk.Button(frame, text="Redo", command=self.redo)
        self.redo_button.pack(side=tk.TOP, pady=5)

        # 캔버스 크기 입력창
        tk.Label(frame, text="Canvas Width").pack()
        self.width_entry = tk.Entry(frame, width=10)
        self.width_entry.insert(0, str(self.canvas_width))
        self.width_entry.pack(pady=5)

        tk.Label(frame, text="Canvas Height").pack()
        self.height_entry = tk.Entry(frame, width=10)
        self.height_entry.insert(0, str(self.canvas_height))
        self.height_entry.pack(pady=5)

        self.resize_button = tk.Button(frame, text="Resize Canvas", command=self.resize_canvas)
        self.resize_button.pack(side=tk.TOP, pady=5)

        # 모니터 해상도 및 크기 입력창
        tk.Label(frame, text="Screen Width").pack()
        self.screen_width_entry = tk.Entry(frame, width=10)
        self.screen_width_entry.insert(0, "1920")
        self.screen_width_entry.pack(pady=5)

        tk.Label(frame, text="Screen Height").pack()
        self.screen_height_entry = tk.Entry(frame, width=10)
        self.screen_height_entry.insert(0, "1080")
        self.screen_height_entry.pack(pady=5)

        tk.Label(frame, text="Screen Size (inches)").pack()
        self.screen_size_entry = tk.Entry(frame, width=10)
        self.screen_size_entry.insert(0, "24")
        self.screen_size_entry.pack(pady=5)

        self.update_dpi_button = tk.Button(frame, text="Update DPI", command=self.update_dpi)
        self.update_dpi_button.pack(side=tk.TOP, pady=5)

    def update_dpi(self):
        """사용자가 입력한 해상도와 모니터 크기를 바탕으로 DPI를 업데이트"""
        try:
            screen_width = int(self.screen_width_entry.get())
            screen_height = int(self.screen_height_entry.get())
            screen_size = float(self.screen_size_entry.get())

            diagonal_pixels = math.sqrt(screen_width ** 2 + screen_height ** 2)
            self.dpi = diagonal_pixels / screen_size
            self.mm_per_inch = 25.4
            self.pixels_per_mm = self.dpi / self.mm_per_inch

        except ValueError:
            print("화면 해상도 또는 크기 입력이 잘못되었습니다.")

    def reset(self):
        """캔버스 및 상태 초기화"""
        self.points = []
        self.actions = []
        self.redo_stack = []
        self.canvas.delete("all")
        self.close_result_window()

    def resize_canvas(self):
        """캔버스 크기 조절"""
        try:
            new_width = int(self.width_entry.get())
            new_height = int(self.height_entry.get())
            self.canvas.config(width=new_width, height=new_height)
        except ValueError:
            print("잘못된 크기 입력입니다. 정수를 입력해 주세요.")

    def on_click(self, event):
        """캔버스 클릭 이벤트 처리"""
        if len(self.points) < 2:
            # 새 점 추가
            point = CanvasPoint(self.canvas, event.x, event.y)
            self.points.append(point)
            self.actions.append(("point", point))
            self.redo_stack.clear()

            # 두 점이 클릭되면 거리 계산 및 결과 표시
            if len(self.points) == 2:
                self.calculate_distance()
        else:
            # 선을 클릭하면, 이미 존재하는 선을 선택하거나 이동
            for obj in self.canvas.find_all():
                tags = self.canvas.gettags(obj)
                if 'line' in tags:
                    self.canvas.tag_bind(obj, '<Button-1>', self.on_line_click)

    def on_line_click(self, event):
        """선 클릭 이벤트 처리"""
        # 이 이벤트 핸들러에서 선의 시작점 및 끝점을 확인하고, 이동 상태를 관리합니다.
        pass

    def calculate_distance(self):
        """두 점 사이의 거리 계산 및 결과 표시"""
        x1, y1 = self.points[0].get_coords()
        x2, y2 = self.points[1].get_coords()

        # 거리 계산 (픽셀 단위)
        distance_pixels = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # 픽셀을 미리미터로 변환
        if self.pixels_per_mm:
            distance_mm = distance_pixels / self.pixels_per_mm
            result_text = f"거리: {distance_mm:.2f} mm (점: ({x1}, {y1}) 및 ({x2}, {y2}))"
        else:
            result_text = f"거리: {distance_pixels:.2f} 픽셀 (점: ({x1}, {y1}) 및 ({x2}, {y2}))"

        # 두 점을 잇는 선 그리기
        line = CanvasLine(self.canvas, x1, y1, x2, y2)
        self.actions.append(("line", line))
        
        # 선 중간에 결과 텍스트 추가
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        CanvasText(self.canvas, mid_x, mid_y, result_text)
        
        self.points = []

    def show_result(self, result_text):
        """결과를 새로운 Toplevel 창에 리스트 형태로 표시"""
        if not hasattr(self, 'result_window') or not self.result_window.winfo_exists():
            self.result_window = tk.Toplevel(self.root)
            self.result_window.title("Calculation Results")
            self.result_listbox = tk.Listbox(self.result_window, width=60, height=20)
            self.result_listbox.pack(padx=10, pady=10)
        
        self.result_listbox.insert(tk.END, result_text)

    def close_result_window(self):
        """현재 열린 결과 창을 닫기"""
        if hasattr(self, 'result_window') and self.result_window.winfo_exists():
            self.result_window.destroy()
            del self.result_window

    def undo(self):
        """마지막 작업 취소"""
        if not self.actions:
            return

        last_action = self.actions.pop()
        self.redo_stack.append(last_action)

        if last_action[0] == "point":
            last_action[1].delete()
        elif last_action[0] == "line":
            last_action[1].delete()
        elif last_action[0] == "text":
            last_action[1].delete()

    def redo(self):
        """마지막으로 취소한 작업 다시 수행"""
        if not self.redo_stack:
            return

        last_action = self.redo_stack.pop()
        self.actions.append(last_action)

        if last_action[0] == "point":
            CanvasPoint(self.canvas, last_action[1].x, last_action[1].y, last_action[1].color)
        elif last_action[0] == "line":
            CanvasLine(self.canvas, last_action[1].x1, last_action[1].y1, last_action[1].x2, last_action[1].y2, last_action[1].color)
        elif last_action[0] == "text":
            CanvasText(self.canvas, last_action[1].x, last_action[1].y, last_action[1].text)

if __name__ == "__main__":
    root = tk.Tk()
    app = DistanceCalculator(root)
    root.mainloop()
