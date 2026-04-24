"""Playwright 기반 코레일 웹 액션 함수 모듈."""

import logging
import random
import time
from typing import Optional

from constants import (
    KORAIL_LOGIN_URL,
    KORAIL_TICKET_URL,
    STATION_CODES,
    SEAT_TYPE_SPECIAL,
    LOGIN_WAIT_TIMEOUT,
)

logger = logging.getLogger(__name__)


def create_browser(playwright):
    """Playwright 브라우저 인스턴스를 생성합니다."""
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()
    return browser, context, page


def login(page, korail_id: str, korail_pw: str) -> bool:
    """코레일에 로그인합니다."""
    try:
        page.goto(KORAIL_LOGIN_URL, timeout=LOGIN_WAIT_TIMEOUT * 1000)
        _random_delay()
        page.fill("#txtMember", korail_id)
        _random_delay(0.3, 0.8)
        page.fill("#txtPwd", korail_pw)
        _random_delay(0.5, 1.0)
        page.click(".btn_login")
        page.wait_for_load_state("networkidle", timeout=LOGIN_WAIT_TIMEOUT * 1000)

        if "로그인" not in page.title():
            logger.info("로그인 성공")
            return True
        logger.error("로그인 실패: 아이디 또는 비밀번호를 확인하세요.")
        return False
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        return False


def search_trains(page, journey: dict) -> list[dict]:
    """출발역/도착역/날짜/시간으로 열차를 조회합니다."""
    dep_code = STATION_CODES.get(journey["dep_station"], journey["dep_station"])
    arr_code = STATION_CODES.get(journey["arr_station"], journey["arr_station"])
    dep_date = journey["dep_date"].replace("-", "")  # YYYYMMDD
    dep_time = journey["dep_time"].replace(":", "") + "00"  # HHMMSS

    try:
        url = (
            f"{KORAIL_TICKET_URL}"
            f"?txtGoAbrdDt={dep_date}"
            f"&txtGoStart={dep_code}"
            f"&txtGoEnd={arr_code}"
            f"&txtGoHour={dep_time}"
            f"&selGoTrain=100"  # KTX
        )
        page.goto(url, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        _random_delay()

        return _parse_train_list(page)
    except Exception as e:
        logger.error(f"열차 조회 오류: {e}")
        return []


def find_special_seat(trains: list[dict], target_train_no: str = "") -> Optional[dict]:
    """조회된 열차 목록에서 특실 예약 가능한 열차를 반환합니다.
    target_train_no가 지정된 경우 해당 열차만 확인합니다."""
    if target_train_no:
        for train in trains:
            if train.get("train_no") == target_train_no and train.get("special_available"):
                return train
        return None
    for train in trains:
        if train.get("special_available"):
            return train
    return None


def reserve_train(page, train: dict) -> bool:
    """특실 예약 버튼을 클릭하여 예약을 진행합니다."""
    try:
        _random_delay(0.5, 1.2)
        special_btn_selector = f"[data-train-no='{train['train_no']}'] .btn_special"
        btn = page.locator(special_btn_selector)

        if btn.count() == 0 or not btn.is_enabled():
            logger.warning(f"열차 {train['train_no']}: 특실 버튼 비활성화")
            return False

        btn.click()
        page.wait_for_load_state("networkidle", timeout=10000)
        _random_delay(1.0, 2.0)

        # 예약 확인 페이지 여부 확인
        if "예약" in page.title() or page.locator(".reservation-confirm").count() > 0:
            logger.info(f"열차 {train['train_no']} 특실 예약 접수 완료")
            return True

        logger.warning(f"열차 {train['train_no']}: 예약 확인 페이지 이동 실패")
        return False
    except Exception as e:
        logger.error(f"예약 처리 오류: {e}")
        return False


def _parse_train_list(page) -> list[dict]:
    """페이지에서 열차 목록을 파싱합니다."""
    trains = []
    rows = page.locator("tr.train_row")

    for i in range(rows.count()):
        row = rows.nth(i)
        try:
            train_no = row.get_attribute("data-train-no") or ""
            dep_time = row.locator(".dep_time").inner_text().strip()
            arr_time = row.locator(".arr_time").inner_text().strip()
            special_btn = row.locator(".btn_special")
            special_available = (
                special_btn.count() > 0
                and special_btn.is_enabled()
                and "매진" not in special_btn.inner_text()
            )
            trains.append(
                {
                    "train_no": train_no,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "special_available": special_available,
                }
            )
        except Exception:
            continue

    return trains


def _random_delay(min_s: float = 1.0, max_s: float = 3.5) -> None:
    """Anti-bot 방지용 랜덤 딜레이."""
    time.sleep(random.uniform(min_s, max_s))
