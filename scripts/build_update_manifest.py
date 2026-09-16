"""Validate signed release packages and assemble one complete Tauri update feed."""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


def package_names(version: str) -> dict[str, str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Expected a stable release version")
    return {
        "darwin-aarch64": "Speccify_aarch64.app.tar.gz",
        "windows-x86_64": f"Speccify_{version}_x64-setup.exe",
        "linux-x86_64": f"Speccify_{version}_amd64.AppImage",
        "linux-aarch64": f"Speccify_{version}_aarch64.AppImage",
    }


def build_manifest(release: dict, directory: Path, public_key: str) -> dict:
    tag = release["tag_name"]
    if not tag.startswith("v"):
        raise ValueError("Release tag must start with v")
    version = tag[1:]
    names = package_names(version)
    assets = {asset["name"]: asset for asset in release["assets"]}
    platforms = {}
    with tempfile.TemporaryDirectory() as temp:
        public = Path(temp) / "public.key"
        public.write_bytes(base64.b64decode(public_key, validate=True))
        for platform, name in names.items():
            asset = assets[name]
            signature_asset = assets[name + ".sig"]
            for item in (asset, signature_asset):
                path = directory / item["name"]
                if item["state"] != "uploaded" or path.stat().st_size != item["size"]:
                    raise ValueError(f"Incomplete artifact: {item['name']}")
                digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != item["digest"]:
                    raise ValueError(f"Digest mismatch: {item['name']}")
            signature = (directory / (name + ".sig")).read_text().strip()
            decoded_signature = Path(temp) / "signature"
            decoded_signature.write_bytes(base64.b64decode(signature, validate=True))
            subprocess.run(
                [
                    "minisign",
                    "-Vm",
                    str(directory / name),
                    "-p",
                    str(public),
                    "-x",
                    str(decoded_signature),
                ],
                check=True,
                capture_output=True,
            )
            url = asset["browser_download_url"]
            expected = f"https://github.com/mhennemeyer/speccify/releases/download/{tag}/{name}"
            if url != expected:
                raise ValueError(f"Unexpected download URL: {name}")
            platforms[platform] = {"url": url, "signature": signature}
    return {
        "version": version,
        "notes": release.get("body") or f"Speccify {version}",
        "pub_date": release.get("published_at")
        or datetime.datetime.now(datetime.timezone.utc).isoformat(),  # noqa: UP017 (runner Python 3.10)
        "platforms": platforms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(Path("apps/desktop/src-tauri/tauri.conf.json").read_text())
    result = build_manifest(
        json.loads(args.release.read_text()), args.directory, config["plugins"]["updater"]["pubkey"]
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Verified update platforms:", ", ".join(result["platforms"]))


if __name__ == "__main__":
    main()
