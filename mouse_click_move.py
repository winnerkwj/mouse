import threading
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
import cv2  # OpenCV for video processing

class SettingsWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("마우스 히트맵 생성기")

        # 설정 변수들
        self.alpha_var = tk.DoubleVar(value=0.5)
        self.cmap_var = tk.StringVar(value='jet')
        self.colormap_alpha_var = tk.DoubleVar(value=1.0)  # 컬러맵 알파값 변수

        # 비디오 파일 경로 및 마우스 포인터 템플릿 이미지
        self.video_path = None
        self.template_image = None

        # 마우스 위치 데이터
        self.video_positions = []

        # GUI 구성
        self.create_widgets()

    def create_widgets(self):
        # 투명도 설정
        tk.Label(self, text="히트맵 투명도 (0.0 ~ 1.0):").grid(row=0, column=0, sticky='w')
        self.alpha_scale = tk.Scale(self, variable=self.alpha_var, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL)
        self.alpha_scale.grid(row=0, column=1, sticky='we')

        # 컬러맵 선택
        tk.Label(self, text="컬러맵 선택:").grid(row=1, column=0, sticky='w')
        cmap_list = plt.colormaps()
        self.cmap_combo = ttk.Combobox(self, values=cmap_list, state='readonly')
        self.cmap_combo.current(cmap_list.index('jet'))
        self.cmap_combo.grid(row=1, column=1, sticky='w')

        # 컬러맵 알파값 설정
        tk.Label(self, text="컬러맵 알파값 (0.0 ~ 1.0):").grid(row=2, column=0, sticky='w')
        self.colormap_alpha_scale = tk.Scale(
            self,
            variable=self.colormap_alpha_var,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient=tk.HORIZONTAL
        )
        self.colormap_alpha_scale.grid(row=2, column=1, sticky='we')

        # 마우스 포인터 템플릿 선택
        tk.Label(self, text="마우스 포인터 템플릿 이미지:").grid(row=3, column=0, sticky='w')
        self.template_button = tk.Button(self, text="템플릿 선택", command=self.select_template)
        self.template_button.grid(row=3, column=1, sticky='w')

        # 비디오 파일 선택 및 처리 버튼
        self.process_video_button = tk.Button(self, text="비디오 처리", command=self.process_video)
        self.process_video_button.grid(row=4, column=0, columnspan=2, pady=10)

    def select_template(self):
        template_path = filedialog.askopenfilename(
            title="마우스 포인터 템플릿 이미지 선택",
            filetypes=[('Image Files', '*.png;*.jpg;*.jpeg;*.bmp')]
        )
        if not template_path:
            return
        self.template_image = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if self.template_image is None:
            messagebox.showerror("오류", "템플릿 이미지를 불러올 수 없습니다.")

    def process_video(self):
        video_path = filedialog.askopenfilename(
            title="비디오 파일 선택",
            filetypes=[('Video Files', '*.mp4;*.avi;*.mov;*.mkv')]
        )
        if not video_path:
            return
        self.video_path = video_path
        self.process_video_file()

    def process_video_file(self):
        if self.template_image is None:
            messagebox.showwarning("경고", "먼저 마우스 포인터 템플릿 이미지를 선택하세요.")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("오류", "비디오 파일을 열 수 없습니다.")
            return

        # 비디오 프레임 크기 가져오기
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 위치 리스트 초기화
        positions = []

        # 진행률 표시를 위한 총 프레임 수 가져오기
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        progress = 0

        # 프레임을 읽고 마우스 포인터 감지
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            x, y = self.detect_mouse_pointer(frame)
            if x is not None and y is not None:
                positions.append((x, y))

            progress += 1
            # 진행률 표시를 추가할 수 있습니다.

        cap.release()

        if not positions:
            messagebox.showwarning("경고", "마우스 포인터 위치를 감지할 수 없습니다.")
            return

        # 위치 저장
        self.video_positions = positions

        # 히트맵 생성
        self.generate_heatmap_from_positions(positions, frame_width, frame_height)

    def detect_mouse_pointer(self, frame):
        if self.template_image is None:
            return None, None

        # 프레임과 템플릿 이미지를 그레이스케일로 변환
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(self.template_image, cv2.COLOR_BGR2GRAY)

        # 템플릿 매칭 실행
        res = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        # 감지 임계값 설정
        threshold = 0.8
        if max_val >= threshold:
            x, y = max_loc
            # 템플릿 크기 고려하여 중심 좌표 계산
            x += int(self.template_image.shape[1] / 2)
            y += int(self.template_image.shape[0] / 2)
            return x, y
        else:
            return None, None

    def generate_heatmap_from_positions(self, positions, width, height):
        # 히트맵 데이터 생성
        heatmap_data = np.zeros((height, width), dtype=np.float32)

        for pos in positions:
            x, y = int(pos[0]), int(pos[1])
            if 0 <= x < width and 0 <= y < height:
                heatmap_data[y, x] += 1

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

        # 첫 번째 프레임에 히트맵 오버레이
        cap = cv2.VideoCapture(self.video_path)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("오류", "비디오 프레임을 읽을 수 없습니다.")
            return

        # 프레임을 PIL 이미지로 변환
        frame_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))

        # 히트맵 이미지를 프레임 이미지에 오버레이
        combined_image = Image.alpha_composite(frame_image, heatmap_image)

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
        self.destroy()

def main():
    root = SettingsWindow()
    root.protocol("WM_DELETE_WINDOW", root.on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
