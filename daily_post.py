"""매일 한 개씩 발행. topics.txt 우선 → 없으면 LLM으로 주제 자동 생성. 이미지 자동 삽입."""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from generate_topic import generate_topic
from publish_helper import generate_and_publish

load_dotenv()

BASE = Path(__file__).parent
TOPICS_FILE = BASE / "topics.txt"
LOG_FILE = BASE / "posted_log.txt"


def load_topics() -> list[dict]:
    """topics.txt 확장 파싱. 형식: 주제 | 태그들 | 이미지URL(선택)"""
    if not TOPICS_FILE.exists():
        return []
    items = []
    for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        topic = parts[0] if parts else ""
        tags = [t.strip() for t in parts[1].split(",")] if len(parts) > 1 else []
        image_url = parts[2] if len(parts) > 2 else ""
        product_url = parts[3] if len(parts) > 3 else ""
        if topic:
            items.append({
                "topic": topic,
                "tags": [t for t in tags if t],
                "image_url": image_url,
                "product_url": product_url,
            })
    return items


def load_posted_topics() -> list[str]:
    if not LOG_FILE.exists():
        return []
    posted = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            posted.append(parts[1].strip())
    return posted


def append_log(topic: str, post_id: str, url: str, source: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{topic}\t{post_id}\t{url}\t{source}\n")


def pick_next_topic() -> tuple[dict, str]:
    posted_set = set(load_posted_topics())
    force_auto = os.environ.get("AUTO_TOPIC", "").lower() in ("1", "true", "yes")

    if not force_auto:
        for item in load_topics():
            if item["topic"] not in posted_set:
                return item, "topics.txt"

    print("[자동 생성] topics.txt 소진 또는 AUTO_TOPIC=1 → LLM으로 주제 생성")
    for attempt in range(3):
        topic, tags = generate_topic(recent=load_posted_topics())
        if topic not in posted_set:
            return {"topic": topic, "tags": tags, "image_url": ""}, "auto"
        print(f"[재시도 {attempt + 1}] 중복 주제 생성됨: {topic}")

    raise RuntimeError("3회 시도 후에도 중복되지 않은 주제 생성 실패")


def main():
    publish_now = "--publish" in sys.argv

    item, source = pick_next_topic()
    print(f"[선택된 주제] {item['topic']} (출처: {source})")
    print(f"[태그] {item['tags']}")

    result = generate_and_publish(
        topic=item["topic"],
        tags=item["tags"],
        image_url=item.get("image_url", ""),
        product_url=item.get("product_url", ""),
        as_draft=not publish_now,
    )

    post_id = result.get("id", "")
    url = result.get("url", "(초안)")
    status = "발행됨" if publish_now else "초안 저장됨"
    meta = result.get("_post", {})

    append_log(item["topic"], post_id, url, source)
    print(f"[{status}] {meta.get('title', item['topic'])}")
    print(f"[메타 설명] {meta.get('meta_description', '')}")
    print(f"URL: {url}")
    print(f"ID: {post_id}")


if __name__ == "__main__":
    main()
