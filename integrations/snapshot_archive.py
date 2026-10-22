"""Compressed, content-addressed snapshot backups for S3-compatible storage.

Manifests are published only after every object passes download verification.
This module never deletes source files or remote objects.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compressed(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(data)
    return buffer.getvalue()


def safe_path(value: str) -> str:
    """Accept portable relative paths, including when restoring on Windows."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Unsafe archive path: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or part.endswith((".", " "))
           or re.search(r'[<>:"|?*\x00-\x1f]', part)
           or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", part)
           for part in parts):
        raise ValueError(f"Unsafe archive path: {value!r}")
    return value


def discover(source: Path) -> list[Path]:
    """Archive only snapshot data, never arbitrary repository configuration."""
    source = source.resolve(strict=True)
    files = []
    for folder in ("raw", "processed", "archive", "comparisons"):
        directory = source / folder
        if directory.is_symlink():
            raise ValueError(f"Symlink is not allowed: {directory}")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink is not allowed: {path}")
            if path.is_file() and path.suffix in {".csv", ".json"}:
                if not path.resolve().is_relative_to(source):
                    raise ValueError(f"Path escapes source: {path}")
                files.append(path)
    if not files:
        raise ValueError("No CSV or JSON snapshots found under raw/processed/archive/comparisons")
    return files


def get_bytes(client, bucket: str, key: str) -> bytes:
    body = client.get_object(Bucket=bucket, Key=key)["Body"]
    try:
        return body.read()
    finally:
        body.close()


def store_verified(client, bucket: str, key: str, payload: bytes, content_type: str) -> None:
    """Retry safely; never replace a conflicting object or mask access errors."""
    try:
        existing = get_bytes(client, bucket, key)
    except Exception as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code")
        if code not in {"NoSuchKey", "404", "NotFound"}:
            raise
        client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType=content_type)
        existing = get_bytes(client, bucket, key)
    if existing != payload:
        raise ValueError(f"Remote verification failed: {key}")


def upload(source: Path, client=None, bucket: str = "", prefix: str = "tfanalytics/v1") -> dict:
    """With no client, build a dry-run inventory without accessing the network."""
    source = source.resolve(strict=True)
    prefix = safe_path(prefix)
    entries = []
    total_compressed = 0
    seen = set()
    for path in discover(source):
        relative = safe_path(path.relative_to(source).as_posix())
        if relative.casefold() in seen:
            raise ValueError(f"Case-insensitive path collision: {relative}")
        seen.add(relative.casefold())
        data = path.read_bytes()
        digest = sha256(data)
        payload = compressed(data)
        key = f"{prefix}/objects/{digest}.gz"
        if client is not None:
            store_verified(client, bucket, key, payload, "application/gzip")
        entries.append({"path": relative, "sha256": digest, "size": len(data), "key": key})
        total_compressed += len(payload)
    manifest = json.dumps({"version": 1, "files": entries}, sort_keys=True, indent=2).encode()
    key = f"{prefix}/manifests/{sha256(manifest)}.json"
    if client is not None:
        store_verified(client, bucket, key, manifest, "application/json")
    return {"manifest": key, "files": len(entries),
            "source_bytes": sum(entry["size"] for entry in entries),
            "compressed_bytes": total_compressed, "verified": client is not None}


def restore(client, bucket: str, manifest_key: str, destination: Path | None = None) -> int:
    """Verify all bytes; optionally restore without overwriting different files."""
    safe_path(manifest_key)
    payload = get_bytes(client, bucket, manifest_key)
    if PurePosixPath(manifest_key).name != f"{sha256(payload)}.json":
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads(payload)
    if manifest.get("version") != 1 or not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValueError("Unsupported or empty manifest")
    prefix = manifest_key.rsplit("/manifests/", 1)[0]
    seen = set()
    # Validate every path before writing any files.
    for entry in manifest["files"]:
        relative = safe_path(entry["path"])
        if relative.casefold() in seen:
            raise ValueError(f"Duplicate archive path: {relative}")
        seen.add(relative.casefold())
        digest = entry["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or entry["key"] != f"{prefix}/objects/{digest}.gz":
            raise ValueError("Invalid object key")
        if type(entry["size"]) is not int or entry["size"] < 0:
            raise ValueError("Invalid object size")
    root = destination.resolve() if destination is not None else None
    for entry in manifest["files"]:
        payload = get_bytes(client, bucket, entry["key"])
        # Limit decompression to the size recorded in the checksummed manifest.
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
            data = stream.read(entry["size"] + 1)
        if len(data) != entry["size"] or sha256(data) != entry["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {entry['path']}")
        if root is not None:
            target = root / entry["path"]
            if not target.resolve().is_relative_to(root):
                raise ValueError(f"Restore path escapes destination: {entry['path']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError(f"Refusing to overwrite: {target}")
            else:
                with target.open("xb") as stream:
                    stream.write(data)
    return len(manifest["files"])


def storage_client():
    import boto3
    from botocore.config import Config

    endpoint = os.environ.get("SNAPSHOT_ARCHIVE_ENDPOINT_URL") or None
    if endpoint and not endpoint.startswith("https://"):
        raise ValueError("Archive endpoint must use HTTPS")
    return boto3.client("s3", endpoint_url=endpoint,
                        region_name=os.environ.get("AWS_DEFAULT_REGION") or "us-east-1",
                        config=Config(retries={"mode": "standard", "max_attempts": 5},
                                      request_checksum_calculation="when_required",
                                      response_checksum_validation="when_required"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["upload", "verify", "restore", "list"])
    parser.add_argument("--source", type=Path, default=Path("data"))
    parser.add_argument("--bucket", default=os.environ.get("SNAPSHOT_ARCHIVE_BUCKET"))
    parser.add_argument("--prefix", default=os.environ.get("SNAPSHOT_ARCHIVE_PREFIX") or "tfanalytics/v1")
    parser.add_argument("--manifest")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.command != "upload":
        parser.error("--dry-run is only supported for upload")
    if not args.dry_run and not args.bucket:
        parser.error("Set SNAPSHOT_ARCHIVE_BUCKET or --bucket")
    if args.command in {"verify", "restore"} and not args.manifest:
        parser.error("--manifest is required")
    if args.command == "restore" and args.destination is None:
        parser.error("--destination is required")
    client = None if args.dry_run else storage_client()
    if args.command == "upload":
        print(json.dumps(upload(args.source, client, args.bucket, args.prefix), indent=2))
    elif args.command == "list":
        for page in client.get_paginator("list_objects_v2").paginate(
                Bucket=args.bucket, Prefix=f"{safe_path(args.prefix)}/manifests/"):
            for item in page.get("Contents", []):
                print(item["Key"])
    else:
        count = restore(client, args.bucket, args.manifest,
                        args.destination if args.command == "restore" else None)
        print(f"Verified {count} files" + (f"; restored to {args.destination}" if args.command == "restore" else ""))


if __name__ == "__main__":
    main()
