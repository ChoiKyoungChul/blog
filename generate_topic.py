"""LLM으로 블로그 주제 자동 생성. 이전 발행 이력을 참고해 중복 회피."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

DEFAULT_THEME = "일상 팁, 자기계발, IT/기술, 취미, 생산성"

SYSTEM_PROMPT = (
    "당신은 한국어 블로그 바이럴 제목 전문가입니다. 네이버/구글에서 검색 유입과 클릭률(CTR)을 극대화합니다.\n\n"
    "출력은 반드시 아래 JSON 형식만 반환하세요 (설명, 마크다운 금지):\n"
    '{"topic": "제목", "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]}\n\n'
    "제목 작성 규칙 (반드시 준수):\n"
    "- 30~55자 사이\n"
    "- 검색량 높은 핵심 키워드를 반드시 포함 (예: 방법, 후기, 추천, 비교, 순위, 총정리, TOP)\n"
    "- 아래 클릭 유도 패턴 중 1~2개 활용 (자연스럽게):\n"
    "  · 숫자 활용: 'TOP 7', 'BEST 5', '5분 만에', '10년차가 알려주는'\n"
    "  · 호기심 유발: '99%가 모르는', '진짜 아는 사람만', '숨겨진', '아무도 안 알려주는'\n"
    "  · 손실 회피: '이거 모르면 손해', '~하기 전에 꼭 확인', '진짜 후회하는'\n"
    "  · 즉각 이익: '~하는 법', '~하는 꿀팁', '무료로', '돈 아끼는'\n"
    "  · 권위/증거: '전문가가 추천하는', '실사용 후기', '직접 써본'\n"
    "  · 감정 훅: '충격', '레전드', '진짜 대박', '미쳤다' (과하지 않게 1개만)\n"
    "- 낚시성 과장 금지 (콘텐츠와 어긋나는 제목 X)\n"
    "- 부제/부연 설명은 콜론(:) 또는 대시(-)로 구분 가능\n\n"
    "태그 규칙:\n"
    "- 5개, 검색량 있는 실제 검색 키워드 위주\n"
    "- 대분류 1개 + 세부 키워드 3~4개 조합"
)


def _user_prompt(theme: str, recent: list[str]) -> str:
    recent_str = "\n".join(f"- {t}" for t in recent[-30:]) if recent else "(없음)"
    return (
        f"주제 카테고리: {theme}\n\n"
        f"최근 발행한 주제 (완전히 다른 각도로):\n{recent_str}\n\n"
        "요청:\n"
        "- 위 카테고리 안에서 실제 검색량이 있을 만한 주제 1개\n"
        "- 사람들이 자주 검색하는 문제/궁금증을 해결하는 각도\n"
        "- 클릭 유도 제목 규칙 준수\n"
        "- JSON만 출력"
    )


def _try_anthropic(theme: str, recent: list[str]) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _user_prompt(theme, recent)}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[주제 생성 Anthropic 실패] {e}")
        return None


def _try_openai(theme: str, recent: list[str]) -> str | None:
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
                {"role": "user", "content": _user_prompt(theme, recent)},
            ],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[주제 생성 OpenAI 실패] {e}")
        return None


def _try_gemini(theme: str, recent: list[str]) -> str | None:
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
        resp = model.generate_content(_user_prompt(theme, recent))
        return resp.text.strip()
    except Exception as e:
        print(f"[주제 생성 Gemini 실패] {e}")
        return None


PROVIDERS = {
    "anthropic": _try_anthropic,
    "openai": _try_openai,
    "gemini": _try_gemini,
}


def generate_topic(recent: list[str] | None = None) -> tuple[str, list[str]]:
    theme = os.environ.get("BLOG_THEME", DEFAULT_THEME)
    recent = recent or []

    preferred = os.environ.get("LLM_PROVIDER", "").lower().strip()
    order = [preferred] if preferred in PROVIDERS else []
    order += [p for p in PROVIDERS if p not in order]

    raw = None
    for name in order:
        print(f"[주제 생성 시도] {name}")
        raw = PROVIDERS[name](theme, recent)
        if raw:
            break

    if not raw:
        raise RuntimeError("주제 생성에 실패했습니다. LLM 키를 확인하세요.")

    data = _parse_json(raw)
    topic = data.get("topic", "").strip()
    tags = [t.strip() for t in data.get("tags", []) if t.strip()]

    if not topic:
        raise RuntimeError(f"주제 파싱 실패: {raw}")

    return topic, tags


def _parse_json(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if match:
        s = match.group(0)
    return json.loads(s)


if __name__ == "__main__":
    topic, tags = generate_topic()
    print(f"주제: {topic}")
    print(f"태그: {tags}")
