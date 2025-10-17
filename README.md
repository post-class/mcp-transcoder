# Overview
This tool is an adapter for situations where your MCP client only supports the STDIO protocol, but the target MCP server speaks StreamableHTTP.

## Usage
### Install
uv add mcp-transcoder

## Example MCP client configuration
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

## Prerequisites
- The MCP server must support StreamableHTTP.
- Server-Sent Events (SSE) is not supported.

## Notes
- If the server requires an API key, you can pass `--headers KEY VALUE` multiple times.
- If a custom CA certificate is required, specify `--ssl-cert-file /path/to/cacert.pem` (applies only to the MCP connection). For quick testing, you can set `--insecure` to skip HTTPS verification. The environment variable `SSL_CERT_FILE` is also supported, but `--ssl-cert-file` is recommended so the setting does not affect the entire process.

## Timeout settings
- The overall timeout for each request (initialize / list_tools / call_tool, etc.) is 120 seconds by default.
- To change it, specify `--timeout SECONDS`.
  - Example: `uvx mcp-transcoder --timeout 300 https://example/mcp`
- The same value is applied to the HTTP client (httpx) timeouts to improve stability for long-running operations.

## Command-line options

| Option | Description | Default | Example |
|---|---|---|---|
| `url` | The target StreamableHTTP MCP endpoint (required) | none (required) | `https://your_mcp_streamable_http_endpoint/mcp` |
| `-H KEY VALUE` / `--headers KEY VALUE` | Add extra HTTP headers (e.g., API keys) | none | `--headers x-api-key YOUR_API_KEY`, `--headers Authorization "Bearer YOUR_TOKEN"` |
| `--insecure` / `--no-insecure` | Disable/enable TLS certificate verification | verification enabled (`--no-insecure`) | Disable: `--insecure` / Recommended: `SSL_CERT_FILE=/path/to/cacert.pem uvx mcp-transcoder ...` |
| `--timeout SECONDS` | Overall timeout per request (initialize/list_tools/call_tool, etc.) | `120` (or `MCP_PROXY_TIMEOUT` env var) | `--timeout 300`, `MCP_PROXY_TIMEOUT=300 uvx mcp-transcoder ...` |
| `--ssl-cert-file PATH` | CA bundle used only for MCP connections | system/default trust store | `--ssl-cert-file /path/to/cacert.pem` |
| `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` | Log verbosity | `INFO` | `--log-level DEBUG` |

## TLS verification (enterprise CA / self-signed)
- Adding `--insecure` disables certificate verification to the remote server.
  - Example: `uvx mcp-transcoder --insecure --headers x-api-key YOUR_API_KEY https://example/mcp`
- Recommended: Keep verification enabled and provide a CA certificate instead.
  - Example: `uvx mcp-transcoder --ssl-cert-file /path/to/cacert.pem https://example/mcp`
  - Note: `--ssl-cert-file` is applied only to the httpx client used for the MCP connection. It does not affect `uvx` dependency resolution (e.g., connections to PyPI).

# Tests
```
uv run pytest -q
```

# uvx cache precautions
To avoid issues caused by stale caches, pass `--isolated --no-cache` to the `uvx` command when testing.

# URLs
## PyPI
https://pypi.org/project/mcp-transcoder/
## GitHub
https://github.com/post-class/mcp-transcoder/

