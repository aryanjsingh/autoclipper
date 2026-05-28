#!/usr/bin/env python3
"""Convert browser-extension JSON cookies to Netscape format for yt-dlp."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def json_to_netscape(cookies: list[dict]) -> str:
    lines = ["# Netscape HTTP Cookie File", "# Generated from JSON cookie export", ""]
    for cookie in cookies:
        domain = cookie.get("domain", "")
        host_only = cookie.get("hostOnly", False)
        if not host_only and domain and not domain.startswith("."):
            domain = f".{domain.lstrip('.')}"

        include_subdomains = "FALSE" if host_only else "TRUE"
        path = cookie.get("path", "/") or "/"
        secure = "TRUE" if cookie.get("secure") else "FALSE"

        if cookie.get("session") or not cookie.get("expirationDate"):
            expires = "0"
        else:
            expires = str(int(float(cookie["expirationDate"])))

        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if not name:
            continue
        lines.append("\t".join([domain, include_subdomains, path, secure, expires, name, value]))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON cookies file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Netscape cookies output")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cookies" in data:
        cookies = data["cookies"]
    elif isinstance(data, list):
        cookies = data
    else:
        print("Unsupported JSON cookie format", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json_to_netscape(cookies), encoding="utf-8")
    print(f"Wrote {len(cookies)} cookies to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
