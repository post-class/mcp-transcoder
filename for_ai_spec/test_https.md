以下の仕様でテストコードを実装して、test/test_https.py ファイルに保存してください。

# test_mcp_servers.json を読み込む
- ${xxx} は .env の同名の値で置換する
- 読み込んだ設定に合わせて期待値を設定して実行する
- それぞれ、 list_toolsを実行する
- それぞれ、 call_tool("browser_navigate", {"url": "https://yahoo.co.jp"} を実行する

## my_mcp_insecure
この設定で接続すると、https検証がスキップされるので正常稼働するテスト

## my_mcp_ssl_cert_file
pemファイルを読み込むので、httpsエラーにならず正常稼働するテスト

## my_mcp_ssl_error
--insecure がなく、pemファイルもないので、httpsエラーになる事を確認するテスト