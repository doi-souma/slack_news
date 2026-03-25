# 個人向け自動ニュース通知システム

## システム概要
GitHub Actions で毎朝9時（JST）に自動実行される個人向けニュース通知システム。
RSSフィードからニュースを収集し、Gemini APIで個人の興味に合った記事を選別、
HTMLページとして GitHub Pages に公開し、そのURLをSlackに通知する。

## 処理フロー
```
GitHub Actions（毎朝9時JST）
│
├─ 1. fetch_news.py
│       RSSフィード収集 → Gemini APIで記事選別 → output/articles.json
│
├─ 2. generate_html.py
│       output/articles.json → output/index.html
│
├─ 3. GitHub Pages へ output/ をデプロイ
│       → https://doi-souma.github.io/slack_news/news/
│
└─ 4. notify_slack.py
        Slackの #news チャンネルへページURLを通知
```

## ファイル構成
```
news_bot/
├── .github/workflows/daily-news.yml  # GitHub Actions ワークフロー
├── config/preferences.yaml           # カテゴリ・RSSソース・Geminiプロンプト設定
├── scripts/
│   ├── fetch_news.py                 # RSS収集 + Gemini選別 → articles.json
│   ├── generate_html.py              # articles.json → index.html（Jinja2）
│   └── notify_slack.py              # SlackへページURLを通知
├── templates/
│   └── news.html.j2                  # HTMLテンプレート（Jinja2）
├── output/                           # 生成物（.gitignoreで除外）
│   ├── articles.json
│   └── index.html
├── requirements.txt
└── .env                              # ローカル開発用（.gitignoreで除外）
```

## 環境変数
| 変数名 | 用途 | 管理場所 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API認証 | .env / GitHub Secrets |
| `SLACK_API_BOT_TOKEN` | Slack API認証（`xoxb-`から始まる） | .env / GitHub Secrets |
| `SLACK_CHANNEL` | 通知先チャンネルID（`C`から始まる） | .env / GitHub Secrets |
| `PAGE_URL` | GitHub PagesのURL | GitHub Secrets |

## GitHub Secrets（登録済み）
- `GEMINI_API_KEY`
- `SLACK_API_BOT_TOKEN`
- `SLACK_CHANNEL`
- `PAGE_URL` = `https://doi-souma.github.io/slack_news/news/`

## RSSフィードソース（config/preferences.yaml）
| カテゴリ | メディア |
|---|---|
| AI・テクノロジー | Gigazine、ITmedia AI+、CNET Japan |
| 政治・国際情勢 | BBC Japan、ロイター日本語版 |
| 経済・金融 | ロイター経済、東洋経済オンライン |

## Gemini API
- モデル: `gemini-2.0-flash`
- 用途: 記事の選別のみ（要約は生成しない）
- 処理: 記事タイトルのリストを渡し、選んだ記事番号をJSON配列で返させる
- 無料枠（Google AI Studio）: 課金なし・上限超過時はエラーで停止
- フォールバック: APIが使えない場合は全記事をそのまま表示

## ローカル開発環境
```bash
# 仮想環境を有効化
source .venv/bin/activate

# 個別実行
python scripts/fetch_news.py      # output/articles.json を生成
python scripts/generate_html.py   # output/index.html を生成
python scripts/notify_slack.py    # Slackに通知

# 終了
deactivate
```

## 今後の課題
- Gemini APIの選別精度の確認・プロンプト調整
- HTMLページのUI改善（現在は薄い青系カラーテーマ）
- 記事の重複排除ロジックの改善
- 公開日時のフォーマット統一（現在RSSの生データをそのまま表示）
