#!/usr/bin/env bash
set -Eeuo pipefail

# uvx で実行可能かをテストするシェルスクリプト
# - 出力ファイル: test/test_uvx.sh
# - .env の TEST_URL_PLAYWRIGHT を読み取り、コマンドの ${TEST_URL_PLAYWRIGHT} を置換
# - 起動テスト（--isolated --no-cache --timeout 9）と list_tools / call_tool の表示を行う

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# uv キャッシュディレクトリ（プロジェクトルート配下）
export UV_CACHE_DIR="${ROOT_DIR}/.uv_cache"
mkdir -p "${UV_CACHE_DIR}"

# バージョンは定数として定義
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

###############################################################################
# 起動テスト（--isolated --no-cache --timeout 9）
###############################################################################
CMD=(uvx --isolated --no-cache "mcp-transcoder@${MCP_TRANSCODER_VERSION}" --insecure --timeout 9 "${URL}")
echo "Startup test: ${CMD[*]}" >&2

# timeout があれば使用。0 正常 / 124 タイムアウトを成功とみなす
if command -v timeout >/dev/null 2>&1; then
  set +e
  timeout 8s "${CMD[@]}"
  status=$?
  set -e
  if [[ ${status} -ne 0 && ${status} -ne 124 ]]; then
    echo "[ERROR] Startup failed with status ${status}" >&2
    exit ${status}
  fi
else
  # timeout が無い場合のフォールバック
  "${CMD[@]}" &
  pid=$!
  sleep 3
  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "[ERROR] Process exited prematurely" >&2
    exit 1
  fi
  kill "${pid}" 2>/dev/null || true
fi
echo "OK: startup did not fail" >&2

###############################################################################
# list_tools テスト（--isolated/--no-cache は付与しない）
###############################################################################
echo "Querying list_tools..." >&2

set +e
UV_CACHE_DIR="${UV_CACHE_DIR}" MCP_TRANSCODER_VERSION="${MCP_TRANSCODER_VERSION}" URL="${URL}" \
  uv run -q python - <<'PY'
import os, json, anyio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

URL = os.environ["URL"]
VERSION = os.environ.get("MCP_TRANSCODER_VERSION", "0.0.0")

async def main():
    # --isolated / --no-cache は付与しない
    server = StdioServerParameters(
        command="uvx",
        args=[f"mcp-transcoder@{VERSION}", "--insecure", URL],
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
  echo "[ERROR] list_tools test failed" >&2
  exit ${rc}
fi

###############################################################################
# call_tool テスト（--isolated/--no-cache は付与しない）
###############################################################################
echo "Calling tool: browser_install..." >&2

set +e
UV_CACHE_DIR="${UV_CACHE_DIR}" MCP_TRANSCODER_VERSION="${MCP_TRANSCODER_VERSION}" URL="${URL}" \
  uv run -q python - <<'PY'
import os, json, anyio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

URL = os.environ["URL"]
VERSION = os.environ.get("MCP_TRANSCODER_VERSION", "0.0.0")

async def main():
    # --isolated / --no-cache は付与しない
    server = StdioServerParameters(
        command="uvx",
        args=[f"mcp-transcoder@{VERSION}", "--insecure", URL],
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            if "browser_install" not in names:
                print("call_tool: browser_install not available")
                return
            res = await session.call_tool("browser_install")
            print("call_tool(browser_install):")
            try:
                print(json.dumps(res.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False))
            except Exception:
                content = getattr(res, 'content', None)
                is_error = getattr(res, 'isError', None)
                print(json.dumps({"isError": is_error, "content": content}, default=str, ensure_ascii=False))

anyio.run(main)
PY
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  echo "[ERROR] call_tool (browser_install) test failed" >&2
  exit ${rc}
fi

###############################################################################
# call_tool テスト（--isolated/--no-cache は付与しない）
###############################################################################
echo "Calling tool: browser_navigate..." >&2

set +e
UV_CACHE_DIR="${UV_CACHE_DIR}" MCP_TRANSCODER_VERSION="${MCP_TRANSCODER_VERSION}" URL="${URL}" \
  uv run -q python - <<'PY'
import os, json, anyio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

URL = os.environ["URL"]
VERSION = os.environ.get("MCP_TRANSCODER_VERSION", "0.0.0")

async def main():
    # --isolated / --no-cache は付与しない
    server = StdioServerParameters(
        command="uvx",
        args=[f"mcp-transcoder@{VERSION}", "--insecure", URL],
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
                # Fallback: 最低限のフィールドのみ出力
                content = getattr(res, 'content', None)
                is_error = getattr(res, 'isError', None)
                print(json.dumps({"isError": is_error, "content": content}, default=str, ensure_ascii=False))

anyio.run(main)
PY
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  echo "[ERROR] call_tool test failed" >&2
  exit ${rc}
fi

echo "All tests completed." >&2
