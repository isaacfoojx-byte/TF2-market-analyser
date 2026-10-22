import gzip
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from integrations.snapshot_archive import restore, sha256, upload


class MissingObject(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.writes = 0

    def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise MissingObject()
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, *, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body
        self.writes += 1


class SnapshotArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.contents = {
            "raw/example.csv": b"name,price\r\nhat,3\r\n",
            "processed/non_unusual/example.csv": b"name,price\nhat,3\n",
            "processed/non_unusual/quality/example.quality.json": b'{"accepted_rows": 1}',
            "processed/non_unusual/quality/example.rows.csv": b"row,status\n1,accepted\n",
        }
        for name, data in self.contents.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (self.source / ".env").write_text("DO_NOT_ARCHIVE")
        self.storage = MemoryStorage()

    def test_round_trip_preserves_bytes_reports_and_paths(self):
        result = upload(self.source, self.storage, "bucket")
        destination = self.root / "restore"
        self.assertEqual(restore(self.storage, "bucket", result["manifest"], destination), 4)
        self.assertEqual(restore(self.storage, "bucket", result["manifest"]), 4)
        for name, data in self.contents.items():
            self.assertEqual((destination / name).read_bytes(), data)
        self.assertFalse((destination / ".env").exists())

    def test_rerun_performs_no_writes_and_restore_is_idempotent(self):
        first = upload(self.source, self.storage, "bucket")
        writes = self.storage.writes
        self.assertEqual(first, upload(self.source, self.storage, "bucket"))
        self.assertEqual(writes, self.storage.writes)
        destination = self.root / "restore"
        restore(self.storage, "bucket", first["manifest"], destination)
        restore(self.storage, "bucket", first["manifest"], destination)

    def test_changed_source_creates_new_archive_preserving_old(self):
        first = upload(self.source, self.storage, "bucket")
        (self.source / "raw/example.csv").write_bytes(b"changed")
        second = upload(self.source, self.storage, "bucket")
        self.assertNotEqual(first["manifest"], second["manifest"])
        destination = self.root / "old"
        restore(self.storage, "bucket", first["manifest"], destination)
        self.assertEqual((destination / "raw/example.csv").read_bytes(), self.contents["raw/example.csv"])

    def test_corrupt_upload_does_not_publish_manifest(self):
        original_put = self.storage.put_object
        def corrupt(**kwargs):
            kwargs["Body"] = b"corrupt"
            original_put(**kwargs)
        self.storage.put_object = corrupt
        with self.assertRaisesRegex(ValueError, "verification failed"):
            upload(self.source, self.storage, "bucket")
        self.assertFalse(any("/manifests/" in key for key in self.storage.objects))

    def test_restore_rejects_corrupt_data(self):
        result = upload(self.source, self.storage, "bucket")
        key = next(key for key in self.storage.objects if key.endswith(".gz"))
        self.storage.objects[key] = gzip.compress(b"wrong")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            restore(self.storage, "bucket", result["manifest"])

    def test_restore_rejects_corrupt_manifest(self):
        result = upload(self.source, self.storage, "bucket")
        self.storage.objects[result["manifest"]] += b" "
        with self.assertRaisesRegex(ValueError, "Manifest checksum"):
            restore(self.storage, "bucket", result["manifest"])

    def test_restore_rejects_unsafe_and_duplicate_paths(self):
        result = upload(self.source, self.storage, "bucket")
        original = self.storage.objects[result["manifest"]]
        for path in ("../escape.csv", "/absolute.csv", "C:/escape.csv", "raw\\escape.csv",
                     "raw/CON", "raw/file:stream", "raw/file.", "RAW/EXAMPLE.CSV"):
            with self.subTest(path=path):
                manifest = json.loads(original)
                manifest["files"][-1]["path"] = path
                data = json.dumps(manifest).encode()
                key = f"tfanalytics/v1/manifests/{sha256(data)}.json"
                self.storage.objects[key] = data
                with self.assertRaises(ValueError):
                    restore(self.storage, "bucket", key, self.root / "restore")
                self.assertFalse((self.root / "restore").exists())

    def test_restore_refuses_overwriting_existing_file(self):
        result = upload(self.source, self.storage, "bucket")
        destination = self.root / "restore"
        (destination / "raw").mkdir(parents=True)
        target = destination / "raw/example.csv"
        target.write_bytes(b"keep me")
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            restore(self.storage, "bucket", result["manifest"], destination)
        self.assertEqual(target.read_bytes(), b"keep me")

    def test_access_denied_is_not_treated_as_missing(self):
        def denied(**kwargs):
            raise PermissionError("Access denied")
        self.storage.get_object = denied
        with self.assertRaises(PermissionError):
            upload(self.source, self.storage, "bucket")
        self.assertEqual(self.storage.writes, 0)

    def test_dry_run_and_empty_source(self):
        result = upload(self.source)
        self.assertEqual(result["files"], 4)
        self.assertFalse(result["verified"])
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, "No CSV"):
            upload(empty)


if __name__ == "__main__":
    unittest.main()
