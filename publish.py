"""Claude로 초안 생성 → Blogger에 발행."""
import argparse
import os

from dotenv import load_dotenv

from blogger_auth import get_blogger_service
from generate_post import generate_post

load_dotenv()


def publish(topic: str, labels: list[str], draft: bool, tone: str) -> dict:
    post = generate_post(topic, tone=tone, labels=labels)
    service = get_blogger_service()

    body = {
        "kind": "blogger#post",
        "title": post.title,
        "content": post.html,
        "labels": post.labels,
    }

    blog_id = os.environ["BLOG_ID"]
    request = service.posts().insert(blogId=blog_id, body=body, isDraft=draft)
    return request.execute()


def main():
    parser = argparse.ArgumentParser(description="Claude → Blogger 자동 발행")
    parser.add_argument("topic", help="글 주제")
    parser.add_argument("--labels", nargs="*", default=[], help="태그 (공백 구분)")
    parser.add_argument("--tone", default="친근하고 정보성 있는", help="글의 톤")
    parser.add_argument("--publish", action="store_true", help="즉시 발행 (기본은 초안 저장)")
    args = parser.parse_args()

    result = publish(
        topic=args.topic,
        labels=args.labels,
        draft=not args.publish,
        tone=args.tone,
    )

    status = "발행됨" if args.publish else "초안 저장됨"
    print(f"[{status}] {result.get('title')}")
    print(f"URL: {result.get('url', '(초안 URL 없음)')}")
    print(f"ID: {result.get('id')}")


if __name__ == "__main__":
    main()
