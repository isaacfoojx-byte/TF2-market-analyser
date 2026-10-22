# Durable snapshot archive

The archive command backs up CSV and JSON files under `raw/`, `processed/`,
`archive/`, and `comparisons/` inside a source directory. For the repository,
use `--source data`. Quality reports and row audits are included. It never deletes
local files, changes Git history, or removes remote objects.

## Set up a bucket

Create a private bucket in AWS S3, Cloudflare R2, or another S3-compatible service.
Use a dedicated bucket such as `tfanalytics-snapshots` (choose an available name).
Leave public access disabled. Do not configure expiration of archive objects.
Keep the default immediately readable storage class for initial restore testing.

Create credentials restricted to this bucket. The uploader needs object read and
write permissions; `list` also needs bucket listing permission. It does not need
delete permission. For AWS, the actions are `s3:GetObject`, `s3:PutObject`, and
`s3:ListBucket`; scope object access to `tfanalytics/v1/*`. For R2, create an Object
Read & Write API token scoped to this bucket. Keep credentials in your secret
manager or GitHub Actions secrets, never in source files or chat.

Provider setup references:

- [AWS S3 bucket creation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)
- [Cloudflare R2 bucket creation](https://developers.cloudflare.com/r2/buckets/create-buckets/)
- [R2 S3 API credentials](https://developers.cloudflare.com/r2/api/tokens/)
- [R2 boto3 endpoint configuration](https://developers.cloudflare.com/r2/examples/aws/boto3/)

Install the optional uploader dependency:

```powershell
python -m pip install -r requirements-archive.txt
```

The command uses the standard AWS credential chain, including local AWS profiles
or `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables. Temporary
credentials can additionally use `AWS_SESSION_TOKEN` locally. Configure these in
your shell using your provider's credentials. Configure the non-secret settings:

```powershell
$env:SNAPSHOT_ARCHIVE_BUCKET = 'your-bucket-name'
$env:AWS_DEFAULT_REGION = 'your-aws-region'
```

For AWS S3, leave `SNAPSHOT_ARCHIVE_ENDPOINT_URL` unset. For R2:

```powershell
$env:SNAPSHOT_ARCHIVE_ENDPOINT_URL = 'https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com'
$env:AWS_DEFAULT_REGION = 'auto'
```

Other compatible providers use their HTTPS endpoint and region. Compatibility
must be confirmed with a real upload and restore before relying on that provider.

## Backfill and test recovery

First inspect the size without credentials, boto3, or a network connection:

```powershell
python -m integrations.snapshot_archive upload --source data --dry-run
```

Back up all existing snapshots:

```powershell
python -m integrations.snapshot_archive upload --source data
```

The command prints a manifest key such as
`tfanalytics/v1/manifests/<sha256>.json`. Save the actual key in your backup records.
Use that key to verify and restore into a separate directory:

```powershell
python -m integrations.snapshot_archive verify --manifest tfanalytics/v1/manifests/ACTUAL_HASH.json
python -m integrations.snapshot_archive restore --manifest tfanalytics/v1/manifests/ACTUAL_HASH.json --destination restored-data
```

Restore checks the manifest checksum, decompresses each file, and verifies its
original size and SHA-256. Existing identical files are accepted; different files
are never overwritten. A failed restore can leave already verified files in the
destination; rerun the same command to resume after fixing the failure. A write
interrupted mid-file can leave a partial file; remove that specific partial file
from the recovery directory before retrying.

List the available manifests if a key is lost:

```powershell
python -m integrations.snapshot_archive list
```

The restored directory has the same relative layout as `data/`. Test it with the
existing importer, using a separate database (see its `--help` options), before
considering any removal from Git. This archive proves byte integrity; it does not
replace the existing market-data validation or PostgreSQL backups.

## Enable daily backups

In GitHub repository Settings > Secrets and variables > Actions, add:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `SNAPSHOT_ARCHIVE_BUCKET` | Bucket name |
| Variable | `SNAPSHOT_ARCHIVE_REGION` | AWS region, or `auto` for R2 |
| Variable | `SNAPSHOT_ARCHIVE_ENDPOINT_URL` | Omit for AWS; HTTPS endpoint for other providers |
| Variable | `SNAPSHOT_ARCHIVE_PREFIX` | Optional; defaults to `tfanalytics/v1` |
| Secret | `SNAPSHOT_ARCHIVE_ACCESS_KEY_ID` | Dedicated storage access key ID |
| Secret | `SNAPSHOT_ARCHIVE_SECRET_ACCESS_KEY` | Dedicated storage secret access key |
| Variable | `SNAPSHOT_ARCHIVE_ENABLED` | Set to `true` after configuring the above |

Both daily workflows archive after snapshot validation and before committing or
publishing. With the switch unset, existing workflows continue as before. Once
enabled, an archive verification failure fails the step and prevents subsequent
publishing; the existing diagnostic Actions artifact still runs. Fix the storage
configuration and rerun the job. Git copies are retained during this migration.
The manual scraping workflow is unchanged; use the backfill command for snapshots
created outside the two daily jobs.

Daily manifests contain that run's files; the initial backfill manifest contains
the full existing archive. Restore the backfill and subsequent daily manifests
into the same directory to recover the complete dataset. The community workflow
preserves `raw/non_unusual/` and `processed/non_unusual/` paths.

## Storage format and verification

Each original file is compressed separately with gzip and stored at
`<prefix>/objects/<original-sha256>.gz`. Deterministic gzip headers make identical
uploads reusable. Unchanged content is downloaded and verified without another
write. Changed content creates a new object, preserving previous versions.

A JSON manifest records each relative path, original size, checksum, and object
key. Its own checksum forms its filename. It is uploaded last, only after every
object has been downloaded and compared against the exact uploaded bytes. A
partial upload can leave unreferenced objects, but no completed manifest. A retry
reuses verified objects. Permission errors and conflicting remote content fail
the command instead of silently replacing backups.

Memory usage scales with an individual file, not the entire dataset. These
commands are intended for the current daily snapshot sizes, not multi-GB individual
files. Download verification uses additional requests and bandwidth; check the
chosen provider's charges. Checksums detect corruption, not malicious replacement
by someone with bucket write access. Provider versioning or retention locks can be
configured separately if required.

This is the first migration step. Repository growth continues until the archive
has passed a real restore test and the website's CSV dependencies are migrated.
Do not delete the CSVs or rewrite Git history as part of this setup.
