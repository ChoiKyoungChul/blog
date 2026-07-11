"""Flask 웹 관리 페이지."""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

from generate_topic import generate_topic
from publish_helper import generate_and_publish
from scrape_daitg import CATEGORIES, scrape_to_topics

load_dotenv()

BASE = Path(__file__).parent
TOPICS_FILE = BASE / "topics.txt"
LOG_FILE = BASE / "posted_log.txt"
ENV_FILE = BASE / ".env"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-in-production-abc123")


# ---------- helpers ----------
def read_topics() -> list[dict]:
    if not TOPICS_FILE.exists():
        return []
    items = []
    for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.rstrip()
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        parts = [p.strip() for p in raw.split("|")]
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


def write_topics(items: list[dict]) -> None:
    lines = ["# 한 줄에 하나씩. 형식: 주제 | 태그1,태그2 | 이미지URL | 구매URL"]
    for it in items:
        tags = ",".join(it.get("tags", []))
        img = it.get("image_url", "")
        purchase = it.get("product_url", "")
        cols = [it["topic"]]
        if tags or img or purchase:
            cols.append(tags)
        if img or purchase:
            cols.append(img)
        if purchase:
            cols.append(purchase)
        lines.append(" | ".join(cols))
    TOPICS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        while len(parts) < 5:
            parts.append("")
        entries.append({
            "time": parts[0],
            "topic": parts[1],
            "id": parts[2],
            "url": parts[3],
            "source": parts[4] or "topics.txt",
        })
    return list(reversed(entries))


def update_env(updates: dict[str, str]) -> None:
    current = dotenv_values(str(ENV_FILE)) if ENV_FILE.exists() else {}
    current.update(updates)
    lines = [f"{k}={v}" for k, v in current.items() if k]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    load_dotenv(str(ENV_FILE), override=True)


