# 個人向け自動ニュース通知システム

## システム概要
GitHub Actions で毎朝9時15分（JST）に自動実行される個人向けニュース通知システム。
RSSフィードからニュースを収集し、カテゴリごとに新着順で選別、
HTMLページとして GitHub Pages に公開し、そのURLをSlackに通知する。

## 処理フロー
```
GitHub Actions（毎朝9時15分JST）
│
├─ 1. fetch_news.py
│       RSSフィード収集 → カテゴリごと新着5件を選別 → output/articles.json
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
├── .github/workflows/daily-news.yml  # GitHub Actions ワークフロー（cron: '15 0 * * *'）
├── config/preferences.yaml           # カテゴリ・RSSソース設定
├── scripts/
│   ├── fetch_news.py                 # RSS収集 → カテゴリごと選別 → articles.json
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
| `SLACK_API_BOT_TOKEN` | Slack API認証（`xoxb-`から始まる） | .env / GitHub Secrets |
| `SLACK_CHANNEL` | 通知先チャンネルID（`C`から始まる） | .env / GitHub Secrets |
| `PAGE_URL` | GitHub PagesのURL | GitHub Secrets |

## GitHub Secrets（登録済み）
- `SLACK_API_BOT_TOKEN`
- `SLACK_CHANNEL`
- `PAGE_URL` = `https://doi-souma.github.io/slack_news/news/`

## RSSフィードソース（config/preferences.yaml）
| カテゴリ | メディア |
|---|---|
| AI・テクノロジー | ITmedia NEWS、Zenn、Qiita |
| 政治・国際情勢 | BBC Japan、ロイター日本語版 |
| 経済・金融 | ロイター経済、東洋経済オンライン |

## 記事選別ロジック
- Gemini APIは使用しない
- カテゴリごとに新着順で上位5件を取得（`articles_per_category: 5`）
- 合計15件／日

## 画像取得
RSSエントリから以下の優先順で画像URLを抽出し、カードにサムネイルを表示する：
1. `media:thumbnail`
2. `media:content`（imageタイプ）
3. `enclosure`（image/\*タイプ）
4. summary／description内の`<img>`タグ

画像がない記事はテキストのみ表示。

## HTMLページのUI
- 背景: 白（`#fff`）
- アクセントカラー: 青系（`#2c4a6e` / `#4a7ab5` / `#7aafd4`）
- カードレイアウト: 左サムネイル＋右テキストの横並び（スマホは縦並び）

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
