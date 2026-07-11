# GitHub Actions로 매일 자동 발행하기

컴퓨터가 꺼져있어도 매일 오전 9시(한국시간) 클라우드에서 자동으로 블로그 글이 발행되도록 설정합니다.

## 1단계: GitHub 저장소 생성

1. https://github.com/new 접속
2. **Repository name**: `blog-automation` (아무 이름이나)
3. **Private** 선택 (중요! 코드에 개인 정보 포함될 수 있음)
4. "Create repository" 클릭
5. 다음 화면에서 표시되는 저장소 URL 복사 (예: `https://github.com/USERNAME/blog-automation.git`)

## 2단계: 로컬 코드를 GitHub에 업로드

터미널에서 이 폴더로 이동해서:

```bash
cd C:\laragon\www\blog

git init
git branch -M main
git add .
git commit -m "initial: 블로그 자동화 시스템"
git remote add origin https://github.com/USERNAME/blog-automation.git
git push -u origin main
```

⚠️ `.env`, `credentials.json`, `token.json`은 `.gitignore` 덕분에 커밋되지 않습니다. GitHub에 올라가지 않으니 안심하세요.

## 3단계: Secrets 등록

### 3-1. base64 인코딩 실행

터미널에서:
```bash
python encode_secrets.py
```

`CREDENTIALS_JSON_B64`, `TOKEN_JSON_B64` 두 개의 긴 문자열이 출력됩니다. 각각 복사해두세요.

### 3-2. GitHub에 Secrets 등록

1. GitHub 저장소 페이지 → **Settings** 탭
2. 왼쪽 메뉴 **Secrets and variables → Actions**
3. **New repository secret** 클릭
4. 아래 7개 Secret을 하나씩 추가:

| Secret 이름 | 값 |
|-------------|-----|
| `CREDENTIALS_JSON_B64` | 위 스크립트 출력의 credentials.json 값 |
| `TOKEN_JSON_B64` | 위 스크립트 출력의 token.json 값 |
| `ANTHROPIC_API_KEY` | `.env`에 있는 값 |
| `OPENAI_API_KEY` | `.env`에 있는 값 |
| `GEMINI_API_KEY` | (없으면 빈 문자열) |
| `PIXABAY_API_KEY` | `.env`에 있는 값 |
| `BLOG_ID` | `.env`에 있는 값 (예: 8692506503286044297) |

### 3-3. Variables 등록 (선택)

같은 페이지 **Variables** 탭에서 추가 (Secret 아님):

| Variable 이름 | 값 (예시) |
|--------------|----------|
| `LLM_PROVIDER` | `openai` |
| `BLOG_THEME` | `일상 팁, 자기계발, IT/기술` |
| `AUTO_TOPIC` | `0` |
| `EMBED_VIDEO` | `1` |

## 4단계: Actions 활성화

1. 저장소 페이지 → **Actions** 탭
2. "I understand my workflows, go ahead and enable them" 클릭 (있으면)
3. 왼쪽 목록에서 **Daily Blog Post** 클릭
4. 오른쪽 **Run workflow** 버튼 → **draft: true** 선택 후 실행 (초안으로 첫 테스트)
5. 실행 완료 후 로그 확인 → Blogger 초안 페이지에서 새 글 확인

정상이면 **매일 오전 9시(한국)** 에 자동 실행됩니다.

## 5단계: 시간 변경 (선택)

`.github/workflows/daily.yml` 파일의 cron 표현식 수정:

```yaml
schedule:
  - cron: '0 0 * * *'   # UTC 기준 → KST 오전 9시
```

- `0 22 * * *` → KST 오전 7시
- `0 3 * * *` → KST 오후 12시 (정오)
- `0 9 * * *` → KST 오후 6시

변경 후 `git commit` + `git push`.

## 이력 관리

- 워크플로 실행 후 발행된 이력은 `posted_log.txt`가 자동으로 커밋됩니다
- `topics.txt` 소진 시 AI가 새 주제 생성 → 그 결과도 posted_log에 기록
- 로컬 웹 대시보드 사용하려면 `git pull`로 최신 이력 받아오세요

## 비용

- GitHub Actions Private repo: **월 2000분 무료** (매일 15분씩 = 월 450분, 충분)
- Public repo로 하면 무제한 무료 (단, 개인 코드 공개됨)

## 로컬 웹앱은 어떻게?

- 로컬 Flask 앱 (`python app.py`)은 **주제 관리, 즉시 발행, 상품 가져오기** 용도로 계속 사용
- 매일 자동 발행만 GitHub Actions가 담당
- 로컬에서 주제 추가/수정 후 `git push`하면 다음 자동 실행에 반영됨

## 트러블슈팅

**Actions 실행 실패 시:**
1. Actions 탭 → 실패한 실행 클릭 → 빨간 X 단계 클릭해서 에러 확인
2. 대부분 Secret 값 오타. `python encode_secrets.py`로 다시 인코딩 후 Secret 업데이트
3. OAuth 토큰 만료 시: 로컬에서 `python blogger_auth.py` 재실행 → `token.json` 재생성 → 다시 인코딩해서 `TOKEN_JSON_B64` Secret 업데이트

**로컬 웹앱과 GitHub Actions 간 topics.txt 충돌 시:**
- Actions가 실행 후 push한 걸 로컬에서 `git pull` 필수
- 로컬에서 편집했으면 `git push` 후 다음 스케줄 대기
