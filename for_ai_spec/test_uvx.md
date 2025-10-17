uvx で実行可能かをテストするシェルスクリプトを作成してください

# 出力ファイルパス
test/test_uvx.sh

# テスト対象コマンド
```bash
uvx　mcp-transcoder@0.1.0 --insecure ${TEST_URL_PLAYWRIGHT}
```
- ${TEST_URL_PLAYWRIGHT} は.envの同じキー名の値で置換してください
- バージョン(0.1.0)はスクリプトの先頭の方で定数にして使ってください

# スクリプトで以下のテストを実施してください
## 起動テスト
「--isolated --no-cache --timeout 9」
のオプションを付けて起動して、とりあえず起動が失敗しないことのテストを実施

## list_tools テスト
list_tools の結果を表示してください
「--isolated --no-cache」は付与しないでください

## call_tool (browser_install)
call_tool の結果を表示してください
call_tool("browser_install")
「--isolated --no-cache」は付与しないでください

## call_tool (browser_navigate)
call_tool の結果を表示してください
call_tool("browser_navigate", {"url": "https://yahoo.co.jp"})
「--isolated --no-cache」は付与しないでください