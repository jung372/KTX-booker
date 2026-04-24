"""K-Reservation Bot - Flask 웹 서버 (모바일 지원)."""

import json
import logging
import queue
import threading
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import config_manager
from constants import STATION_CODES
from core_engine import ReservationEngine

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

_engine: ReservationEngine = None
_engine_lock = threading.Lock()
_subscribers: list[queue.Queue] = []
_subscribers_lock = threading.Lock()
_current_status = {"status": "idle", "journey": None, "attempts": 0, "running": False}


# ── SSE 브로드캐스터 ──────────────────────────────────────────────────────────

def _broadcast(event_type: str, data: dict) -> None:
    message = json.dumps({"type": event_type, **data})
    with _subscribers_lock:
        dead = [q for q in _subscribers if q.full()]
        for q in dead:
            _subscribers.remove(q)
        for q in _subscribers:
            q.put_nowait(message)


def _on_status(status: str, journey, attempts: int) -> None:
    global _current_status
    running = status not in ("idle", "success", "error")
    _current_status = {"status": status, "journey": journey, "attempts": attempts, "running": running}
    _broadcast("status", _current_status)


def _on_log(message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    _broadcast("log", {"message": f"[{ts}] {message}"})


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    stations = sorted(STATION_CODES.keys())
    return render_template("index.html", stations=stations)


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(config_manager.load_config())


@app.route("/api/config", methods=["POST"])
def save_config():
    try:
        data = request.get_json(force=True) or {}
        # 기존 설정과 병합하여 저장 (누락 키 보존)
        existing = config_manager.load_config()
        existing.update(data)
        config_manager.save_config(existing)
        logging.info("설정 저장 완료: korail_id=%s", existing.get("korail_id", ""))
        return jsonify({"ok": True})
    except Exception as e:
        logging.exception("설정 저장 오류")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True})


@app.route("/api/stations", methods=["GET"])
def get_stations():
    return jsonify(sorted(STATION_CODES.keys()))


@app.route("/api/search", methods=["POST"])
def search_trains_api():
    data = request.get_json(force=True) or {}
    dep_station = data.get("dep_station", "").strip()
    arr_station = data.get("arr_station", "").strip()
    dep_date    = data.get("dep_date", "").strip()
    dep_time    = data.get("dep_time", "00:00").strip()

    if not dep_station or not arr_station or not dep_date:
        return jsonify({"ok": False, "error": "출발역, 도착역, 날짜를 입력하세요."})

    cfg = config_manager.load_config()
    if not cfg.get("korail_id") or not cfg.get("korail_pw"):
        return jsonify({"ok": False, "error": "설정 탭에서 코레일 계정을 먼저 저장하세요."})

    journey = {"dep_station": dep_station, "arr_station": arr_station,
               "dep_date": dep_date, "dep_time": dep_time}
    try:
        from playwright.sync_api import sync_playwright
        import korail_api as _api
        with sync_playwright() as pw:
            browser, context, page = _api.create_browser(pw)
            try:
                if not _api.login(page, cfg["korail_id"], cfg["korail_pw"]):
                    return jsonify({"ok": False, "error": "코레일 로그인 실패. 아이디/비밀번호를 확인하세요."})
                trains = _api.search_trains(page, journey)
                return jsonify({"ok": True, "trains": trains})
            finally:
                browser.close()
    except Exception as e:
        logging.exception("열차 검색 오류")
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/start", methods=["POST"])
def start():
    global _engine
    with _engine_lock:
        if _engine and _engine.is_running():
            return jsonify({"ok": False, "error": "이미 실행 중입니다."})
        cfg = config_manager.load_config()

        data = request.get_json(force=True) or {}
        if data.get("dep_station"):
            primary = {
                "dep_station":     data["dep_station"],
                "arr_station":     data.get("arr_station", ""),
                "dep_date":        data.get("dep_date", ""),
                "dep_time":        data.get("dep_time", ""),
                "target_train_no": data.get("target_train_no", ""),
            }
            cfg["primary_journey"] = primary
            config_manager.save_config(cfg)
        else:
            primary = cfg.get("primary_journey", {})

        extra = [j for j in cfg.get("journeys", []) if j.get("dep_station")]
        cfg["journeys"] = ([primary] if primary.get("dep_station") else []) + extra[:2]

        valid, errors = config_manager.validate_config(cfg)
        if not valid:
            return jsonify({"ok": False, "error": "\n".join(errors)})
        _engine = ReservationEngine(cfg, _on_status, _on_log)
        _engine.start()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def stop():
    global _engine
    with _engine_lock:
        if _engine and _engine.is_running():
            _engine.stop()
    return jsonify({"ok": True})


@app.route("/api/status", methods=["GET"])
def status():
    running = _engine.is_running() if _engine else False
    return jsonify({**_current_status, "running": running})


# ── SSE 스트림 ────────────────────────────────────────────────────────────────

@app.route("/api/events")
def events():
    """실시간 상태·로그를 SSE로 스트리밍합니다."""
    q: queue.Queue = queue.Queue(maxsize=200)
    with _subscribers_lock:
        _subscribers.append(q)

    def generate():
        yield f"data: {json.dumps({'type': 'status', **_current_status})}\n\n"
        try:
            while True:
                try:
                    yield f"data: {q.get(timeout=25)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            with _subscribers_lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 실행 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n K-Reservation Bot 서버 시작")
    print(f" PC 브라우저 : http://localhost:5000")
    print(f" 모바일 접속 : http://{local_ip}:5000  (같은 Wi-Fi 필요)\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
