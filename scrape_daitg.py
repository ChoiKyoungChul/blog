"""daitg.kr 카테고리에서 상품명 스크래핑 → 블로그 주제로 변환."""
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://daitg.kr/daitg/shop/list.php"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CATEGORIES = {
    "1011": ("패션의류", "액세서리"),
    "1070": ("패션의류", "가방"),
    "1080": ("패션의류", "패션잡화"),
    "1090": ("패션의류", "모자"),
    "2010": ("뷰티", "스킨케어"),
    "2011": ("뷰티", "미용소품"),
    "2030": ("뷰티", "마스크팩"),
    "2040": ("뷰티", "선케어"),
    "2050": ("뷰티", "메이크업"),
    "2060": ("뷰티", "향수"),
    "2070": ("뷰티", "헤어케어"),
    "2080": ("뷰티", "바디케어"),
    "2090": ("뷰티", "네일용품"),
    "3011": ("식품", "헬스용품"),
    "3030": ("식품", "다이어트식품"),
    "3040": ("식품", "홍삼·건강즙"),
    "3050": ("식품", "음료·차"),
    "3060": ("식품", "간편식"),
    "3070": ("식품", "과자·간식"),
    "3080": ("식품", "견과류"),
    "3090": ("식품", "건강용품"),
    "5010": ("생활/리빙", "주방용품"),
    "5011": ("생활/리빙", "반려동물용품"),
    "5020": ("생활/리빙", "욕실용품"),
    "5030": ("생활/리빙", "청소용품"),
    "5040": ("생활/리빙", "세탁용품"),
    "5050": ("생활/리빙", "수납정리"),
    "5060": ("생활/리빙", "침구·커튼"),
    "5070": ("생활/리빙", "인테리어소품"),
    "5080": ("생활/리빙", "생활잡화"),
    "5090": ("생활/리빙", "문구·사무용품"),
    "6010": ("의료용품", "진단용품"),
    "6020": ("의료용품", "의료소모품"),
    "6030": ("의료용품", "응급처치용품"),
    "6040": ("의료용품", "위생용품"),
    "6050": ("의료용품", "재활용품"),
    "7010": ("산업/안전용품", "공구"),
    "7020": ("산업/안전용품", "철물"),
    "7030": ("산업/안전용품", "안전용품"),
    "7040": ("산업/안전용품", "전기용품"),
    "7050": ("산업/안전용품", "작업용품"),
}


@dataclass
class Product:
    name: str
    category: str
    subcategory: str
    ca_id: str
    image_url: str = ""
    detail_url: str = ""


def _clean_name(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"\[[^\]]+\]", "", s)  # 대괄호 제거
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip("/·,-")
    if len(s) > 60:
        s = s[:60].rsplit(" ", 1)[0]
    return s.strip()


def _extract_core_keyword(name: str) -> str:
    """상품명에서 핵심 키워드만 추출 (검색 유입용)."""
    words = re.split(r"[/\s,·]", name)
    for w in words:
        w = w.strip()
        if 2 <= len(w) <= 12 and not w.isdigit():
            return w
    return name[:12]


def _to_topic(product_name: str, subcategory: str) -> str:
    core = _clean_name(product_name)
    if not core:
        return ""
    keyword = _extract_core_keyword(core)

    templates = [
        f"{keyword} 추천 TOP 5, 후회 없는 선택 가이드",
        f"진짜 써본 {keyword} 솔직 후기와 고르는 법",
        f"{keyword} 사기 전에 꼭 봐야 할 5가지",
        f"99%가 모르는 {keyword} 200% 활용법",
        f"{subcategory} 필수템! {keyword} 실사용 후기",
        f"{keyword} 종류별 비교, 뭐가 제일 좋을까?",
        f"이거 하나면 끝! {keyword} 완벽 정리",
        f"{keyword} 저렴하게 사는 꿀팁 총정리",
        f"살까 말까 고민된다면? {keyword} 장단점 총정리",
        f"주부들이 극찬한 {keyword} BEST 5",
    ]
    idx = abs(hash(core)) % len(templates)
    return templates[idx]


def fetch_products(ca_id: str, max_items: int = 20) -> list[Product]:
    if ca_id not in CATEGORIES:
        return []
    category, subcategory = CATEGORIES[ca_id]

    resp = requests.get(BASE_URL, params={"ca_id": ca_id}, headers={"User-Agent": UA}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = set()
    products = []
    for card in soup.select("li.sct_li"):
        img_tag = card.select_one(".sct_img img")
        if not img_tag:
            continue

        name = (img_tag.get("alt") or "").strip()
        src = (img_tag.get("src") or img_tag.get("data-src") or "").strip()
        if not name or not src:
            continue

        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://daitg.kr" + src

        link = card.select_one(".sct_img a") or card.select_one(".sct_txt a")
        detail = ""
        if link:
            href = link.get("href", "")
            detail = href if href.startswith("http") else f"https://daitg.kr/daitg/shop/{href.lstrip('/')}"

        if name in seen:
            continue
        seen.add(name)

        products.append(Product(
            name=name, category=category, subcategory=subcategory,
            ca_id=ca_id, image_url=src, detail_url=detail,
        ))
        if len(products) >= max_items:
            break

    return products


def scrape_to_topics(ca_ids: list[str], per_category: int = 5) -> list[dict]:
    topics = []
    seen = set()
    for ca_id in ca_ids:
        products = fetch_products(ca_id, max_items=per_category * 2)
        added = 0
        for p in products:
            topic = _to_topic(p.name, p.subcategory)
            if not topic or topic in seen:
                continue
            seen.add(topic)
            topics.append({
                "topic": topic,
                "tags": [p.category, p.subcategory, "쇼핑팁"],
                "source_product": p.name,
                "image_url": p.image_url,
                "detail_url": p.detail_url,
            })
            added += 1
            if added >= per_category:
                break
    return topics


if __name__ == "__main__":
    import sys

    ca_ids = sys.argv[1:] or ["5010", "5030"]
    result = scrape_to_topics(ca_ids, per_category=3)
    for t in result:
        print(f"- {t['topic']}")
        print(f"  tags: {t['tags']}")
        print(f"  from: {t['source_product']}\n")
