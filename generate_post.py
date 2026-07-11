"""LLM으로 SEO 최적화된 블로그 글 생성 (Anthropic/OpenAI/Gemini 자동 선택)."""
import json
import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Post:
    title: str
    html: str
    labels: list[str]
    meta_description: str = ""
    keywords: list[str] = field(default_factory=list)


SYSTEM_PROMPT = (
    "당신은 SEO + 체류시간 최적화 전문 한국어 블로그 작가입니다. "
    "검색 상위 노출과 낮은 이탈률을 동시에 달성합니다.\n\n"
    "출력은 반드시 아래 JSON 형식만 반환하세요 (마크다운, 코드블럭 감싸기 금지):\n"
    "{\n"
    '  "title": "클릭 유도 + 검색 키워드 조합 제목 (30~55자)",\n'
    '  "meta_description": "검색 결과에 노출될 요약 (120~155자, 핵심 키워드+호기심 유발)",\n'
    '  "keywords": ["주요 키워드", "관련 키워드", "롱테일 키워드"],\n'
    '  "html": "본문 HTML"\n'
    "}\n\n"
    "제목 규칙 (CTR 극대화):\n"
    "- 검색량 있는 핵심 키워드 반드시 포함 (방법, 후기, 추천, 비교, TOP, 순위, 총정리 등)\n"
    "- 클릭 훅 활용: 숫자(TOP 5, 5분 만에), 호기심(99%가 모르는, 진짜 아는 사람만), "
    "손실 회피(모르면 손해, 후회하는), 권위(전문가 추천, 10년차)\n"
    "- 과장 낚시는 금지 (본문에서 반드시 약속 이행)\n\n"
    "본문 SEO 규칙:\n"
    "- 첫 문단(<p>): 독자의 검색 의도를 즉시 확인 + 이 글에서 얻을 결론 요약 (이탈 방지)\n"
    "- <h2> 3~5개, 검색 세부 키워드 자연 포함\n"
    "- <h3>로 세부 구조화\n"
    "- <ul>/<ol> 리스트로 스캐닝 가독성\n"
    "- <strong>으로 핵심 문장 강조 (남용 금지)\n"
    "- 실제 예시/수치/비교 표 활용 (신뢰도 ↑)\n"
    "- 1500~2200자 분량\n"
    "- 마지막 <h2>는 'FAQ' 또는 '자주 묻는 질문'으로 Q&A 3개\n"
    "- 마무리 문단: 요약 + 명확한 다음 행동(CTA)\n"
    "- 광고성 과장 금지, 근거 있는 톤 유지\n"
)


def _user_prompt(topic: str, tone: str) -> str:
    return (
        f"주제: {topic}\n"
        f"톤: {tone}\n\n"
        "위 주제로 SEO 최적화 블로그 글을 작성하세요. JSON 형식만 출력."
    )


def _try_anthropic(topic: str, tone: str) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _user_prompt(topic, tone)}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[Anthropic 실패] {e}")
        return None


def _try_openai(topic: str, tone: str) -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(topic, tone)},
            ],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI 실패] {e}")
        return None


def _try_gemini(topic: str, tone: str) -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=SYSTEM_PROMPT,
        )
        resp = model.generate_content(_user_prompt(topic, tone))
        return resp.text.strip()
    except Exception as e:
        print(f"[Gemini 실패] {e}")
        return None


PROVIDERS = {
    "anthropic": _try_anthropic,
    "openai": _try_openai,
    "gemini": _try_gemini,
}


def _parse_json(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if match:
        s = match.group(0)
    return json.loads(s)


def _wrap_seo(html: str, keywords: list[str], meta_description: str) -> str:
    """본문 상단에 요약 박스, 하단에 스키마 마크업 추가."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "description": meta_description,
        "keywords": ", ".join(keywords),
    }
    schema_script = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
    return html + "\n" + schema_script


def generate_post(
    topic: str,
    tone: str = "친근하고 정보성 있는",
    labels: list[str] | None = None,
) -> Post:
    preferred = os.environ.get("LLM_PROVIDER", "").lower().strip()
    order = [preferred] if preferred in PROVIDERS else []
    order += [p for p in PROVIDERS if p not in order]

    raw = None
    for name in order:
        print(f"[시도] {name}")
        raw = PROVIDERS[name](topic, tone)
        if raw:
            print(f"[성공] {name}")
            break

    if not raw:
        raise RuntimeError(
            "사용 가능한 LLM이 없습니다. .env에 ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY 중 하나 이상 설정하세요."
        )

    try:
        data = _parse_json(raw)
    except Exception:
        return Post(title=topic, html=raw, labels=labels or [])

    title = (data.get("title") or topic).strip()
    meta = (data.get("meta_description") or "").strip()
    keywords = [k.strip() for k in data.get("keywords", []) if k.strip()]
    html = (data.get("html") or "").strip()
    html = _wrap_seo(html, keywords, meta)

    final_labels = list(dict.fromkeys((labels or []) + keywords))[:10]

    return Post(
        title=title,
        html=html,
        labels=final_labels,
        meta_description=meta,
        keywords=keywords,
    )


if __name__ == "__main__":
    import sys

    topic = " ".join(sys.argv[1:]) or "파이썬으로 블로그 자동화하기"
    post = generate_post(topic)
    print(f"\n[제목] {post.title}")
    print(f"[메타] {post.meta_description}")
    print(f"[키워드] {post.keywords}")
    print(f"\n{post.html[:500]}...")
