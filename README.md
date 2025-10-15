# 概要
Streamable HTTP 方式のMCPサーバをStdio方式に変換して使用できるようにするアプリです。
特徴として、強制的にステートレスにするため、mcp-session-idを毎回削除します。

## 利用方法
### インストール
uv add mcp-transcoder

## クライアントのMCP設定例
```json
{
	"mcpServers": {
		"lf-agents": {
			"command": "uvx",
			"args": [
				"mcp-transcoder",
				"--insecure",
				"--timeout",
				"300",
				"--headers",
				"x-api-key",
				"YOUR_API_KEY",
				"https://your_mcp_domain/mcp"
			]
		}
	}
}
```

## 前提条件
MCPサーバはStreamableHTTPである必要があります。
SSEには対応しておりません。


## 補足:
- APIキーが必要なサーバの場合は `--headers KEY VALUE` を複数回指定できます。
- CA証明書が必要な場合、`--ssl-cert-file /path/to/cacert.pem` を指定してください（MCP 接続時のみ適用）。テスト用に簡易実行したい場合、`--insecure` をセットすると HTTPS 検証をスキップします。環境変数 `SSL_CERT_FILE` も利用可能ですが、ツール全体へ波及させないため `--ssl-cert-file` の使用を推奨します。

## タイムアウト設定
- 各リクエスト（initialize / list_tools / call_tool など）の「全体タイムアウト」は既定で 120 秒です。
- 変更する場合は `--timeout 秒数` を指定します。
  - 例: `uvx mcp-transcoder --timeout 300 https://example/mcp`
- この値は HTTP 通信（httpx）のタイムアウトにも適用され、長い処理に対する疎通を安定化させます。

## コマンドラインオプション一覧（表）

| オプション | 意味 | 既定値 | 設定例 |
|---|---|---|---|
| `url` | 接続先の StreamableHTTP MCP エンドポイント（必須） | なし（必須） | `https://your_mcp_streamable_http_endpoint/mcp` |
| `-H KEY VALUE` / `--headers KEY VALUE` | 追加のHTTPヘッダーを付与（APIキーなど）。`mcp-session-id` は常に除去 | なし | `--headers x-api-key YOUR_API_KEY`、`--headers Authorization "Bearer YOUR_TOKEN"` |
| `--insecure` / `--no-insecure` | TLS証明書検証を無効化/有効化 | 検証有効（`--no-insecure`） | 無効化: `--insecure`／推奨: `SSL_CERT_FILE=/path/to/cacert.pem uvx mcp-transcoder ...` |
| `--timeout SECONDS` | 各リクエストの全体タイムアウト秒（initialize/list_tools/call_tool等） | `120`（または `MCP_PROXY_TIMEOUT` 環境変数） | `--timeout 300`、`MCP_PROXY_TIMEOUT=300 uvx mcp-transcoder ...` |
| `--ssl-cert-file PATH` | MCP 接続時のみ使用する CA バンドル | なし（システム/既定の信頼ストア） | `--ssl-cert-file /path/to/cacert.pem` |
| `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` | ログ出力の詳細度 | `INFO` | `--log-level DEBUG` |

## TLS 検証（社内CA / 自己署名対応）
- `--insecure` を付与すると、リモートへのTLS証明書検証を無効化します。
  - 例: `uvx mcp-transcoder --insecure --headers x-api-key YOUR_API_KEY https://example/mcp`
- 推奨: 検証無効ではなく、CA証明書を指定して検証を有効のままにする
  - 例: `uvx mcp-transcoder --ssl-cert-file /path/to/cacert.pem https://example/mcp`
  - 互換: 環境変数 `SSL_CERT_FILE=/path/to/cacert.pem` も有効（未指定時のフォールバック）。
  - 補足: `--ssl-cert-file` は MCP 接続の httpx クライアントにのみ適用され、`uvx` の依存解決（PyPI への接続）には影響しません。

# url
## pypi
https://pypi.org/project/mcp-transcoder/
## git
https://github.com/post-class/mcp-transcoder/
