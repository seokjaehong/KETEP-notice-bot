#!/usr/bin/env python3
"""
KETEP 공지사항 모니터링 및 Slack 알림 봇
"""

import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# 설정
KETEP_URL = "https://www.ketep.re.kr/board?menuId=MENU002080100000000&boardId=BOARD00022"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
CACHE_FILE = Path("seen_notices.json")

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


def load_seen_notices() -> set:
    """이전에 확인한 공지사항 ID 불러오기"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("seen_ids", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def save_seen_notices(seen_ids: set):
    """확인한 공지사항 ID 저장"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen_ids": list(seen_ids), "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def generate_notice_id(title: str, date: str) -> str:
    """공지사항 고유 ID 생성"""
    content = f"{title}_{date}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


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
                    notice_id = generate_notice_id(title, date)
                    notices.append({
                        "id": notice_id,
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
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📢 KETEP 새 공지사항 ({len(notices)}건)",
                "emoji": True
            }
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

    # 이전에 확인한 공지사항 불러오기
    seen_ids = load_seen_notices()
    print(f"이전에 확인한 공지사항: {len(seen_ids)}건")

    # 공지사항 크롤링
    all_notices = fetch_ketep_notices()
    print(f"크롤링한 공지사항: {len(all_notices)}건")

    # 새 공지사항 필터링
    new_notices = [n for n in all_notices if n["id"] not in seen_ids]
    print(f"새 공지사항: {len(new_notices)}건")

    if new_notices:
        # Slack 알림 전송
        if send_slack_notification(new_notices):
            # 성공 시 확인한 공지사항 ID 저장
            for notice in new_notices:
                seen_ids.add(notice["id"])
            save_seen_notices(seen_ids)
            print("새 공지사항 ID 저장 완료")
    else:
        print("새 공지사항이 없습니다.")

    # 첫 실행 시에도 현재 공지사항 ID 저장 (다음 실행을 위해)
    if not seen_ids and all_notices:
        for notice in all_notices:
            seen_ids.add(notice["id"])
        save_seen_notices(seen_ids)
        print("초기 공지사항 ID 저장 완료")

    print(f"[{datetime.now().isoformat()}] 모니터링 완료")


if __name__ == "__main__":
    main()
