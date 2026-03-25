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
    date_str = datetime.now(timezone.utc).astimezone().strftime("%Y年%m月%d日")
    count = len(articles)

    # カテゴリ別の件数を集計
    category_counts: dict[str, int] = {}
    for a in articles:
        cat = a.get("category", "その他")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    category_summary = "　".join(f"{cat}: {n}本" for cat, n in category_counts.items())

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📰 *今日のニュース（{date_str}）*\n{category_summary}　計 *{count}本*",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"👉 <{page_url}|ニュースページを開く>",
            },
        },
    ]

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
