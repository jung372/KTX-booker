"""설정 파일 로드 및 유효성 검사 모듈."""

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).parent / "config.json"
ENV_PATH = Path(__file__).parent / ".env"


# GitHub Secrets / 환경변수 → config 키 매핑
_ENV_MAP = {
    "korail_id":        "KORAIL_ID",
    "korail_pw":        "KORAIL_PW",
    "telegram_token":   "TELEGRAM_TOKEN",
    "telegram_chat_id": "TELEGRAM_CHAT_ID",
}

# primary_journey 환경변수 매핑
_JOURNEY_ENV_MAP = {
    "dep_station": "JOURNEY_DEP_STATION",
    "arr_station": "JOURNEY_ARR_STATION",
    "dep_date":    "JOURNEY_DATE",
    "dep_time":    "JOURNEY_TIME",
}


def load_config() -> dict:
    """config.json을 로드하고 환경변수(GitHub Secrets)가 있으면 우선 적용합니다."""
    defaults = _default_config()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            stored = json.load(f)
        for k, v in defaults.items():
            if k not in stored:
                stored[k] = v
        config = stored
    else:
        config = defaults

    # 환경변수 / GitHub Secrets 우선 적용
    for field, env_key in _ENV_MAP.items():
        val = get_env(env_key)
        if val:
            config[field] = val

    # primary_journey 환경변수 적용
    pj = config.get("primary_journey", {})
    for field, env_key in _JOURNEY_ENV_MAP.items():
        val = get_env(env_key)
        if val:
            pj[field] = val
    config["primary_journey"] = pj

    return config


def save_config(config: dict) -> None:
    """설정을 config.json에 저장합니다."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def validate_config(config: dict) -> tuple[bool, list[str]]:
    """설정값의 유효성을 검사합니다. (유효 여부, 오류 목록) 반환."""
    errors = []

    if not config.get("korail_id"):
        errors.append("코레일 아이디가 비어있습니다.")
    if not config.get("korail_pw"):
        errors.append("코레일 비밀번호가 비어있습니다.")
    if not config.get("telegram_token"):
        errors.append("텔레그램 봇 토큰이 비어있습니다.")
    if not config.get("telegram_chat_id"):
        errors.append("텔레그램 Chat ID가 비어있습니다.")

    journeys = config.get("journeys", [])
    if not journeys:
        errors.append("1순위 여정 정보가 없습니다.")
    for i, j in enumerate(journeys, 1):
        if not j.get("dep_station"):
            errors.append(f"{i}순위: 출발역이 비어있습니다.")
        if not j.get("arr_station"):
            errors.append(f"{i}순위: 도착역이 비어있습니다.")
        if not j.get("dep_date"):
            errors.append(f"{i}순위: 출발 날짜가 비어있습니다.")
        if not j.get("dep_time"):
            errors.append(f"{i}순위: 출발 시간대가 비어있습니다.")

    return (len(errors) == 0, errors)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """환경 변수 또는 .env 파일에서 값을 가져옵니다."""
    value = os.environ.get(key)
    if value:
        return value
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default


def _default_config() -> dict:
    return {
        "korail_id": "",
        "korail_pw": "",
        "telegram_token": "",
        "telegram_chat_id": "",
        "primary_journey": {"dep_station": "", "arr_station": "", "dep_date": "", "dep_time": ""},
        "journeys": [
            {"dep_station": "", "arr_station": "", "dep_date": "", "dep_time": ""},
            {"dep_station": "", "arr_station": "", "dep_date": "", "dep_time": ""},
        ],
        "search_interval_min": 1.0,
        "search_interval_max": 3.5,
    }
