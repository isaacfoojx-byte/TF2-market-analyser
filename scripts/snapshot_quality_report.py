"""Verify cleaning reports without requiring analytics dependencies."""
import hashlib
import json
from pathlib import Path


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_quality_report(raw_path, processed_path, raw_count, processed_count):
    """Allow cleaned row removal only when a report accounts for that exact pair."""
    report_path = processed_path.parent / "quality" / f"{processed_path.stem}.quality.json"
    if not report_path.exists():
        return False
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = {
        "input_rows": raw_count, "accepted_rows": processed_count,
        "rejected_rows": raw_count - processed_count,
        "raw_sha256": file_hash(raw_path), "processed_sha256": file_hash(processed_path),
    }
    if processed_count > raw_count or any(report.get(k) != v for k, v in expected.items()):
        raise ValueError("Quality report does not match the raw/processed snapshot pair")
    if sum(report.get("rejection_counts", {}).values()) != raw_count - processed_count:
        raise ValueError("Quality report does not account for every rejected row")
    return True
