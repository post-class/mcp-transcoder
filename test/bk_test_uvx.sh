#!/usr/bin/env bash
set -Eeuo pipefail

# uvx で実行可能かをテストするスクリプト
# - .env の TEST_URL_PLAYWRIGHT を読み取り、コマンドの ${TEST_URL_PLAYWRIGHT} を置換して実行
# - 実行は長時間ブロックするため、短時間のタイムアウト付きで起動確認のみを行う

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Package version (constant)
MCP_TRANSCODER_VERSION="0.1.0"

# .env を読み込んで TEST_URL_PLAYWRIGHT を取得
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck source=/dev/null
  set -a; source "${ROOT_DIR}/.env"; set +a
fi

URL="${TEST_URL_PLAYWRIGHT:-}"
if [[ -z "${URL}" ]]; then
  echo "[ERROR] TEST_URL_PLAYWRIGHT is not set in .env" >&2
  exit 1
fi

# キャッシュ対策
export UV_CACHE_DIR="${ROOT_DIR}/.uv_cache"
export TMPDIR="${ROOT_DIR}/.uv_tmp"
mkdir -p "${UV_CACHE_DIR}" "${TMPDIR}"

CMD=(uvx --isolated --no-cache "mcp-transcoder@${MCP_TRANSCODER_VERSION}" --insecure --timeout 300 "${URL}")
echo "Running: ${CMD[*]}" >&2

# timeout が利用可能なら使用し、0(正常)または124(タイムアウト)を成功扱いとする
if command -v timeout >/dev/null 2>&1; then
  set +e
  timeout 8s "${CMD[@]}"
  status=$?
  set -e
  if [[ ${status} -ne 0 && ${status} -ne 124 ]]; then
    echo "[ERROR] Command failed with status ${status}" >&2
    exit ${status}
  fi
else
  # timeout がない環境向けのフォールバック: バックグラウンド起動して短時間後にkill
  "${CMD[@]}" &
  pid=$!
  # 少し待って起動エラーがないことを確認
  sleep 3
  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "[ERROR] Process exited prematurely" >&2
    exit 1
  fi
  # 後始末
  kill "${pid}" 2>/dev/null || true
fi

echo "OK: uvx executed successfully (startup verified)" >&2

# list_tools の結果表示（mcp クライアントで stdio 接続）
echo "Querying list_tools via stdio client..." >&2

set +e
UV_CACHE_DIR="${UV_CACHE_DIR}" MCP_TRANSCODER_VERSION="${MCP_TRANSCODER_VERSION}" URL="${URL}" \
  uv run -q python - <<'PY'
import os, json, anyio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

URL = os.environ["URL"]
VERSION = os.environ.get("MCP_TRANSCODER_VERSION", "0.0.0")
UV_CACHE_DIR = os.environ.get("UV_CACHE_DIR")

async def main():
    server = StdioServerParameters(
        command="uvx",
        args=["--isolated", "--no-cache", f"mcp-transcoder@{VERSION}", "--insecure", "--timeout", "60", URL],
        env={"UV_CACHE_DIR": UV_CACHE_DIR} if UV_CACHE_DIR else None,
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("list_tools:")
            print(json.dumps(names, ensure_ascii=False))

anyio.run(main)
PY
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  echo "[ERROR] list_tools query failed" >&2
  exit ${rc}
fi

# call_tool("browser_navigate", {"url": "https://yahoo.co.jp"}) の結果表示
echo "Calling browser_navigate via stdio client..." >&2

set +e
UV_CACHE_DIR="${UV_CACHE_DIR}" MCP_TRANSCODER_VERSION="${MCP_TRANSCODER_VERSION}" URL="${URL}" \
  uv run -q python - <<'PY'
import os, json, anyio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

URL = os.environ["URL"]
VERSION = os.environ.get("MCP_TRANSCODER_VERSION", "0.0.0")
UV_CACHE_DIR = os.environ.get("UV_CACHE_DIR")

async def main():
    server = StdioServerParameters(
        command="uvx",
        args=["--isolated", "--no-cache", f"mcp-transcoder@{VERSION}", "--insecure", "--timeout", "60", URL],
        env={"UV_CACHE_DIR": UV_CACHE_DIR} if UV_CACHE_DIR else None,
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            if "browser_navigate" not in names:
                print("call_tool: browser_navigate not available")
                return
            res = await session.call_tool("browser_navigate", {"url": "https://yahoo.co.jp"})
            print("call_tool(browser_navigate):")
            try:
                print(json.dumps(res.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False))
            except Exception:
                # Fallback: print minimal fields
                content = getattr(res, 'content', None)
                is_error = getattr(res, 'isError', None)
                print(json.dumps({"isError": is_error, "content": content}, default=str, ensure_ascii=False))

anyio.run(main)
PY
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  echo "[ERROR] call_tool query failed" >&2
  exit ${rc}
fi
