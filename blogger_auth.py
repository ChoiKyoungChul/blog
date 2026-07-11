"""Google Blogger OAuth 인증 모듈."""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/blogger"]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_blogger_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} 파일이 필요합니다. "
                    "Google Cloud Console에서 OAuth 클라이언트 JSON을 다운로드해 저장하세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("blogger", "v3", credentials=creds)


def list_my_blogs():
    service = get_blogger_service()
    blogs = service.blogs().listByUser(userId="self").execute()
    for blog in blogs.get("items", []):
        print(f"{blog['id']}\t{blog['name']}\t{blog['url']}")


if __name__ == "__main__":
    list_my_blogs()
