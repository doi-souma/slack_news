"""
fetch_news.py
カテゴリ別RSSフィードからニュースを収集し、Gemini APIで選別・要約してJSONに保存する。
"""

import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import google.generativeai as genai
import yaml
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def strip_html(text: str) -> str:
    """HTMLタグを除去し、エンティティをデコードする。"""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return text.strip()


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "preferences.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_all_articles(categories: list[dict], max_per_feed: int = 8) -> list[dict]:
    """全カテゴリのRSSフィードから記事を収集する。カテゴリ情報も付与。"""
    articles = []
    seen_urls = set()

    for category in categories:
        cat_name = category["name"]
        for feed_info in category.get("rss_sources", []):
            print(f"Fetching: [{cat_name}] {feed_info['name']}")
            try:
                feed = feedparser.parse(feed_info["url"])
                for entry in feed.entries[:max_per_feed]:
                    url = entry.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    articles.append({
                        "category": cat_name,
                        "source": feed_info["name"],
                        "title": entry.get("title", ""),
                        "url": url,
                        "summary": strip_html(entry.get("summary", entry.get("description", "")))[:200],
                        "published": entry.get("published", ""),
                    })
            except Exception as e:
                print(f"  Warning: {feed_info['name']}: {e}", file=sys.stderr)
            time.sleep(0.5)

    print(f"Fetched {len(articles)} articles total.")
    return articles


def select_articles(articles: list[dict], config: dict) -> list[dict]:
    """Geminiで記事を選別する。APIが使えない場合は全記事をそのまま返す。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Returning all articles.")
        return articles

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        news_per_day = config.get("news_per_day", 7)
        keywords = [
            kw
            for cat in config.get("categories", [])
            for kw in cat.get("keywords", [])
        ]

        articles_text = "\n".join(
            f"{i+1}. [{a['category']}] {a['title']}"
            for i, a in enumerate(articles)
        )

        prompt = (
            f"以下のニュース記事リストから、情報系学生にとって重要な{news_per_day}本を選んでください。\n"
            f"特に注目するキーワード: {', '.join(keywords[:15])}\n\n"
            f"{articles_text}\n\n"
            f"選んだ記事の番号だけをJSON配列で返してください。例: [1, 5, 8, 12]"
        )

        print("Calling Gemini API (selection only)...")
        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        indices: list[int] = json.loads(raw)
        selected = [articles[i - 1] for i in indices if 1 <= i <= len(articles)]
        print(f"Selected {len(selected)} articles by Gemini.")
        return selected

    except Exception as e:
        print(f"Gemini API unavailable ({e}). Returning all articles as fallback.")
        return articles


def save_articles(articles: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")


def main() -> None:
    config = load_config()

    articles = fetch_all_articles(config["categories"])
    if not articles:
        print("No articles fetched. Exiting.")
        sys.exit(1)

    selected = select_articles(articles, config)

    output_path = Path(__file__).parent.parent / "output" / "articles.json"
    save_articles(selected, output_path)


if __name__ == "__main__":
    main()
