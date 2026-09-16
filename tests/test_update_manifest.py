"""Release feeds must contain signed packages for every supported target."""

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.build_update_manifest import build_manifest, package_names

FIXTURE = Path(__file__).resolve().parents[1] / "apps/desktop/src-tauri/tests/fixtures/updater"


@pytest.fixture
def release_files(tmp_path):
    if not shutil.which("minisign"):
        pytest.skip("minisign executable required for release signature verification")
    release = {"tag_name": "v1.2.3", "body": "Changes", "assets": []}
    for name in package_names("1.2.3").values():
        for suffix, fixture in (("", "payload.txt"), (".sig", "payload.txt.sig")):
            data = (FIXTURE / fixture).read_bytes()
            file = tmp_path / (name + suffix)
            file.write_bytes(data)
            release["assets"].append(
                {
                    "name": file.name,
                    "state": "uploaded",
                    "size": len(data),
                    "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                    "browser_download_url": f"https://github.com/mhennemeyer/speccify/releases/download/v1.2.3/{file.name}",
                }
            )
    return release, tmp_path, (FIXTURE / "public.key").read_text().strip()


def test_complete_feed_verifies_actual_signatures(release_files):
    manifest = build_manifest(*release_files)
    assert manifest["version"] == "1.2.3"
    assert set(manifest["platforms"]) == {
        "darwin-aarch64",
        "windows-x86_64",
        "linux-x86_64",
        "linux-aarch64",
    }


def test_tampered_package_fails_even_with_matching_digest(release_files):
    release, directory, _ = release_files
    asset = release["assets"][0]
    data = b"modified package"
    (directory / asset["name"]).write_bytes(data)
    asset.update(size=len(data), digest="sha256:" + hashlib.sha256(data).hexdigest())
    with pytest.raises(subprocess.CalledProcessError):
        build_manifest(*release_files)


def test_missing_platform_does_not_publish_partial_feed(release_files):
    release_files[0]["assets"].pop()
    with pytest.raises(KeyError):
        build_manifest(*release_files)


def test_wrong_download_origin_is_rejected(release_files):
    release_files[0]["assets"][0]["browser_download_url"] = "https://example.invalid/package"
    with pytest.raises(ValueError, match="Unexpected download URL"):
        build_manifest(*release_files)


@pytest.mark.parametrize("version", ["v1.2.3", "1.2.3-beta", "1.2/../3", "latest"])
def test_only_stable_release_versions(version):
    with pytest.raises(ValueError):
        package_names(version)
