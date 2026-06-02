"""두 점 사이의 화면 거리를 mm로 계산하는 도구.

거의 투명한 메인 창 위 캔버스에 두 점을 찍으면 픽셀 거리를 구하고,
입력한 화면 해상도·물리 크기에서 얻은 DPI로 mm 거리로 환산한다.
점/선은 드래그로 옮길 수 있고 Undo/Redo를 지원한다.
"""

import tkinter as tk
import math


class CanvasObject:
    """캔버스 객체의 기본 클래스."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.id = None

    def delete(self):
        if self.id:
            self.canvas.delete(self.id)


class CanvasPoint(CanvasObject):
    """캔버스에서 점을 나타내는 클래스."""
    def __init__(self, canvas, x, y, color='red'):
        super().__init__(canvas)
        self.x = x
        self.y = y
        self.color = color
        self.draw()
        self.canvas.tag_bind(self.id, '<B1-Motion>', self.on_drag)

    def draw(self):
        self.id = self.canvas.create_oval(
            self.x - 5, self.y - 5, self.x + 5, self.y + 5,
            fill=self.color, outline=self.color
        )

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.canvas.coords(self.id, self.x - 5, self.y - 5, self.x + 5, self.y + 5)

    def on_drag(self, event):
        self.move(event.x - self.x, event.y - self.y)

    def get_coords(self):
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

    def draw(self):
        self.id = self.canvas.create_line(
            self.x1, self.y1, self.x2, self.y2,
            fill=self.color, width=2
        )

    def move(self, dx, dy):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy
        self.canvas.coords(self.id, self.x1, self.y1, self.x2, self.y2)

    def on_drag(self, event):
        self.move(event.x - self.x1, event.y - self.y1)


class CanvasText(CanvasObject):
    """캔버스에 결과 텍스트를 나타내는 클래스."""
    def __init__(self, canvas, x, y, text):
        super().__init__(canvas)
        self.x = x
        self.y = y
        self.text = text
        self.draw()

    def draw(self):
        self.id = self.canvas.create_text(
            self.x, self.y, text=self.text, fill='black', font=('Arial', 12)
        )


class DistanceCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Distance Calculator")

        # 메인 창은 거의 투명하게, 컨트롤 창은 불투명하게 둔다.
        self.root.attributes('-alpha', 0.1)
        self.root.geometry("+300+300")

        self.control_window = tk.Toplevel(self.root)
        self.control_window.title("Controls")
        self.control_window.geometry("200x400")
        self.control_window.attributes('-alpha', 1.0)

        self.canvas_width = 500
        self.canvas_height = 500
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="#D3D3D3")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 찍은 점과 작업(undo/redo) 스택
        self.points = []
        self.actions = []
        self.redo_stack = []

        self.create_controls()
        self.canvas.bind("<Button-1>", self.on_click)

        self.dpi = None
        self.pixels_per_mm = None
        self.update_dpi()

    def create_controls(self):
        frame = tk.Frame(self.control_window)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        tk.Button(frame, text="Reset", command=self.reset).pack(side=tk.TOP, pady=5)
        tk.Button(frame, text="Undo", command=self.undo).pack(side=tk.TOP, pady=5)
        tk.Button(frame, text="Redo", command=self.redo).pack(side=tk.TOP, pady=5)

        tk.Label(frame, text="Canvas Width").pack()
        self.width_entry = tk.Entry(frame, width=10)
        self.width_entry.insert(0, str(self.canvas_width))
        self.width_entry.pack(pady=5)

        tk.Label(frame, text="Canvas Height").pack()
        self.height_entry = tk.Entry(frame, width=10)
        self.height_entry.insert(0, str(self.canvas_height))
        self.height_entry.pack(pady=5)

        tk.Button(frame, text="Resize Canvas", command=self.resize_canvas).pack(side=tk.TOP, pady=5)

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

        tk.Button(frame, text="Update DPI", command=self.update_dpi).pack(side=tk.TOP, pady=5)

    def update_dpi(self):
        """입력한 해상도와 물리 크기로 DPI와 mm당 픽셀 수를 계산한다."""
        try:
            screen_width = int(self.screen_width_entry.get())
            screen_height = int(self.screen_height_entry.get())
            screen_size = float(self.screen_size_entry.get())
            diagonal_pixels = math.hypot(screen_width, screen_height)
            self.dpi = diagonal_pixels / screen_size
            self.pixels_per_mm = self.dpi / 25.4
        except (ValueError, ZeroDivisionError):
            print("화면 해상도 또는 크기 입력이 잘못되었습니다.")

    def reset(self):
        """캔버스 및 상태 초기화."""
        self.points = []
        self.actions = []
        self.redo_stack = []
        self.canvas.delete("all")

    def resize_canvas(self):
        try:
            new_width = int(self.width_entry.get())
            new_height = int(self.height_entry.get())
            self.canvas.config(width=new_width, height=new_height)
        except ValueError:
            print("잘못된 크기 입력입니다. 정수를 입력해 주세요.")

    def on_click(self, event):
        if len(self.points) < 2:
            point = CanvasPoint(self.canvas, event.x, event.y)
            self.points.append(point)
            self.actions.append(("point", point))
            self.redo_stack.clear()
            if len(self.points) == 2:
                self.calculate_distance()

    def calculate_distance(self):
        """두 점 사이의 거리를 계산하고 선과 결과 텍스트를 그린다."""
        x1, y1 = self.points[0].get_coords()
        x2, y2 = self.points[1].get_coords()

        distance_pixels = math.hypot(x2 - x1, y2 - y1)
        if self.pixels_per_mm:
            distance_mm = distance_pixels / self.pixels_per_mm
            result_text = f"거리: {distance_mm:.2f} mm (점: ({x1}, {y1}) 및 ({x2}, {y2}))"
        else:
            result_text = f"거리: {distance_pixels:.2f} 픽셀 (점: ({x1}, {y1}) 및 ({x2}, {y2}))"

        line = CanvasLine(self.canvas, x1, y1, x2, y2)
        self.actions.append(("line", line))

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        CanvasText(self.canvas, mid_x, mid_y, result_text)

        self.points = []

    def undo(self):
        """마지막 작업 취소(점/선 모두 캔버스에서 제거)."""
        if not self.actions:
            return
        last_action = self.actions.pop()
        self.redo_stack.append(last_action)
        last_action[1].delete()

    def redo(self):
        """마지막으로 취소한 점/선을 다시 그린다."""
        if not self.redo_stack:
            return
        last_action = self.redo_stack.pop()
        self.actions.append(last_action)
        kind, obj = last_action
        if kind == "point":
            CanvasPoint(self.canvas, obj.x, obj.y, obj.color)
        elif kind == "line":
            CanvasLine(self.canvas, obj.x1, obj.y1, obj.x2, obj.y2, obj.color)


if __name__ == "__main__":
    root = tk.Tk()
    app = DistanceCalculator(root)
    root.mainloop()
