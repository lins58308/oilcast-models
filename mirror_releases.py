#!/usr/bin/env python3
"""One-time, append-only mirror of public OilCast signed GitHub releases.

Run in the public *staging* distribution repository. It never modifies the
source repository, model contents, signatures, or the Android app.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE = "lins58308/oilcast-models"
TARGET = "lins58308/oilcast-model-delivery-staging"
MAX_BYTES = 24 * 1024 * 1024
USER_AGENT = "OilcastSignedMirror/1"


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        host = url.hostname or ""
        if url.scheme != "https" or not (
            host in {"github.com", "api.github.com", "uploads.github.com"}
            or host.endswith(".githubusercontent.com")
        ):
            raise RuntimeError("Unexpected GitHub redirect destination")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if host != urllib.parse.urlsplit(req.full_url).hostname:
            redirected.remove_header("Authorization")
        return redirected


OPENER = urllib.request.build_opener(SafeRedirect())


def call(url, token="", method="GET", data=None, content_type="application/vnd.github+json"):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=80) as response:
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f"GitHub {method} failed: HTTP {error.code}") from None
    if len(body) > MAX_BYTES:
        raise RuntimeError("Model release asset exceeds safety limit")
    if url.startswith("https://github.com/"):
        return body
    return json.loads(body) if body else None


def api(repository, route, token="", method="GET", payload=None):
    value = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    return call(f"https://api.github.com/repos/{repository}{route}", token, method, value)


def all_source_releases():
    releases = []
    for page in range(1, 11):
        batch = api(SOURCE, f"/releases?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError("Failed to list public model releases")
        releases.extend(batch)
        if len(releases) > 500:
            raise RuntimeError("More releases than safety limit")
        if len(batch) < 100:
            break
    chosen = [r for r in releases if not r.get("draft") and
              (re.fullmatch(r"model-\d+-\d+", r["tag_name"]) or
               r["tag_name"] == "training-checkpoint")]
    if not chosen or not any(r["tag_name"] == "training-checkpoint" for r in chosen):
        raise RuntimeError("Signed releases or cloud training checkpoint missing")
    return list(reversed(chosen))


def expected_assets(row):
    expected = {"checkpoint.json"} if row["tag_name"] == "training-checkpoint" else {"model.json", "envelope.json"}
    available = {asset["name"] for asset in row["assets"]}
    if available != expected:
        raise RuntimeError(f"Unexpected asset set for {row['tag_name']}: {available}")
    return expected


def source_asset(asset):
    url = asset.get("browser_download_url", "")
    if not url.startswith(f"https://github.com/{SOURCE}/releases/download/"):
        raise RuntimeError("Unexpected source asset URL")
    body = call(url)
    if body is None or len(body) != asset["size"]:
        raise RuntimeError(f"Source asset download incomplete: {asset['name']}")
    return body


def target_asset(asset, tag):
    url = f"https://github.com/{TARGET}/releases/download/{urllib.parse.quote(tag)}/{asset['name']}"
    return call(url)


def mirror_one(source, token):
    tag = source["tag_name"]
    expected = expected_assets(source)
    existing = api(TARGET, "/releases/tags/" + urllib.parse.quote(tag, safe=""), token)
    if existing is None:
        existing = api(TARGET, "/releases", token, "POST", {
            "tag_name": tag, "name": source["name"],
            "body": "Signed public OilCast cloud-model download mirror.",
            "draft": True, "prerelease": source["prerelease"],
            "make_latest": "false",
        })
    present = {a["name"]: a for a in existing.get("assets", [])}
    if not set(present).issubset(expected):
        raise RuntimeError(f"Unexpected target assets for {tag}")
    for asset in source["assets"]:
        name = asset["name"]
        original = source_asset(asset)
        digest = hashlib.sha256(original).hexdigest()
        if name in present:
            # Existing published release assets must be immutable and identical.
            if existing.get("draft"):
                # Draft assets are not anonymously downloadable. Compare sizes
                # and fail closed before touching existing bytes.
                if present[name]["size"] != len(original):
                    raise RuntimeError(f"Pre-existing draft asset size mismatch: {tag}/{name}")
                continue
            copy = target_asset(present[name], tag)
            if copy is None or hashlib.sha256(copy).hexdigest() != digest:
                raise RuntimeError(f"Pre-existing target asset differs: {tag}/{name}")
            continue
        upload_url = existing["upload_url"].split("{", 1)[0]
        upload_url += "?name=" + urllib.parse.quote(name)
        uploaded = call(upload_url, token, "POST", original, "application/octet-stream")
        if not isinstance(uploaded, dict) or uploaded.get("size") != len(original):
            raise RuntimeError(f"Upload failed: {tag}/{name}")
    if existing.get("draft"):
        api(TARGET, f"/releases/{existing['id']}", token, "PATCH", {
            "draft": False, "make_latest": "false"})
    # Read back the published binary after all assets exist.
    for asset in source["assets"]:
        original = source_asset(asset)
        published = target_asset(asset, tag)
        if published is None or hashlib.sha256(original).digest() != hashlib.sha256(published).digest():
            raise RuntimeError(f"Published checksum mismatch: {tag}/{asset['name']}")
    print("Verified public model release", tag, ", assets:", ", ".join(sorted(expected)), flush=True)


def main():
    if os.environ.get("GITHUB_REPOSITORY") != TARGET:
        raise RuntimeError("This migration can only run in the staging distribution repository")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN required")
    newest = api(SOURCE, "/releases/latest")
    if not newest or not re.fullmatch(r"model-\d+-\d+", newest["tag_name"]):
        raise RuntimeError("Cannot identify latest signed model release")
    models = all_source_releases()
    print(f"Mirroring {len(models)} public releases; latest {newest['tag_name']}", flush=True)
    for row in models:
        mirror_one(row, token)
    release = api(TARGET, "/releases/tags/" + urllib.parse.quote(newest["tag_name"]), token)
    api(TARGET, f"/releases/{release['id']}", token, "PATCH", {"make_latest": "true"})
    mirrored = api(TARGET, "/releases/latest")
    if mirrored["tag_name"] != newest["tag_name"]:
        raise RuntimeError("Mirrored latest tag does not match source")
    print("SUCCESS: latest signed model and all release assets mirrored", flush=True)


if __name__ == "__main__":
    main()
