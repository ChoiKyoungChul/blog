# Blogger 자동 발행

Claude로 글을 생성해서 구글 Blogger에 자동으로 올리는 스크립트.

## 1. 설치

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Google Cloud OAuth 설정

1. https://console.cloud.google.com/ 접속 → 프로젝트 생성
2. **API 및 서비스 → 라이브러리** → "Blogger API v3" 검색 → 사용 설정
3. **API 및 서비스 → OAuth 동의 화면**
   - User Type: 외부
   - 앱 이름/이메일 입력 후 저장
   - 테스트 사용자에 본인 Gmail 추가
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
   - 애플리케이션 유형: **데스크톱 앱**
   - JSON 다운로드 → `credentials.json`으로 이 폴더에 저장

## 3. 환경변수 설정

```bash
copy .env.example .env
```

`.env` 편집:
- `ANTHROPIC_API_KEY`: https://console.anthropic.com/ 에서 발급
- `BLOG_ID`: 아래 명령으로 확인

```bash
python blogger_auth.py
```

첫 실행 시 브라우저가 열려 구글 로그인 → 승인. `token.json`이 생성되고 블로그 목록이 출력됩니다. 원하는 블로그 ID를 `.env`에 넣으세요.

## 4. 사용법

**초안으로 저장 (기본, 안전):**
```bash
python publish.py "파이썬 초보를 위한 팁 5가지"
```

**즉시 발행:**
```bash
python publish.py "파이썬 초보를 위한 팁 5가지" --publish
```

**태그와 톤 지정:**
```bash
python publish.py "리액트 훅 정리" --labels 리액트 프론트엔드 --tone "전문적이고 실용적인"
```

## 파일 구조

- `generate_post.py` — Claude로 HTML 초안 생성
- `blogger_auth.py` — OAuth 인증, 블로그 목록 조회
- `publish.py` — 메인 엔트리포인트
- `credentials.json` — OAuth 클라이언트 (직접 다운로드, git 제외)
- `token.json` — 액세스 토큰 (자동 생성, git 제외)

## 5. 매일 자동 발행 (Windows 작업 스케줄러)

### 5-1. 주제 목록 준비
`topics.txt` 열어서 발행하고 싶은 주제를 한 줄에 하나씩 추가하세요.
- 형식: `주제 | 태그1,태그2,태그3` (태그는 선택)
- `#`으로 시작하는 줄과 빈 줄은 무시됨
- 발행된 주제는 `posted_log.txt`에 기록되어 중복 발행 안 됨

### 5-2. 수동 테스트
```bash
python daily_post.py              # 초안 저장
python daily_post.py --publish    # 즉시 발행
```

### 5-3. 작업 스케줄러 등록
1. **Win + R** → `taskschd.msc` 실행
2. 오른쪽 **"작업 만들기"** 클릭 (기본 작업 아님)
3. **일반 탭**
   - 이름: `블로그 자동 발행`
   - "사용자가 로그온할 때만 실행" 선택
4. **트리거 탭** → 새로 만들기
   - 매일, 시작 시간 지정 (예: 오전 9:00)
5. **동작 탭** → 새로 만들기
   - 프로그램/스크립트: `C:\laragon\www\blog\run_daily.bat`
6. **조건 탭**
   - "컴퓨터가 AC 전원일 때만 시작" 해제 (노트북인 경우)
7. 확인 → 저장

### 5-4. 로그 확인
- `daily_log.txt` — 실행 결과 (표준 출력/에러)
- `posted_log.txt` — 발행 이력 (날짜, 주제, ID, URL)

## 파일 구조

- `generate_post.py` — LLM으로 HTML 초안 생성 (Anthropic/OpenAI/Gemini 자동 선택)
- `blogger_auth.py` — OAuth 인증, 블로그 목록 조회
- `publish.py` — 단발성 발행 엔트리포인트
- `daily_post.py` — 매일 자동 발행용 (topics.txt에서 선택)
- `run_daily.bat` — 작업 스케줄러가 호출하는 배치 파일
- `topics.txt` — 주제 대기열
- `posted_log.txt` — 발행 이력 (자동 생성)
- `daily_log.txt` — 스케줄러 실행 로그 (자동 생성)
- `credentials.json` — OAuth 클라이언트 (직접 다운로드, git 제외)
- `token.json` — 액세스 토큰 (자동 생성, git 제외)

## 팁

- 처음엔 `--publish` 없이 초안으로 뽑아본 뒤, Blogger 웹에서 검토·수정 후 발행하는 걸 추천합니다
- `topics.txt`에 20~30개 주제를 미리 채워두면 한 달 동안 자동 운영 가능
- 주제 소진되면 스크립트가 "발행할 새 주제가 없습니다" 출력하고 조용히 종료
