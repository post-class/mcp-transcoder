import json
import os
import re
from pathlib import Path

import pytest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parent.parent
SERVERS_JSON = ROOT / "test" / "test_mcp_servers.json"
DOTENV = ROOT / ".env"


def _load_env_file() -> dict[str, str]:
    env: dict[str, str] = {}
    if DOTENV.exists():
        for line in DOTENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = v
    return env


def _substitute_env(value: str, mapping: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return mapping.get(key, os.environ.get(key, m.group(0)))

    return re.sub(r"\$\{([^}]+)\}", repl, value)


def _load_servers_config() -> dict:
    cfg = json.loads(SERVERS_JSON.read_text(encoding="utf-8"))
    env_map = _load_env_file()

    # 置換処理
    for name, entry in cfg.get("mcpServers", {}).items():
        new_args = []
        for a in entry.get("args", []):
            if isinstance(a, str):
                new_args.append(_substitute_env(a, env_map))
            else:
                new_args.append(a)
        entry["args"] = new_args
    # uvx をローカル実装に切り替える: uv run -q mcp-transcoder
    for name, entry in cfg.get("mcpServers", {}).items():
        if entry.get("command") == "uvx":
            entry["command"] = "uv"
            entry["args"] = ["run", "-q", "mcp-transcoder", *entry.get("args", [])[1:]]
    return cfg


def _uv_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("UV_CACHE_DIR", str(ROOT / ".uv_cache"))
    return env


async def _run_basic_checks(server_params: StdioServerParameters):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert tools.tools
            names = {t.name for t in tools.tools}
            if "browser_navigate" in names:
                # 実サーバ環境に依存するため、失敗（isError=True）も許容する
                _ = await session.call_tool("browser_navigate", {"url": "https://yahoo.co.jp"})


@pytest.mark.anyio
async def test_https_insecure():
    cfg = _load_servers_config()["mcpServers"]["my_mcp_insecure"]
    params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=_uv_env())
    await _run_basic_checks(params)


@pytest.mark.anyio
async def test_https_ssl_cert_file():
    cfg = _load_servers_config()["mcpServers"]["my_mcp_ssl_cert_file"]
    params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=_uv_env())
    await _run_basic_checks(params)


@pytest.mark.anyio
async def test_https_ssl_error():
    cfg = _load_servers_config()["mcpServers"]["my_mcp_ssl_error"]
    params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=_uv_env())
    with pytest.raises(Exception):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.list_tools()
