"""우선순위 제어 및 전체 루프 스케줄링 모듈."""

import logging
import threading
import time
import random
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ReservationEngine:
    """KTX 특실 예약 자동화 핵심 엔진."""

    def __init__(self, config: dict, status_callback: Callable, log_callback: Callable):
        self.config = config
        self._on_status_update = status_callback  # UI 상태 업데이트 콜백
        self._on_log = log_callback                # UI 로그 출력 콜백
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._attempt_count = 0

    def start(self, daemon: bool = True) -> None:
        """엔진을 백그라운드 스레드로 시작합니다.
        daemon=False 시 메인 스레드 종료 후에도 엔진이 계속 실행됩니다(CLI 용)."""
        if self._running:
            return
        self._running = True
        self._attempt_count = 0
        self._thread = threading.Thread(target=self._run_loop, daemon=daemon)
        self._thread.start()
        self._log("모니터링 시작")

    def wait(self) -> None:
        """엔진 스레드가 완전히 종료될 때까지 블로킹합니다(CLI 용)."""
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def stop(self) -> None:
        """엔진을 중지합니다."""
        self._running = False
        self._log("모니터링 중지")
        self._on_status_update("idle", None, 0)

    def is_running(self) -> bool:
        return self._running

    def _run_loop(self) -> None:
        """우선순위 순서로 열차를 반복 조회합니다."""
        from playwright.sync_api import sync_playwright
        import korail_api
        import notifier

        cfg = self.config
        journeys = cfg.get("journeys", [])
        active_journeys = [j for j in journeys if j.get("dep_station") and j.get("dep_date")]

        with sync_playwright() as playwright:
            browser, context, page = korail_api.create_browser(playwright)
            try:
                self._log("코레일 로그인 시도 중...")
                if not korail_api.login(page, cfg["korail_id"], cfg["korail_pw"]):
                    self._log("로그인 실패. 중단합니다.")
                    self._running = False
                    self._on_status_update("error", None, 0)
                    return

                notifier.send_start_notification(
                    cfg["telegram_token"], cfg["telegram_chat_id"], active_journeys
                )

                while self._running:
                    for priority, journey in enumerate(active_journeys, 1):
                        if not self._running:
                            break

                        self._attempt_count += 1
                        label = (
                            f"{journey['dep_station']}→{journey['arr_station']} "
                            f"{journey['dep_date']} {journey['dep_time']}"
                        )
                        self._log(f"[{self._attempt_count}회] {priority}순위 조회: {label}")
                        self._on_status_update("searching", label, self._attempt_count)

                        trains = korail_api.search_trains(page, journey)
                        target = korail_api.find_special_seat(trains, journey.get("target_train_no", ""))

                        if target:
                            self._log(f"특실 발견! 열차 {target['train_no']} 예약 시도 중...")
                            self._on_status_update("reserving", label, self._attempt_count)

                            target.update({
                                "dep_station": journey["dep_station"],
                                "arr_station": journey["arr_station"],
                                "dep_date": journey["dep_date"],
                            })

                            if korail_api.reserve_train(page, target):
                                self._log(f"예약 완료! 열차 {target['train_no']}")
                                self._on_status_update("success", label, self._attempt_count)
                                notifier.send_reservation_success(
                                    cfg["telegram_token"], cfg["telegram_chat_id"], target
                                )
                                self._running = False
                                return

                    interval = random.uniform(
                        cfg.get("search_interval_min", 1.0),
                        cfg.get("search_interval_max", 3.5),
                    )
                    time.sleep(interval)

            except Exception as e:
                self._log(f"오류 발생: {e}")
                self._on_status_update("error", None, self._attempt_count)
                notifier.send_error_alert(
                    cfg.get("telegram_token", ""),
                    cfg.get("telegram_chat_id", ""),
                    str(e),
                )
            finally:
                browser.close()

    def _log(self, message: str) -> None:
        logger.info(message)
        self._on_log(message)
