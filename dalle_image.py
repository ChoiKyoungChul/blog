"""OpenAI DALL-E로 이미지 생성 → 압축된 base64 data URL 반환."""
import base64
import io
import os

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

DEFAULT_MODEL = "gpt-image-1"
DEFAULT_SIZE = "1024x1024"

# 모델별 quality 매핑
QUALITY_MAP = {
    "dall-e-3": "standard",
    "dall-e-2": "standard",
    "gpt-image-1": "low",  # 비용 절감 (medium/high는 더 좋지만 비쌈)
}


def _compress_to_jpeg_b64(image_bytes: bytes, max_width: int = 900, quality: int = 82) -> str:
    """PNG/PIL로 열어서 JPEG로 압축한 base64."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = bg
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(out.getvalue()).decode()


def _url_to_data_url(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        b64 = _compress_to_jpeg_b64(resp.content)
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        print(f"[이미지 다운로드 실패] {e}")
        return None


def generate_dalle_image(prompt: str, size: str = DEFAULT_SIZE) -> tuple[str, str] | None:
    """DALL-E 이미지 생성. (data_url, alt_text) 반환. 실패 시 None."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("[DALL-E] OPENAI_API_KEY 없음")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        model = os.environ.get("DALLE_MODEL", DEFAULT_MODEL)

        quality = os.environ.get("DALLE_QUALITY") or QUALITY_MAP.get(model, "low")
        resp = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        url = getattr(resp.data[0], "url", None)
        b64 = getattr(resp.data[0], "b64_json", None)

        if b64:
            raw = base64.b64decode(b64)
            compressed = _compress_to_jpeg_b64(raw)
            data_url = f"data:image/jpeg;base64,{compressed}"
        elif url:
            data_url = _url_to_data_url(url)
            if not data_url:
                return None
        else:
            return None

        alt = prompt[:120]
        return data_url, alt
    except Exception as e:
        print(f"[DALL-E 실패] {e}")
        return None


def generate_dalle_images(prompts: list[str]) -> list[tuple[str, str]]:
    """여러 프롬프트를 순차 생성. 실패한 것은 스킵."""
    results = []
    for i, prompt in enumerate(prompts, 1):
        if not prompt:
            continue
        print(f"[DALL-E 생성 {i}/{len(prompts)}] {prompt[:60]}...")
        result = generate_dalle_image(prompt)
        if result:
            results.append(result)
            print(f"[DALL-E 생성 {i}] 성공 ({len(result[0])} bytes)")
        else:
            print(f"[DALL-E 생성 {i}] 실패")
    return results


if __name__ == "__main__":
    import sys

    prompt = " ".join(sys.argv[1:]) or "A cozy morning coffee scene, warm lighting, minimalist style, no text, no logos"
    result = generate_dalle_image(prompt)
    if result:
        print(f"Data URL length: {len(result[0])} bytes")
        print(f"Alt: {result[1]}")
    else:
        print("생성 실패")
