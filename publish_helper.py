"""발행 공통 로직: 이미지 삽입, Blogger API 호출, SEO 메타 처리."""
import html
import os

from blogger_auth import get_blogger_service
from dalle_image import generate_dalle_images
from generate_post import Post, generate_post
from image_search import search_pixabay, search_pixabay_video


def _first_h2_or_top(html_str: str) -> tuple[str, str]:
    """이미지를 첫 <p> 뒤에 넣기 위해 <p>...</p> 위치를 찾는다."""
    end = html_str.find("</p>")
    if end == -1:
        return "", html_str
    return html_str[: end + 4], html_str[end + 4 :]


def _make_img_tag(image_url: str, alt: str, caption: str = "") -> str:
    alt_esc = html.escape(alt)
    caption_html = f'<figcaption style="font-size:12px;color:#888;text-align:center;">{html.escape(caption)}</figcaption>' if caption else ""
    return (
        f'<figure style="margin:16px 0;text-align:center;">'
        f'<img src="{html.escape(image_url)}" alt="{alt_esc}" '
        f'style="max-width:100%;height:auto;border-radius:8px;">'
        f'{caption_html}</figure>'
    )


KOREAN_TO_EN_KEYWORDS = {
    "주방용품": "kitchen",
    "요리": "cooking",
    "세탁용품": "laundry",
    "청소용품": "cleaning",
    "욕실용품": "bathroom",
    "수납정리": "organize home",
    "침구·커튼": "bedroom",
    "인테리어소품": "home decor",
    "생활잡화": "household",
    "문구·사무용품": "office supplies",
    "반려동물용품": "pet",
    "스킨케어": "skincare",
    "미용소품": "beauty",
    "마스크팩": "face mask",
    "메이크업": "makeup",
    "선케어": "sunscreen",
    "향수": "perfume",
    "헤어케어": "haircare",
    "바디케어": "body care",
    "네일용품": "nail",
    "헬스용품": "fitness",
    "다이어트식품": "diet food",
    "홍삼·건강즙": "health drink",
    "음료·차": "tea",
    "간편식": "meal prep",
    "과자·간식": "snacks",
    "견과류": "nuts",
    "건강용품": "wellness",
    "진단용품": "medical",
    "의료소모품": "medical supplies",
    "응급처치용품": "first aid",
    "위생용품": "hygiene",
    "재활용품": "recycle",
    "공구": "tools",
    "철물": "hardware",
    "안전용품": "safety",
    "전기용품": "electric",
    "작업용품": "work",
    "액세서리": "accessories",
    "가방": "bag",
    "패션잡화": "fashion",
    "모자": "hat",
    "뷰티": "beauty",
    "식품": "food",
    "생활/리빙": "home",
    "의료용품": "medical",
    "산업/안전용품": "industrial",
    "패션의류": "fashion",
    "AI": "ai technology",
    "챗GPT": "ai chatbot",
    "파이썬": "programming",
    "커피": "coffee",
    "홈카페": "coffee",
    "운동": "workout",
    "홈트": "home workout",
    "건강": "healthy",
    "재테크": "money",
    "저축": "savings",
    "독서": "reading",
    "영화": "movie",
    "넷플릭스": "streaming",
    "요리": "cooking",
    "아침식사": "breakfast",
    "스마트폰": "smartphone",
    "생산성": "productivity",
    "루틴": "morning routine",
    "자기계발": "self improvement",
}


def _translate_for_video(keyword: str) -> str:
    return KOREAN_TO_EN_KEYWORDS.get(keyword.strip(), "")


def _extract_search_keywords(topic: str, tags: list[str] | None = None) -> list[str]:
    """검색용 키워드 후보 리스트 (우선순위 순)."""
    candidates = []
    if tags:
        for tag in tags:
            if tag and tag not in ("쇼핑팁", "생활/리빙", "산업/안전용품"):
                candidates.append(tag)
    if len(topic) <= 20:
        candidates.append(topic)
    else:
        first = topic.split()[0] if topic.split() else topic
        first = first.split("/")[0].split(",")[0].strip()
        if first and len(first) <= 20:
            candidates.append(first)
    seen = set()
    unique = []
    for k in candidates:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _extract_video_keywords(topic: str, tags: list[str] | None = None) -> list[str]:
    """비디오 전용 키워드 — Pixabay는 서양 콘텐츠 위주라 영어로 매핑."""
    candidates = []
    if tags:
        for tag in tags:
            en = _translate_for_video(tag)
            if en:
                candidates.append(en)
    ko_candidates = _extract_search_keywords(topic, tags)
    for kw in ko_candidates:
        en = _translate_for_video(kw)
        if en and en not in candidates:
            candidates.append(en)
    seen = set()
    unique = []
    for k in candidates:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def resolve_image(
    topic: str,
    image_url: str = "",
    tags: list[str] | None = None,
) -> tuple[str, str] | None:
    """토픽/명시적 URL → (image_url, alt). 없으면 태그 기반 Pixabay 검색."""
    if image_url:
        return image_url, topic
    for keyword in _extract_search_keywords(topic, tags):
        result = search_pixabay(keyword)
        if result:
            print(f"[이미지 검색 성공 키워드] {keyword}")
            return result
    return None


def insert_image(html_str: str, image_url: str, alt: str, caption: str = "") -> str:
    img = _make_img_tag(image_url, alt, caption)
    head, tail = _first_h2_or_top(html_str)
    if not head:
        return img + "\n" + html_str
    return head + "\n" + img + "\n" + tail


