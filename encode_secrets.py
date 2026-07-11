"""credentials.json / token.json을 base64로 인코딩해 GitHub Secrets에 등록할 수 있게 출력."""
import base64
from pathlib import Path

BASE = Path(__file__).parent


def encode(filename: str) -> str:
    path = BASE / filename
    if not path.exists():
        return f"❌ {filename} 파일이 없습니다."
    data = path.read_bytes()
    return base64.b64encode(data).decode()


def main():
    print("=" * 70)
    print("GitHub Secrets에 아래 값들을 등록하세요")
    print("(Settings → Secrets and variables → Actions → New repository secret)")
    print("=" * 70)

    for name in ["credentials.json", "token.json"]:
        secret_name = "CREDENTIALS_JSON_B64" if "credentials" in name else "TOKEN_JSON_B64"
        encoded = encode(name)
        print(f"\n### Secret 이름: {secret_name}")
        print(f"### 파일: {name}")
        print("### 값 (아래 전체를 복사):")
        print("-" * 70)
        print(encoded)
        print("-" * 70)


if __name__ == "__main__":
    main()
