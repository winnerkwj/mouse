import pygetwindow as gw

# 현재 실행 중인 모든 창의 이름을 출력
windows = gw.getAllTitles()

# 빈 창 이름을 제외하고 출력
for window in windows:
    if window.strip():  # 빈 이름이 아닌 경우에만 출력
        print(window)