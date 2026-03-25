以下の設計で「個人向け自動ニュース通知システム」を実装してください。

## 構成
- GitHub Actions (cron 毎朝9時JST) でPythonスクリプトを自動実行
- RSSフィードからニュース候補を収集
- Gemini API（無料枠）で選別・要約・個人化
- 生成したHTMLをGitHub Pagesにデプロイ
- そのURLをSlack APIで通知

## ファイル構成
news_bot/
├── .github/workflows/daily-news.yml
├── config/preferences.yaml  ← 作成済み（添付）
├── scripts/fetch_news.py
├── scripts/generate_html.py
└── scripts/notify_slack.py

## preferences.yamlの内容
（ダウンロードしたファイルを添付する）

## 必要なシークレット（GitHub Secretsに登録予定）
- GEMINI_API_KEY
- SLACK_BOT_TOKEN