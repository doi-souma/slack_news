"""
notify_slack.py
生成したニュースページのURLをSlackへ通知する。
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "preferences.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_articles(input_path: Path) -> list[dict]:
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)["articles"]


def build_blocks(articles: list[dict], page_url: str, config: dict) -> list[dict]:
    """Slack Block Kit形式のメッセージを組み立てる。"""
    slack_cfg = config.get("slack", {})
    news_per_day = config.get("news_per_day", 7)
    date_str = datetime.now(timezone.utc).astimezone().strftime("%Y年%m月%d日")

    # ヘッダー（preferences.yaml の message_template を使用）
    template = slack_cfg.get("message_template", "📰 *今日のニュース ({date})*\n👉 {page_url}")
    header_text = template.format(date=date_str, news_per_day=news_per_day, page_url=page_url).strip()

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text},
        },
        {"type": "divider"},
    ]

    # 記事を重要度順に並べてリスト表示
    sorted_articles = sorted(articles, key=lambda a: a.get("importance", 0), reverse=True)
    for article in sorted_articles:
        importance = article.get("importance", 0)
        stars = "★" * importance + "☆" * (5 - importance)
        category = article.get("category", "")
        title = article.get("title", "")
        summary = article.get("summary", "")
        url = article.get("url", "")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*[{category}]* {stars}\n"
                    f"*<{url}|{title}>*\n"
                    f"{summary}"
                ),
            },
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"🔗 ページ全体: <{page_url}|ニュースページを開く>　｜　Powered by Gemini & GitHub Actions"}
        ],
    })

    return blocks


def send_message(client: WebClient, channel: str, blocks: list[dict], date_str: str) -> None:
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=f"📰 今日のニュース {date_str}",  # 通知・検索用のフォールバックテキスト
            blocks=blocks,
        )
        print(f"Sent to channel: {response['channel']} (ts={response['ts']})")
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # .env から環境変数をロード（GitHub Actions では Secrets が直接渡される）
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    token = os.getenv("SLACK_API_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL")
    page_url = os.getenv("PAGE_URL", "https://example.com/news/")  # GitHub Actionsで上書き

    if not token:
        print("Error: SLACK_API_BOT_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)
    if not channel:
        print("Error: SLACK_CHANNEL is not set.", file=sys.stderr)
        sys.exit(1)

    config = load_config()

    input_path = Path(__file__).parent.parent / "output" / "articles.json"
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run fetch_news.py first.", file=sys.stderr)
        sys.exit(1)

    articles = load_articles(input_path)
    date_str = datetime.now(timezone.utc).astimezone().strftime("%Y年%m月%d日")

    client = WebClient(token=token)
    blocks = build_blocks(articles, page_url, config)
    send_message(client, channel, blocks, date_str)


if __name__ == "__main__":
    main()
