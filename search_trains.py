"""열차 조회 후 결과를 data/search_results.json 으로 저장."""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def _to_min(t: str) -> int:
    """'HH:MM' 또는 'HH시MM분' → 분 단위 정수. 파싱 실패 시 -1."""
    try:
        t = t.strip()
        if ":" in t:
            h, m = t.split(":")[:2]
            return int(h) * 60 + int(m[:2])
        if "시" in t:
            h = int(t.split("시")[0].strip())
            rest = t.split("시")[1].replace("분", "").strip()
            return h * 60 + (int(rest) if rest else 0)
    except Exception:
        pass
    return -1


def main() -> None:
    import config_manager
    import korail_api
    from playwright.sync_api import sync_playwright

    cfg = config_manager.load_config()

    journey = {
        "dep_station": os.environ.get("JOURNEY_DEP_STATION", ""),
        "arr_station": os.environ.get("JOURNEY_ARR_STATION", ""),
        "dep_date":    os.environ.get("JOURNEY_DATE", ""),
        "dep_time":    os.environ.get("JOURNEY_TIME", "06:00"),
    }

    if not journey["dep_station"] or not journey["arr_station"] or not journey["dep_date"]:
        print("출발역/도착역/날짜 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    start_min = _to_min(journey["dep_time"])
    end_min   = start_min + 120  # 희망 시간 이후 2시간

    with sync_playwright() as pw:
        browser, context, page = korail_api.create_browser(pw)
        try:
            logging.info("코레일 로그인 중...")
            if not korail_api.login(page, cfg["korail_id"], cfg["korail_pw"]):
                print("로그인 실패", file=sys.stderr)
                sys.exit(1)

            logging.info("열차 조회 중...")
            trains = korail_api.search_trains(page, journey)

            # 희망 시간 기준 2시간 범위 필터링 (자정 경계 처리 포함)
            filtered = []
            for t in trains:
                t_min = _to_min(t.get("dep_time", ""))
                if t_min < 0:
                    filtered.append(t)
                    continue
                if end_min >= 24 * 60:  # 자정 넘김
                    if t_min >= start_min or t_min <= end_min - 24 * 60:
                        filtered.append(t)
                else:
                    if start_min <= t_min <= end_min:
                        filtered.append(t)

            logging.info(f"조회 완료: {len(filtered)}개 열차 (전체 {len(trains)}개 중 2시간 내)")
        finally:
            browser.close()

    Path("data").mkdir(exist_ok=True)
    result = {
        "journey": journey,
        "trains": filtered,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open("data/search_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logging.info("data/search_results.json 저장 완료")


if __name__ == "__main__":
    main()
