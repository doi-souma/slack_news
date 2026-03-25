"""
fetch_news.py
カテゴリ別RSSフィードからニュースを収集し、Gemini APIで選別・要約してJSONに保存する。
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import google.generativeai as genai
import yaml
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")



def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "preferences.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_all_articles(categories: list[dict], max_per_feed: int = 5) -> list[dict]:
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
                        "category_weight": category.get("weight", 1),
                        "source": feed_info["name"],
                        "title": entry.get("title", ""),
                        "url": url,
                        "summary": entry.get("summary", entry.get("description", ""))[:150],
                        "published": entry.get("published", ""),
                    })
            except Exception as e:
                print(f"  Warning: {feed_info['name']}: {e}", file=sys.stderr)
            time.sleep(0.5)

    print(f"Fetched {len(articles)} articles total.")
    return articles


def build_prompt(articles: list[dict], config: dict) -> str:
    """preferences.yaml の gemini_prompt をベースにプロンプトを構築する。"""
    news_per_day = config.get("news_per_day", 7)

    # カテゴリ別にキーワードをまとめて追記
    category_info = "\n".join(
        f"  - {c['name']}（重要度{c['weight']}）: {', '.join(c['keywords'][:6])} など"
        for c in config.get("categories", [])
    )

    # 記事リストをテキスト化（番号付き）
    articles_text = "\n\n".join(
        f"[{i+1}] カテゴリ: {a['category']} | 出典: {a['source']}\n"
        f"タイトル: {a['title']}\n"
        f"URL: {a['url']}\n"
        f"概要: {a['summary'][:300]}"
        for i, a in enumerate(articles)
    )

    # yamlのgemini_promptを展開（{news_per_day}を置換）
    base_prompt = config.get("gemini_prompt", "").format(news_per_day=news_per_day)

    return f"""{base_prompt}

【カテゴリ別キーワード（選別の参考に）】
{category_info}

【記事リスト（全{len(articles)}件）】
{articles_text}

必ずJSON配列のみを返してください。コードブロック（```）は不要です。
出力例:
[
  {{
    "index": 1,
    "title": "記事タイトル（日本語）",
    "summary": "3文以内の要約",
    "category": "AI・テクノロジー",
    "importance": 5,
    "url": "https://...",
    "source": "媒体名",
    "tags": ["LLM", "OpenAI"]
  }}
]
"""


def select_and_summarize(articles: list[dict], config: dict) -> list[dict]:
    """Gemini APIで記事を選別・要約する。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = build_prompt(articles, config)
    print("Calling Gemini API...")

    # 429が来た場合は待機してリトライ（最大3回）
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 60 * (attempt + 1)
                print(f"Rate limited. Waiting {wait}s before retry {attempt + 2}/3...")
                time.sleep(wait)
            else:
                raise

    raw = response.text.strip()

    # コードブロックが含まれる場合は除去
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    selected: list[dict] = json.loads(raw)

    # index が含まれる場合は元記事のURLで補完（Geminiが書き換えた場合の保険）
    for item in selected:
        idx = item.get("index", 0) - 1
        if 0 <= idx < len(articles) and not item.get("url"):
            item["url"] = articles[idx]["url"]

    print(f"Selected {len(selected)} articles by Gemini.")
    return selected


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

    selected = select_and_summarize(articles, config)

    output_path = Path(__file__).parent.parent / "output" / "articles.json"
    save_articles(selected, output_path)


if __name__ == "__main__":
    main()
