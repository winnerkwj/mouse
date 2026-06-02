"""현재 열려 있는 모든 창의 제목을 출력한다(빈 제목 제외)."""

import pygetwindow as gw


def main():
    for title in gw.getAllTitles():
        if title.strip():
            print(title)


if __name__ == "__main__":
    main()
