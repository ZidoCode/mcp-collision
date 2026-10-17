#!/usr/bin/env python3
import json, sys
name = sys.argv[1] if len(sys.argv)>1 else "srv"
tools = {"a": ["read_file","write_file","search"],
         "b": ["read_file","fetch_url","search"],
         "c": ["search-files","read file!","delete_all"]}
tools = tools.get(name, ["tool_one","tool_two"])
for line in sys.stdin:
    req = json.loads(line)
    if req.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":name}}}), flush=True)
    elif req.get("method") == "tools/list":
        print(json.dumps({"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":t,"description":f"tool {t} of {name}"} for t in tools]}}), flush=True)
