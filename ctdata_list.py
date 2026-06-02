"""지정한 폴더의 파일/폴더 목록을 출력한다."""

import os

# 원본 경로 유지. 백슬래시 경로는 raw 문자열로 둬서 잘못된 이스케이프 경고를 피한다.
SCAN_DIR = r"D:\테스트 스캔 파일\OneGuide 테스트 파일"


def main():
    if not os.path.isdir(SCAN_DIR):
        print(f"폴더를 찾을 수 없습니다: {SCAN_DIR}")
        return
    print(os.listdir(SCAN_DIR))


if __name__ == "__main__":
    main()
