# mcp-collision

**Predict MCP tool name collisions before your client does. Zero dependencies.**

[![Tests](https://img.shields.io/badge/tests-17%20passed-brightgreen)]() [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()

Multiple MCP servers installed side-by-side can expose tools with the same name. Clients react differently — some prefix (`server__tool`), some sanitize, some silently shadow. The collision is invisible until your agent calls the wrong tool.

This exact bug class is documented across the ecosystem: [VSCode #324992](https://github.com/microsoft/vscode/issues/324992), [VSCode Copilot #11480](https://github.com/microsoft/vscode-copilot-release/issues/11480), [CopilotKit #2409](https://github.com/CopilotKit/CopilotKit/issues/2409), [PraisonAI #2711](https://github.com/MervinPraison/PraisonAI/issues/2711), [GHSA-67q9-58vj-32qx](https://github.com/advisories/ghsa-67q9-58vj-32qx). Every one was found *after* install. mcp-collision finds them *before*.

## How it works

Reads your client's MCP config (Claude Desktop, Cursor, Cline — anything with `mcpServers`), spawns each stdio server, speaks MCP over stdio (`initialize` → `tools/list`), collects every tool name, and simulates your client's sanitization scheme:

| Client | Scheme | Collision risk |
|---|---|---|
| `claude` | `server__tool`, invalid chars → `_` | `my.server` and `my_server` collapse |
| `cursor` | `server-tool` | dots survive: `my.server-tool` ≠ `my_server-tool` |
| `cline` | `server__tool` | same collapse class as claude |
| `raw` | no prefix | any duplicate tool name collides |

## Usage

```bash
$ mcp-collision scan claude_desktop_config.json
client: claude — 3 servers, 5 tools
  my.server                  2 tools
  my_server                  2 tools
  solo                       1 tools

1 COLLISION(S):
  my_server__read_file
    <- my.server: read_file
    <- my_server: read_file

these calls are ambiguous — your client picks one, you may never know which.
$ echo $?
2
```

```bash
# CI mode: exit non-zero on any collision
$ mcp-collision scan .mcp.json --json
{"client": "claude", "total_tools": 5, "collisions": {"my_server__read_file": [...]}}
```

Config files may be JSONC (comments and trailing commas tolerated — matching what Claude Desktop and Cursor actually parse). Remote (HTTP) servers are skipped with a note; stdio servers are fully enumerated.

## CI

```yaml
- run: pip install mcp-collision
- run: mcp-collision scan .mcp.json   # fails the build on collisions
```

MIT license.