def append_log(topic: str, post_id: str, url: str, source: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{topic}\t{post_id}\t{url}\t{source}\n")


# ---------- routes ----------
@app.route("/")
def dashboard():
    topics = read_topics()
    posted = read_log()
    posted_topics = {p["topic"] for p in posted}
    pending = [t for t in topics if t["topic"] not in posted_topics]
    return render_template(
        "dashboard.html",
        pending_count=len(pending),
        posted_count=len(posted),
        recent=posted[:5],
        next_topic=pending[0] if pending else None,
        auto_topic=os.environ.get("AUTO_TOPIC", "0"),
    )


@app.route("/topics", methods=["GET", "POST"])
def topics_page():
    if request.method == "POST":
        action = request.form.get("action")
        items = read_topics()

        if action == "add":
            topic = request.form.get("topic", "").strip()
            tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
            if topic:
                items.append({"topic": topic, "tags": tags})
                write_topics(items)
                flash(f"주제 추가됨: {topic}", "success")
        elif action == "delete":
            idx = int(request.form.get("index", -1))
            if 0 <= idx < len(items):
                removed = items.pop(idx)
                write_topics(items)
                flash(f"삭제됨: {removed['topic']}", "info")
        elif action == "generate":
            posted_topics = [p["topic"] for p in read_log()]
            try:
                topic, tags = generate_topic(recent=posted_topics)
                items.append({"topic": topic, "tags": tags})
                write_topics(items)
                flash(f"AI 주제 생성됨: {topic}", "success")
            except Exception as e:
                flash(f"주제 생성 실패: {e}", "error")
        elif action in ("publish_now", "draft_now"):
            idx = int(request.form.get("index", -1))
            if 0 <= idx < len(items):
                target = items[idx]
                as_draft = action == "draft_now"
                try:
                    result = generate_and_publish(
                        topic=target["topic"],
                        tags=target.get("tags", []),
                        image_url=target.get("image_url", ""),
                        product_url=target.get("product_url", ""),
                        as_draft=as_draft,
                    )
                    post_id = result.get("id", "")
                    url = result.get("url", "(초안)")
                    meta = result.get("_post", {})
                    append_log(target["topic"], post_id, url, "web-topic")
                    status = "초안 저장" if as_draft else "발행 완료"
                    flash(f"{status}: {meta.get('title', target['topic'])}", "success")
                except Exception as e:
                    flash(f"발행 실패: {e}", "error")

        return redirect(url_for("topics_page"))

    posted_topics = {p["topic"] for p in read_log()}
    items = read_topics()
    for it in items:
        it["posted"] = it["topic"] in posted_topics
    return render_template("topics.html", items=items)


@app.route("/history")
def history():
    return render_template("history.html", entries=read_log())


@app.route("/publish", methods=["GET", "POST"])
def publish_page():
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        tags_raw = request.form.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        tone = request.form.get("tone", "친근하고 정보성 있는")
        as_draft = request.form.get("draft") == "on"

        if not topic:
            flash("주제를 입력하세요", "error")
            return redirect(url_for("publish_page"))

        image_url = request.form.get("image_url", "").strip()
        product_url = request.form.get("product_url", "").strip()
        try:
            result = generate_and_publish(
                topic=topic, tags=tags, image_url=image_url,
                product_url=product_url, tone=tone, as_draft=as_draft,
            )
            post_id = result.get("id", "")
            url = result.get("url", "(초안)")
            meta = result.get("_post", {})
            append_log(topic, post_id, url, "web-manual")
            status = "초안 저장" if as_draft else "발행 완료"
            flash(f"{status}: {meta.get('title', topic)} ({url})", "success")
        except Exception as e:
            flash(f"발행 실패: {e}", "error")

        return redirect(url_for("history"))

    return render_template("publish.html")


@app.route("/run-daily", methods=["POST"])
def run_daily():
    as_draft = request.form.get("draft") == "on"
    args = [sys.executable, "daily_post.py"]
    if not as_draft:
        args.append("--publish")

    try:
        result = subprocess.run(
            args, cwd=str(BASE), capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace",
        )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            flash(f"실행 완료:\n{output[-500:]}", "success")
        else:
            flash(f"실행 실패 (코드 {result.returncode}):\n{output[-500:]}", "error")
    except Exception as e:
        flash(f"실행 오류: {e}", "error")

    return redirect(url_for("dashboard"))


@app.route("/import-daitg", methods=["GET", "POST"])
def import_daitg():
    if request.method == "POST":
        selected = request.form.getlist("categories")
        try:
            per_cat = int(request.form.get("per_category", "3"))
        except ValueError:
            per_cat = 3

        if not selected:
            flash("카테고리를 하나 이상 선택하세요", "error")
            return redirect(url_for("import_daitg"))

        try:
            new_topics = scrape_to_topics(selected, per_category=per_cat)
        except Exception as e:
            flash(f"스크래핑 실패: {e}", "error")
            return redirect(url_for("import_daitg"))

        if not new_topics:
            flash("가져온 상품이 없습니다", "info")
            return redirect(url_for("import_daitg"))

        existing = read_topics()
        existing_set = {t["topic"] for t in existing}
        added = 0
        for t in new_topics:
            if t["topic"] not in existing_set:
                existing.append({
                    "topic": t["topic"],
                    "tags": t["tags"],
                    "image_url": t.get("image_url", ""),
                    "product_url": t.get("detail_url", ""),
                })
                existing_set.add(t["topic"])
                added += 1
        write_topics(existing)
        flash(f"{added}개 주제를 topics.txt에 추가했습니다 (요청 {len(new_topics)}개 중 중복 제외)", "success")
        return redirect(url_for("topics_page"))

    grouped: dict[str, list[tuple[str, str]]] = {}
    for ca_id, (cat, sub) in CATEGORIES.items():
        grouped.setdefault(cat, []).append((ca_id, sub))
    return render_template("import_daitg.html", grouped=grouped)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        updates = {
            "LLM_PROVIDER": request.form.get("provider", ""),
            "BLOG_THEME": request.form.get("theme", ""),
            "AUTO_TOPIC": "1" if request.form.get("auto_topic") == "on" else "0",
        }
        update_env(updates)
        flash("설정 저장됨", "success")
        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        provider=os.environ.get("LLM_PROVIDER", ""),
        theme=os.environ.get("BLOG_THEME", ""),
        auto_topic=os.environ.get("AUTO_TOPIC", "0") == "1",
        has_anthropic=bool(os.environ.get("ANTHROPIC_API_KEY")),
        has_openai=bool(os.environ.get("OPENAI_API_KEY")),
        has_gemini=bool(os.environ.get("GEMINI_API_KEY")),
        blog_id=os.environ.get("BLOG_ID", ""),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
