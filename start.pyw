"""
K-Reservation Bot 런처
더블클릭 시 Flask 서버를 백그라운드에서 시작하고 브라우저를 자동으로 엽니다.
콘솔(터미널) 창이 열리지 않습니다.
"""
import os
import sys
import threading
import time
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import messagebox

# ── 작업 디렉터리를 이 파일 위치로 설정 ─────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

PORT = 5000
URL  = f"http://localhost:{PORT}"


# ── 서버 상태 확인 ──────────────────────────────────────────────────────────
def is_server_ready():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ping", timeout=1)
        return True
    except Exception:
        return False


# ── Flask 서버 실행 (별도 스레드) ───────────────────────────────────────────
def run_flask():
    try:
        from app import app
        app.run(host="127.0.0.1", port=PORT, debug=False,
                threaded=True, use_reloader=False)
    except Exception as e:
        # 메인 스레드로 오류 전달
        root.after(0, lambda: show_error(str(e)))


def show_error(msg):
    status_var.set("⚠ 서버 오류 발생")
    messagebox.showerror("서버 오류", msg)


# ── 부팅 시퀀스 (백그라운드 스레드) ─────────────────────────────────────────
def boot():
    if is_server_ready():
        root.after(0, lambda: status_var.set(f"✓ 서버 실행 중  →  {URL}"))
        root.after(0, lambda: webbrowser.open(URL))
        return

    root.after(0, lambda: status_var.set("서버 시작 중… (최대 15초 소요)"))

    # 패키지 확인
    try:
        import flask  # noqa: F401
    except ImportError:
        root.after(0, lambda: show_error(
            "flask 패키지가 없습니다.\n"
            "터미널에서 다음 명령을 실행하세요:\n"
            "  pip install -r requirements.txt"
        ))
        return

    # Flask 서버 시작
    threading.Thread(target=run_flask, daemon=True).start()

    # 준비될 때까지 대기 (최대 15초)
    for _ in range(30):
        time.sleep(0.5)
        if is_server_ready():
            root.after(0, on_server_ready)
            return

    root.after(0, lambda: status_var.set("⚠ 서버 시작 실패 — 아래 버튼으로 재시도하세요."))


def on_server_ready():
    status_var.set(f"✓ 서버 실행 중  →  {URL}")
    webbrowser.open(URL)


# ── UI ───────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("K-Reservation Bot")
root.geometry("360x95")
root.resizable(False, False)

# 항상 최상위 표시
root.attributes("-topmost", True)

# 상태 레이블
status_var = tk.StringVar(value="초기화 중…")
lbl = tk.Label(root, textvariable=status_var, pady=10, font=("Malgun Gothic", 9))
lbl.pack()

# 버튼 영역
btn_frame = tk.Frame(root)
btn_frame.pack(pady=(0, 8))

tk.Button(
    btn_frame, text="브라우저 열기", width=14,
    command=lambda: webbrowser.open(URL)
).pack(side=tk.LEFT, padx=6)

tk.Button(
    btn_frame, text="서버 재시작", width=14,
    command=lambda: threading.Thread(target=boot, daemon=True).start()
).pack(side=tk.LEFT, padx=6)

tk.Button(
    btn_frame, text="종료", width=8, fg="red",
    command=root.destroy
).pack(side=tk.LEFT, padx=6)

# ── 시작 ─────────────────────────────────────────────────────────────────────
threading.Thread(target=boot, daemon=True).start()
root.mainloop()
