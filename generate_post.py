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
    image_prompts: list[str] = field(default_factory=list)


SYSTEM_PROMPT = (
    "당신은 SEO + 체류시간 최적화 전문 한국어 블로그 작가입니다. "
    "검색 상위 노출과 낮은 이탈률을 동시에 달성합니다.\n\n"
    "출력은 반드시 아래 JSON 형식만 반환하세요 (마크다운, 코드블럭 감싸기 금지):\n"
    "{\n"
    '  "title": "클릭 유도 + 검색 키워드 조합 제목 (30~55자)",\n'
    '  "meta_description": "검색 결과에 노출될 요약 (120~155자, 핵심 키워드+호기심 유발)",\n'
    '  "keywords": ["주요 키워드", "관련 키워드", "롱테일 키워드"],\n'
    '  "image_prompts": ["첫 번째 대표 이미지 생성용 영어 프롬프트 (본문 도입부 시각화)", "두 번째 보조 이미지 프롬프트 (본문 중반 핵심 개념 시각화)"],\n'
    '  "html": "본문 HTML"\n'
    "}\n\n"
    "image_prompts 규칙:\n"
    "- 반드시 영어로 작성 (DALL-E는 영어에 최적화)\n"
    "- 각 프롬프트는 30~80단어\n"
    "- 스타일 지시 포함 (예: 'photorealistic', 'modern flat illustration', 'clean minimalist style', 'warm lighting')\n"
    "- 텍스트/로고/워터마크 금지 문구 포함 ('no text, no logos')\n"
    "- 한국 문화에 어색한 표현 지양 (자연스러운 아시아/글로벌 톤)\n"
    "- 본문의 핵심 시각적 요소를 반영\n\n"
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
    "- 광고성 과장 금지, 근거 있는 톤 유지\n\n"
    "문장 스타일 다양화 규칙 (매우 중요):\n"
    "- 매번 다른 도입 패턴 사용, 아래 예시에서 골고루 활용:\n"
    "  · 인사형: '오늘은 ~에 대해 알아볼게요', '~에 대해 정리해봤어요', '~를 소개해드릴게요'\n"
    "  · 질문형: '혹시 ~로 고민하신 적 있으신가요?', '~이 어렵게 느껴지시나요?'\n"
    "  · 공감형: '많은 분들이 ~때문에 힘들어하시는데요', '저도 예전에 같은 문제가 있었어요'\n"
    "  · 통계형: '~한 사람 중 70%가 모르는 사실이 있어요', '최근 조사에 따르면'\n"
    "  · 스토리형: '얼마 전 지인이 ~라며 물어봤어요', '한 독자분이 ~한 사연을 보내주셨는데요'\n"
    "  · 결론형: '결론부터 말씀드리면 ~입니다', '핵심만 말씀드릴게요'\n"
    "- 문장 종결어미 다양화 (한 종류 3회 초과 반복 금지):\n"
    "  · '~합니다', '~입니다' (격식)\n"
    "  · '~해요', '~이에요/예요' (친근)\n"
    "  · '~답니다', '~더라고요', '~네요' (경험 공유)\n"
    "  · '~겠죠?', '~잖아요' (공감 유도)\n"
    "- 접속사/전환 표현 다양화:\n"
    "  · '그런데', '하지만', '반면에', '다만'\n"
    "  · '한편', '참고로', '덧붙이자면', '무엇보다도'\n"
    "  · '먼저', '우선', '다음으로', '마지막으로'\n"
    "- 독자 호명 표현 섞기: '여러분', '독자분', '~하시는 분', '이 글을 읽는 분이라면'\n"
    "- 리스트 앞에는 반드시 도입 문장 (예: '핵심 포인트를 정리하면 다음과 같아요.')\n"
    "- 같은 문장 구조 3회 연속 금지 (기계적 반복 방지)\n"
    "- <h2> 아래 첫 문장은 소제목을 반복하지 말고 다른 표현으로 시작\n"
)


REVIEW_INSTRUCTIONS = (
    "\n\n[후기 글 특별 지시]\n"
    "제목에 '후기' 또는 '리뷰'가 포함되어 있습니다. 반드시 아래 후기 스타일로 작성하세요:\n"
    "- 1인칭 시점 ('제가', '저는', '직접 써보니')\n"
    "- 구매 계기 → 첫인상 → 실사용 경험 → 장점 → 단점 → 추천 여부 순서로 구성\n"
    "- <h2> 소제목 예시:\n"
    "  · '제가 이 제품을 구매하게 된 이유'\n"
    "  · '개봉하자마자 느낀 첫인상'\n"
    "  · '실제로 써보니 이런 점이 좋았어요'\n"
    "  · '아쉬웠던 점, 솔직하게 말씀드릴게요'\n"
    "  · '다른 제품과 비교하면?'\n"
    "  · '별점과 최종 추천 의견'\n"
    "- 구체적 사용 상황 묘사 (며칠 사용, 어디에 놓고 썼는지, 함께 쓴 물건 등)\n"
    "- 감정 표현 자연스럽게 (놀랐어요, 만족스러워요, 살짝 아쉬웠어요)\n"
    "- 5점 만점 별점 포함 (⭐로 표시)\n"
    "- 어떤 사람에게 추천하는지 구체적으로 명시\n"
    "- 광고성 톤 지양, 솔직한 개인 리뷰 느낌 유지\n"
    "- 마지막에 '이런 분께 추천드려요' 리스트 (3~4개)\n"
)


def _user_prompt(topic: str, tone: str) -> str:
    extra = REVIEW_INSTRUCTIONS if ("후기" in topic or "리뷰" in topic) else ""
    return (
        f"주제: {topic}\n"
        f"톤: {tone}\n"
        f"{extra}\n"
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
    image_prompts = [p.strip() for p in data.get("image_prompts", []) if p.strip()][:2]
    html = (data.get("html") or "").strip()
    html = _wrap_seo(html, keywords, meta)

    final_labels = list(dict.fromkeys((labels or []) + keywords))[:10]

    return Post(
        title=title,
        html=html,
        labels=final_labels,
        meta_description=meta,
        keywords=keywords,
        image_prompts=image_prompts,
    )


if __name__ == "__main__":
    import sys

    topic = " ".join(sys.argv[1:]) or "파이썬으로 블로그 자동화하기"
    post = generate_post(topic)
    print(f"\n[제목] {post.title}")
    print(f"[메타] {post.meta_description}")
    print(f"[키워드] {post.keywords}")
    print(f"\n{post.html[:500]}...")
