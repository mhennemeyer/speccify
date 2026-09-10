"""Read-only smoke test for the local Rust MCP HTTP boundary; never calls tools."""

import argparse
import http.client
import json
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect-server", required=True)
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}:
        parser.error("Use an explicit local http://127.0.0.1:<port> endpoint.")

    def request(method, body=None, headers=None):
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        try:
            connection.request(
                method,
                url.path or "/",
                body,
                headers or {},
            )
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    initialize = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "boundary-smoke", "version": "1"},
            },
        }
    )
    code, body = request("POST", initialize, headers)
    assert code == 200, (code, body)
    assert json.loads(body)["result"]["serverInfo"]["name"] == args.expect_server
    code, body = request(
        "POST",
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        headers,
    )
    assert (code, body) == (202, b""), (code, body)
    code, body = request(
        "POST", json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}), headers
    )
    assert code == 200 and isinstance(json.loads(body)["result"]["tools"], list)
    print("PASS native initialize → initialized → tools/list")

    for method, extra, expected in [
        ("GET", {"Origin": "https://evil.example"}, 403),
        ("POST", {"Origin": "https://evil.example"}, 403),
        ("POST", {"Origin": "null"}, 403),
        ("POST", {"Origin": "http://localhost:1420"}, 403),
        ("POST", {"Host": "evil.example"}, 403),
        ("POST", {"Host": "127.0.0.1:1"}, 403),
        ("POST", {"Content-Type": "text/plain"}, 415),
        ("DELETE", {}, 405),
        ("OPTIONS", {}, 405),
        ("POST", {"Content-Length": str(1024 * 1024 + 1), "Expect": "100-continue"}, 413),
    ]:
        payload = None if "Expect" in extra or method == "GET" else initialize
        code, body = request(method, payload, {**headers, **extra})
        assert code == expected, (method, extra, code, body)
        print(f"PASS {method} {extra}: HTTP {code}")


if __name__ == "__main__":
    main()
