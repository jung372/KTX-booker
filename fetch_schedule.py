"""향후 7일치 KTX 시간표를 구간별로 조회해 data/schedules.json 에 저장.

SCHEDULE_ROUTES 환경변수로 조회 구간을 지정합니다.
  예) 서울>부산,부산>서울,서울>경주,경주>서울
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

KST = timezone(timedelta(hours=9))
DEFAULT_ROUTES = "서울>부산,부산>서울,서울>경주,경주>서울"


def main() -> None:
    import config_manager
    import korail_api
    from playwright.sync_api import sync_playwright

    cfg = config_manager.load_config()

    raw = os.environ.get("SCHEDULE_ROUTES", DEFAULT_ROUTES)
    routes = [r.strip() for r in raw.split(",") if ">" in r.strip()]
    if not routes:
        print("SCHEDULE_ROUTES에 유효한 구간이 없습니다.", file=sys.stderr)
        sys.exit(1)

    today = datetime.now(KST)
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    result: dict = {
        "generated_at": today.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "routes": {},
    }

    with sync_playwright() as pw:
        browser, context, page = korail_api.create_browser(pw)
        try:
            logging.info("코레일 로그인 중...")
            if not korail_api.login(page, cfg["korail_id"], cfg["korail_pw"]):
                print("로그인 실패", file=sys.stderr)
                sys.exit(1)

            for route in routes:
                dep, arr = route.split(">", 1)
                result["routes"][route] = {}
                logging.info(f"구간 조회: {route}")

                for date in dates:
                    try:
                        trains = korail_api.search_trains(
                            page,
                            {"dep_station": dep, "arr_station": arr,
                             "dep_date": date, "dep_time": "00:00"},
                        )
                        # special_available 제외 — 실시간 정보라 저장 의미 없음
                        result["routes"][route][date] = [
                            {"train_no": t["train_no"],
                             "dep_time": t["dep_time"],
                             "arr_time": t["arr_time"]}
                            for t in trains
                        ]
                        logging.info(f"  {date}: {len(trains)}편")
                        time.sleep(1.5)
                    except Exception as e:
                        logging.warning(f"  {date} 조회 실패: {e}")
                        result["routes"][route][date] = []
        finally:
            browser.close()

    Path("data").mkdir(exist_ok=True)
    with open("data/schedules.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = sum(
        len(v) for rd in result["routes"].values() for v in rd.values()
    )
    logging.info(f"완료: {len(routes)}개 구간, 총 {total}편 저장")


if __name__ == "__main__":
    main()
