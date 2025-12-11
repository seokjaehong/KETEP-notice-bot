# KETEP 공지사항 모니터링 봇

KETEP(한국에너지기술평가원) 공지사항을 자동으로 모니터링하고 새 공지가 있으면 Slack으로 알림을 보내는 봇입니다.

## 기능

- KETEP 공지사항 페이지 자동 크롤링
- 새 공지사항 감지 시 Slack 알림 전송
- GitHub Actions를 통한 자동 실행 (매일 3회)
- 중복 알림 방지를 위한 캐시 시스템

## 파일 구조

| 파일 | 설명 |
|------|------|
| `scraper.py` | KETEP 사이트 크롤링 및 Slack 알림 전송 |
| `.github/workflows/monitor.yml` | 매일 3회 자동 실행 (9시, 14시, 18시 KST) |
| `requirements.txt` | Python 의존성 |
| `README.md` | 설정 가이드 (이 파일) |

## 설정 방법

### 1. Slack Webhook 설정

1. [Slack API](https://api.slack.com/apps)에서 새 앱 생성
2. **Incoming Webhooks** 기능 활성화
3. **Add New Webhook to Workspace** 클릭
4. 알림을 받을 채널 선택
5. 생성된 Webhook URL 복사

### 2. GitHub Secrets 설정

1. GitHub 레포지토리 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 시크릿 추가:

| 이름 | 값 |
|------|-----|
| `SLACK_WEBHOOK_URL` | Slack Webhook URL |

### 3. GitHub Actions 활성화

1. 레포지토리의 **Actions** 탭으로 이동
2. 워크플로우 활성화 확인
3. 수동 테스트: **Run workflow** 버튼 클릭

## 실행 일정

| 시간 (KST) | 시간 (UTC) | 설명 |
|------------|------------|------|
| 09:00 | 00:00 | 오전 모니터링 |
| 14:00 | 05:00 | 오후 모니터링 |
| 18:00 | 09:00 | 저녁 모니터링 |

## 로컬 테스트

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export SLACK_WEBHOOK_URL="your-webhook-url"

# 실행
python scraper.py
```

## 알림 예시

새 공지사항이 감지되면 다음과 같은 형태로 Slack에 알림이 전송됩니다:

```
📢 KETEP 새 공지사항 (2건)
────────────────────────
• [공지사항 제목 1]
  📅 2024-01-15

• [공지사항 제목 2]
  📅 2024-01-14
────────────────────────
🔗 KETEP 공지사항 바로가기
```

## 문제 해결

### 크롤링이 안 되는 경우

- KETEP 웹사이트 구조가 변경되었을 수 있습니다
- `scraper.py`의 셀렉터를 웹사이트에 맞게 수정하세요

### Slack 알림이 안 오는 경우

1. `SLACK_WEBHOOK_URL` 시크릿이 올바르게 설정되었는지 확인
2. Webhook URL이 유효한지 확인
3. GitHub Actions 로그에서 오류 메시지 확인

## 라이선스

MIT License
