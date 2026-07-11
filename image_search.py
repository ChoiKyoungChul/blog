"""Pixabay 이미지/비디오 검색."""
import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

IMAGE_ENDPOINT = "https://pixabay.com/api/"
VIDEO_ENDPOINT = "https://pixabay.com/api/videos/"


def search_pixabay(keyword: str) -> tuple[str, str] | None:
    """이미지 검색 → (image_url, alt_text)."""
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    try:
        resp = requests.get(
            IMAGE_ENDPOINT,
            params={
                "key": key,
                "q": keyword,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 20,
                "lang": "ko",
            },
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if not hits:
            return None
        pick = random.choice(hits)
        url = pick.get("largeImageURL") or pick.get("webformatURL")
        alt = pick.get("tags", keyword)
        return url, alt
    except Exception as e:
        print(f"[Pixabay 이미지 실패] {e}")
        return None


def search_pixabay_video(keyword: str) -> dict | None:
    """비디오 검색 → {url, thumbnail, tags, page_url, user} 또는 None."""
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    try:
        resp = requests.get(
            VIDEO_ENDPOINT,
            params={
                "key": key,
                "q": keyword,
                "safesearch": "true",
                "per_page": 10,
                "lang": "ko",
            },
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if not hits:
            return None
        pick = random.choice(hits)
        videos = pick.get("videos", {})
        preferred = videos.get("small") or videos.get("medium") or videos.get("tiny")
        if not preferred or not preferred.get("url"):
            return None
        return {
            "url": preferred["url"],
            "thumbnail": preferred.get("thumbnail", ""),
            "width": preferred.get("width", 640),
            "height": preferred.get("height", 360),
            "tags": pick.get("tags", keyword),
            "page_url": pick.get("pageURL", ""),
            "user": pick.get("user", ""),
        }
    except Exception as e:
        print(f"[Pixabay 비디오 실패] {e}")
        return None


def get_image(keyword: str, fallback_url: str | None = None, fallback_alt: str | None = None) -> tuple[str, str] | None:
    if fallback_url:
        return fallback_url, fallback_alt or keyword
    return search_pixabay(keyword)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "coffee"
    print(f"=== 이미지 검색: {q} ===")
    img = search_pixabay(q)
    if img:
        print(f"URL: {img[0]}")
        print(f"ALT: {img[1]}")
    else:
        print("이미지를 찾을 수 없습니다.")

    print(f"\n=== 비디오 검색: {q} ===")
    vid = search_pixabay_video(q)
    if vid:
        print(f"URL: {vid['url']}")
        print(f"Thumbnail: {vid['thumbnail']}")
        print(f"Page: {vid['page_url']}")
        print(f"User: {vid['user']}")
    else:
        print("비디오를 찾을 수 없습니다.")
