# no.1
README.md にあなたが構築すべきアプリの仕様が記載されています。README.mdを参照して、pythonでアプリ実装してください。

# no.2
以下のテストコードを作成してください。
- test_code_file: test/test_local.py
- target url(streamable http mcp): http://localhost:8931/mcp
## テスト項目
- list_tools
- call_tool
- コマンドラインオプション一覧(README.md 参照)、ただし「--insecure」と「--ssl-cert-file」は別テストで実施するので不要

# no.3
test_https.md のテストコードを作成してください。

# no.4
テスト準備として「npx @playwright/mcp@latest --headless --isolated --browser=chromium --no-sandbox --port 8931」コマンドを実行して、playwright mcp を起動しておいてください。

準備完了後、no.2 と no.3 のテストを実行してください。

