#!/usr/bin/env python3
"""
KETEP 공지사항 모니터링 및 Slack 알림 봇
- 오늘 날짜에 등록된 공지사항만 알림
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 설정
KETEP_URL = "https://www.ketep.re.kr/board?menuId=MENU002080100000000&boardId=BOARD00022"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 브라우저처럼 보이는 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def is_today(date_str: str) -> bool:
    """날짜 문자열이 오늘 날짜인지 확인"""
    if not date_str:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    today_dot = datetime.now().strftime("%Y.%m.%d")
    today_slash = datetime.now().strftime("%Y/%m/%d")
    today_short = datetime.now().strftime("%y-%m-%d")
    today_short_dot = datetime.now().strftime("%y.%m.%d")

    # 날짜 문자열에서 숫자만 추출하여 비교
    date_numbers = re.sub(r'[^0-9]', '', date_str)
    today_numbers = datetime.now().strftime("%Y%m%d")
    today_numbers_short = datetime.now().strftime("%y%m%d")

    return (date_str == today or
            date_str == today_dot or
            date_str == today_slash or
            date_str == today_short or
            date_str == today_short_dot or
            date_numbers == today_numbers or
            date_numbers == today_numbers_short)


def fetch_ketep_notices() -> list:
    """KETEP 공지사항 크롤링"""
    notices = []

    try:
        session = requests.Session()
        response = session.get(KETEP_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 게시판 테이블에서 공지사항 추출
        # KETEP 사이트 구조에 맞게 파싱
        table = soup.find("table", class_="board-list") or soup.find("table")

        if not table:
            # 다른 형태의 게시판 구조 시도
            board_items = soup.select(".board-list li, .list-item, tr[class*='list']")
            if not board_items:
                board_items = soup.select("tbody tr")
        else:
            board_items = table.select("tbody tr")

        for item in board_items:
            try:
                # 제목과 링크 추출
                title_elem = item.select_one("a, .title a, td.title a, .subject a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")

                # 상대 경로를 절대 경로로 변환
                if link and not link.startswith("http"):
                    link = f"https://www.ketep.re.kr{link}"

                # 날짜 추출
                date_elem = item.select_one(".date, td.date, .reg-date, td:nth-child(4), td:nth-child(5)")
                date = date_elem.get_text(strip=True) if date_elem else ""

                # 번호 추출 (있는 경우)
                num_elem = item.select_one(".num, td.num, td:first-child")
                num = num_elem.get_text(strip=True) if num_elem else ""

                if title:
                    notices.append({
                        "num": num,
                        "title": title,
                        "link": link,
                        "date": date,
                        "source": "KETEP"
                    })
            except Exception as e:
                print(f"항목 파싱 중 오류: {e}")
                continue

    except requests.RequestException as e:
        print(f"KETEP 사이트 접속 오류: {e}")

    return notices


def send_slack_notification(notices: list):
    """Slack으로 새 공지사항 알림 전송"""
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        return False

    if not notices:
        print("알릴 새 공지사항이 없습니다.")
        return True

    # Slack 메시지 구성
    today_str = datetime.now().strftime("%Y-%m-%d")
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📢 KETEP 오늘의 공지사항 ({len(notices)}건)",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 {today_str} 등록된 공지"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    for notice in notices[:10]:  # 최대 10개까지만 표시
        notice_text = f"*<{notice['link']}|{notice['title']}>*"
        if notice['date']:
            notice_text += f"\n📅 {notice['date']}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": notice_text
            }
        })

    if len(notices) > 10:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"외 {len(notices) - 10}건의 공지사항이 더 있습니다."
                }
            ]
        })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🔗 <{KETEP_URL}|KETEP 공지사항 바로가기>"
            }
        ]
    })

    payload = {"blocks": blocks}

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        print(f"Slack 알림 전송 완료: {len(notices)}건")
        return True
    except requests.RequestException as e:
        print(f"Slack 알림 전송 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    print(f"[{datetime.now().isoformat()}] KETEP 공지사항 모니터링 시작")
    print(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

    # 공지사항 크롤링
    all_notices = fetch_ketep_notices()
    print(f"크롤링한 공지사항: {len(all_notices)}건")

    # 오늘 등록된 공지사항만 필터링
    today_notices = [n for n in all_notices if is_today(n["date"])]
    print(f"오늘 등록된 공지사항: {len(today_notices)}건")

    if today_notices:
        # Slack 알림 전송
        send_slack_notification(today_notices)
    else:
        print("오늘 등록된 새 공지사항이 없습니다.")

    print(f"[{datetime.now().isoformat()}] 모니터링 완료")


if __name__ == "__main__":
    main()