def insert_image_at_nth_h2(html_str: str, n: int, image_url: str, alt: str) -> str:
    """n번째 <h2> 앞에 이미지 삽입 (1부터 시작)."""
    img = _make_img_tag(image_url, alt)
    parts = html_str.split("<h2>")
    if len(parts) <= n:
        return html_str + "\n" + img
    return "<h2>".join(parts[:n]) + "\n" + img + "\n<h2>" + "<h2>".join(parts[n:])


def _make_video_tag(video: dict, keyword: str) -> str:
    url = html.escape(video["url"])
    thumb = html.escape(video.get("thumbnail", ""))
    user = html.escape(video.get("user", ""))
    page = html.escape(video.get("page_url", ""))
    credit = ""
    if user and page:
        credit = f'<figcaption style="font-size:12px;color:#888;text-align:center;margin-top:4px;">Video by <a href="{page}" target="_blank" rel="noopener">{user}</a> on Pixabay</figcaption>'
    return (
        f'<figure style="margin:24px 0;text-align:center;">'
        f'<video controls preload="metadata" poster="{thumb}" '
        f'style="max-width:100%;height:auto;border-radius:8px;">'
        f'<source src="{url}" type="video/mp4">'
        f'브라우저가 비디오를 지원하지 않습니다.</video>'
        f'{credit}</figure>'
    )


def insert_video(html_str: str, video: dict, keyword: str) -> str:
    """비디오를 두 번째 <h2> 뒤에 삽입 (본문 중간)."""
    tag = _make_video_tag(video, keyword)
    parts = html_str.split("</h2>")
    if len(parts) >= 3:
        return "</h2>".join(parts[:2]) + "</h2>\n" + tag + "\n" + "</h2>".join(parts[2:])
    return html_str + "\n" + tag


def build_post_body(post: Post) -> dict:
    """Blogger API용 body 생성. 검색 설명 customMetaData에 첨부."""
    return {
        "kind": "blogger#post",
        "title": post.title,
        "content": post.html,
        "labels": post.labels,
    }


def _make_cta_block(product_url: str) -> str:
    """구매 페이지로 이동하는 CTA 블록. 새 창으로 열림."""
    safe_url = html.escape(product_url)
    return (
        '<div style="margin:32px 0;padding:20px;background:linear-gradient(135deg,#fff4e6,#ffe4c7);'
        'border:1px solid #ffb347;border-radius:12px;text-align:center;">'
        '<p style="margin:0 0 12px 0;font-size:15px;color:#8b4513;font-weight:600;">'
        '🛒 이 상품이 필요하신가요?</p>'
        '<p style="margin:0 0 16px 0;font-size:14px;color:#666;">'
        '다있지창고에서 합리적인 가격에 만나보세요.</p>'
        f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer sponsored" '
        'style="display:inline-block;padding:12px 28px;background:#ff6b35;color:#fff;'
        'text-decoration:none;border-radius:24px;font-weight:600;font-size:15px;">'
        '다있지창고에서 구매하기 →</a></div>'
    )


def insert_cta(html_str: str, product_url: str) -> str:
    """CTA를 본문 중간(2번째 h2 앞)과 하단 두 곳에 삽입."""
    cta = _make_cta_block(product_url)
    parts = html_str.split("<h2>")
    if len(parts) >= 3:
        mid = "<h2>".join(parts[:2]) + cta + "\n<h2>" + "<h2>".join(parts[2:])
        return mid + "\n" + cta
    return html_str + "\n" + cta


def generate_and_publish(
    topic: str,
    tags: list[str],
    image_url: str = "",
    product_url: str = "",
    tone: str = "친근하고 정보성 있는",
    as_draft: bool = True,
) -> dict:
    """토픽 → LLM 생성 → 이미지 삽입 → Blogger 발행 (초안 또는 게시)."""
    post = generate_post(topic, tone=tone, labels=tags)

    use_dalle = os.environ.get("USE_DALLE_IMAGES", "1") != "0" and post.image_prompts
    dalle_images = generate_dalle_images(post.image_prompts) if use_dalle else []

    if len(dalle_images) >= 1:
        url, alt = dalle_images[0]
        post.html = insert_image(post.html, url, alt)
        print("[DALL-E 이미지 1] 도입부 삽입")
    else:
        img = resolve_image(topic, image_url, tags=tags)
        if img:
            url, alt = img
            post.html = insert_image(post.html, url, alt)
            print(f"[이미지] Pixabay: {url[:80]}")
        else:
            print("[이미지] 이미지 소스 없음")

    if len(dalle_images) >= 2:
        url2, alt2 = dalle_images[1]
        post.html = insert_image_at_nth_h2(post.html, 3, url2, alt2)
        print("[DALL-E 이미지 2] 본문 중간 삽입")

    if os.environ.get("EMBED_VIDEO", "1") != "0":
        video = None
        video_keywords = _extract_video_keywords(topic, tags)
        if not video_keywords:
            print("[비디오] 매핑 가능한 영어 키워드 없음 → 비디오 스킵")
        else:
            for kw in video_keywords:
                video = search_pixabay_video(kw)
                if video:
                    print(f"[비디오 검색 성공 키워드] {kw}")
                    break
            if video:
                post.html = insert_video(post.html, video, topic)
                print(f"[비디오] {video['url']}")
            else:
                print(f"[비디오] 매칭 실패 (시도: {video_keywords})")

    if product_url:
        post.html = insert_cta(post.html, product_url)
        print(f"[구매 CTA] {product_url}")

    service = get_blogger_service()
    result = service.posts().insert(
        blogId=os.environ["BLOG_ID"],
        body=build_post_body(post),
        isDraft=as_draft,
    ).execute()

    result["_post"] = {
        "title": post.title,
        "meta_description": post.meta_description,
        "keywords": post.keywords,
    }
    return result
