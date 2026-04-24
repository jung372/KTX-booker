"""
GitHub Actions / CLI 환경에서 KTX 예약 봇을 실행하는 스크립트.
환경변수(또는 .env 파일)에서 설정을 읽습니다.

사용 예시:
    python run_bot.py

필요 환경변수 (GitHub Secrets 또는 .env 파일로 설정):
    KORAIL_ID, KORAIL_PW
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    JOURNEY_DEP_STATION, JOURNEY_ARR_STATION, JOURNEY_DATE, JOURNEY_TIME
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

import config_manager
from core_engine import ReservationEngine


def on_status(status: str, journey, attempts: int) -> None:
    label = f"[{status.upper()}]"
    if journey:
        label += f" {journey}"
    label += f" (시도 {attempts}회)"
    print(label, flush=True)


def on_log(message: str) -> None:
    print(message, flush=True)


def main() -> None:
    cfg = config_manager.load_config()

    # primary_journey → journeys[0] 로 사용
    primary = cfg.get("primary_journey", {})
    if primary.get("dep_station"):
        extra = [j for j in cfg.get("journeys", []) if j.get("dep_station")]
        cfg["journeys"] = [primary] + extra[:2]

    valid, errors = config_manager.validate_config(cfg)
    if not valid:
        print("[ 설정 오류 ]", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("\n필요한 환경변수를 GitHub Secrets 또는 .env 파일에 설정하세요.", file=sys.stderr)
        sys.exit(1)

    engine = ReservationEngine(cfg, on_status, on_log)
    # daemon=False: 메인 스레드가 종료돼도 엔진이 계속 실행됨
    engine.start(daemon=False)

    try:
        engine.wait()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
        engine.stop()
        engine.wait()


if __name__ == "__main__":
    main()
