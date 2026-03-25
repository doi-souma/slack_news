"""
generate_html.py
output/articles.json を読み込み、Jinja2テンプレートでHTMLを生成する。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "preferences.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_articles(input_path: Path) -> dict:
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def format_date(iso_str: str) -> str:
    """ISO 8601の日時文字列を読みやすい形式に変換する。"""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        jst_offset = 9 * 3600
        dt_jst = datetime.fromtimestamp(dt.timestamp() + jst_offset)
        return dt_jst.strftime("%Y年%m月%d日 %H:%M JST")
    except Exception:
        return iso_str


def render_html(articles: list[dict], config: dict, generated_at: str) -> str:
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    template = env.get_template("news.html.j2")

    # カテゴリの出現順を preferences.yaml の順序に合わせる
    category_order = [c["name"] for c in config.get("categories", [])]

    return template.render(
        date=format_date(generated_at),
        generated_at=format_date(generated_at),
        articles=articles,
        categories=category_order,
    )


def main() -> None:
    config = load_config()

    input_path = Path(__file__).parent.parent / "output" / "articles.json"
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} が見つかりません。先に fetch_news.py を実行してください。")

    data = load_articles(input_path)
    articles = data["articles"]
    generated_at = data["generated_at"]

    html = render_html(articles, config, generated_at)

    output_path = Path(__file__).parent.parent / "output" / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML generated: {output_path}")


if __name__ == "__main__":
    main()
