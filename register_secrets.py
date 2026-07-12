"""gh CLI로 GitHub Secrets 일괄 등록."""
import base64
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).parent
GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "ChoiKyoungChul/blog"

load_dotenv()


def b64(filename: str) -> str:
    return base64.b64encode((BASE / filename).read_bytes()).decode()


def set_secret(name: str, value: str) -> bool:
    if not value:
        print(f"  [SKIP] {name}: value is empty")
        return False
    result = subprocess.run(
        [GH, "secret", "set", name, "-R", REPO, "-b", value],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode == 0:
        print(f"  [OK] {name}")
        return True
    print(f"  [FAIL] {name}: {result.stderr.strip()}")
    return False


secrets = {
    "CREDENTIALS_JSON_B64": b64("credentials.json"),
    "TOKEN_JSON_B64": b64("token.json"),
    "BLOG_ID": os.environ.get("BLOG_ID", ""),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    "PIXABAY_API_KEY": os.environ.get("PIXABAY_API_KEY", ""),
}

print(f"저장소: {REPO}")
print(f"등록할 Secret: {len(secrets)}개\n")

ok = 0
for name, value in secrets.items():
    if set_secret(name, value):
        ok += 1

print(f"\n완료: {ok}/{len(secrets)}")
