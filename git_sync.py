"""로컬↔원격 자동 동기화. daily_post/app에서 발행 전후 호출."""
import subprocess
from pathlib import Path

BASE = Path(__file__).parent


def _run(args: list[str], timeout: int = 30) -> tuple[int, str]:
    result = subprocess.run(
        args, cwd=str(BASE),
        capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def pull_latest() -> bool:
    """발행 직전 원격 최신 이력 가져오기. 충돌 시 원격 우선."""
    if not (BASE / ".git").exists():
        print("[git] .git 없음 → 동기화 스킵")
        return True
    code, out = _run(["git", "fetch", "origin", "main"])
    if code != 0:
        print(f"[git fetch 실패] {out}")
        return False
    code, out = _run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"])
    if code == 0:
        print("[git pull] 최신 동기화 완료")
        return True
    print(f"[git pull 실패] {out}")
    _run(["git", "rebase", "--abort"])
    return False


def push_changes(files: list[str], message: str = "chore: 발행 이력 업데이트") -> bool:
    """발행 후 이력 파일 커밋 → push."""
    if not (BASE / ".git").exists():
        return True
    code, _ = _run(["git", "add"] + files)
    if code != 0:
        return False
    code, out = _run(["git", "diff", "--staged", "--quiet"])
    if code == 0:
        print("[git] 변경사항 없음")
        return True
    code, out = _run(["git", "commit", "-m", message])
    if code != 0:
        print(f"[git commit 실패] {out}")
        return False
    code, out = _run(["git", "push"], timeout=60)
    if code == 0:
        print("[git push] 원격 업데이트 완료")
        return True
    print(f"[git push 실패] {out}")
    return False


if __name__ == "__main__":
    pull_latest()
