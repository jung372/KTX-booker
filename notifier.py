"""텔레그램 알림 전송 모듈."""

import urllib.request
import urllib.parse
import json
import logging
from datetime import datetime

from constants import TELEGRAM_API_BASE

logger = logging.getLogger(__name__)


def send_reservation_success(token: str, chat_id: str, train_info: dict) -> bool:
    """예약 성공 시 텔레그램 메시지를 전송합니다."""
    message = _build_success_message(train_info)
    return _send_message(token, chat_id, message)


def send_error_alert(token: str, chat_id: str, error_msg: str) -> bool:
    """오류 발생 시 텔레그램 알림을 전송합니다."""
    message = f"[K-Reservation Bot] 오류 발생\n{error_msg}"
    return _send_message(token, chat_id, message)


def send_start_notification(token: str, chat_id: str, journeys: list) -> bool:
    """모니터링 시작 알림을 전송합니다."""
    lines = ["[K-Reservation Bot] 모니터링 시작", ""]
    for i, j in enumerate(journeys, 1):
        lines.append(
            f"{i}순위: {j.get('dep_station')} → {j.get('arr_station')} "
            f"{j.get('dep_date')} {j.get('dep_time')}"
        )
    return _send_message(token, chat_id, "\n".join(lines))


def _build_success_message(train_info: dict) -> str:
    lines = [
        "✅ [K-Reservation Bot] 특실 예약 완료!",
        "",
        f"열차번호: {train_info.get('train_no', '-')}",
        f"출발: {train_info.get('dep_station', '-')} {train_info.get('dep_time', '-')}",
        f"도착: {train_info.get('arr_station', '-')} {train_info.get('arr_time', '-')}",
        f"날짜: {train_info.get('dep_date', '-')}",
        f"등급: 특실",
        "",
        f"⏰ 결제 기한: 예약 후 20분 이내",
        "코레일 앱 또는 웹에서 결제를 완료해 주세요.",
    ]
    return "\n".join(lines)


def _send_message(token: str, chat_id: str, text: str) -> bool:
    """텔레그램 Bot API를 통해 메시지를 전송합니다."""
    if not token or not chat_id:
        logger.warning("텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return False

    url = TELEGRAM_API_BASE.format(token=token)
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                logger.info("텔레그램 전송 성공")
                return True
            logger.error(f"텔레그램 전송 실패: {result}")
            return False
    except Exception as e:
        logger.error(f"텔레그램 전송 오류: {e}")
        return False
