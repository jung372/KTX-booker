# 코레일 역 코드 및 고정 URL 상수

KORAIL_MAIN_URL  = "https://www.korail.com"
KORAIL_LOGIN_URL = "https://www.korail.com/korail/com/login.do"
KORAIL_TICKET_URL = "https://www.korail.com/ebizprd/EbizPrdTicketpr21100W.do"

# 주요 역 코드 (코레일 기준)
STATION_CODES = {
    "서울": "0001",
    "용산": "0002",
    "영등포": "0003",
    "수원": "0004",
    "천안아산": "0010",
    "오송": "0015",
    "대전": "0020",
    "김천구미": "0025",
    "동대구": "0030",
    "경주": "0035",
    "포항": "0037",
    "울산": "0040",
    "부산": "0045",
    "광주송정": "0050",
    "목포": "0055",
    "여수엑스포": "0060",
    "전주": "0065",
    "익산": "0067",
    "강릉": "0150",
    "진부": "0152",
    "평창": "0154",
    "둔내": "0156",
    "횡성": "0158",
    "만종": "0160",
    "원주": "0165",
    "청량리": "0180",
    "상봉": "0185",
}

# 좌석 등급
SEAT_TYPE_SPECIAL = "특실"
SEAT_TYPE_GENERAL = "일반실"

# 조회 설정
DEFAULT_SEARCH_INTERVAL_MIN = 1.0  # 초
DEFAULT_SEARCH_INTERVAL_MAX = 3.5  # 초
MAX_RETRY_COUNT = 999
LOGIN_WAIT_TIMEOUT = 30  # 초

# 텔레그램
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"
