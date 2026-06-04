# -*- mode: python ; coding: utf-8 -*-
# 단일 .exe (onefile, windowed) 빌드: pyinstaller mouse_analytics.spec
# numpy/scipy/matplotlib/Pillow/openpyxl/pyautogui 는 PyInstaller 기본/contrib 훅이 처리.
# pynput·screeninfo 는 OS 백엔드를 동적 import 하므로 서브모듈을 명시 수집한다.

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules('pynput')
    + collect_submodules('screeninfo')
)

a = Analysis(
    ['mouse_analytics.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 이 앱이 쓰지 않는 무거운 서드파티 라이브러리 제외(용량/취약성 감소).
    # 블러는 Pillow, 컬러맵은 numpy 로 직접 처리하므로 scipy·matplotlib 불필요.
    excludes=[
        'scipy', 'matplotlib',
        'torch', 'torchvision', 'torchaudio',
        'pandas', 'cv2', 'sympy', 'wx',
        'IPython', 'jedi', 'notebook', 'jupyter', 'jupyter_client',
        'jupyter_core', 'zmq', 'tornado', 'pytest', 'nbconvert', 'nbformat',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mouse_analytics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
