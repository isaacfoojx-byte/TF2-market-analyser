# Google Sheets publishing

## Workbook layout

Use one workbook for Unusual data and a separate workbook for community data.
The scheduled workflows publish two tabs in each:

- **Latest**: the complete most recently published snapshot. Each upload replaces
  the previous contents, including clearing rows left over from a larger snapshot.
- **Daily History**: one row per scrape date and dataset, containing the scrape
  timestamp, total market count, positively priced market count, mean and median
  guide price in keys, and source CSV filename. Zero, negative, missing, and
  non-finite prices do not contribute to price averages.

A summary uses eight cells per day. A full Unusual snapshot currently uses roughly
664,000 cells; keeping a dated full snapshot every day eventually exceeds the
10-million-cell workbook limit. Even monthly workbooks are too large at that size.
Full daily item-level history continues to live in the repository CSV archive.
Summary averages describe that day's catalog, not a fixed-basket price index or
transaction prices; changes in catalog composition can affect them.

## Migrate the full workbook

1. Keep the existing Unusual workbook as a historical archive. Do not delete its
   dated tabs. The code does not automatically copy or remove old Sheets data.
2. Create a new empty Google spreadsheet in your own Google account. Share it as
   **Editor** with the existing service account (the `client_email` in the service
   account configuration). Do not put the private key in files or chat messages.
3. Change the repository Actions secret `GOOGLE_SPREADSHEET_ID` to the new
   spreadsheet ID: the part between `/d/` and `/edit` in its URL.
4. For a clean community workbook, do the same and update
   `COMMUNITY_GOOGLE_SPREADSHEET_ID`. An existing community workbook with sufficient
   free capacity can also be used; its old dated tabs will remain untouched.
5. Deploy the code changes and run **Daily market update** and
   **Daily community price-guide update** from GitHub Actions. Check that upload
   and read-back verification succeed and that both tabs appear.

Keep `GOOGLE_SERVICE_ACCOUNT_JSON` and the API key secrets unchanged. The workflow
creates the two tabs in the configured workbook; it does not create or own Google
Drive workbooks. Changing the uploader alone cannot free space in the old full
workbook. A capacity error explains when a fresh workbook is required.

Historical summaries start when this mode is activated; existing dated tabs and
older CSVs are not automatically backfilled. The source CSV filename in each row
identifies the corresponding full snapshot in `data/processed/` (Unusual) or
`data/processed/non_unusual/` (community).

## Commands and retries

```bash
python -m integrations.google_sheets PATH_TO_UNUSUAL_CSV --daily-history
python -m integrations.google_sheets PATH_TO_COMMUNITY_CSV --schema community --spreadsheet-id-env COMMUNITY_GOOGLE_SPREADSHEET_ID --daily-history
```

Without `--daily-history`, the command updates only `Latest` by default. Explicit
`--sheet-name` or `GOOGLE_SHEET_NAME` overrides remain available for controlled
uploads; `--daily-history` always targets `Latest` and cannot be combined with
`--max-rows` or a custom tab. `Daily History` is reserved for summaries.

History is written and verified before Latest. The two updates are not a single
transaction: if Latest fails, rerun the same snapshot to finish publication.
Latest is cleared before its replacement is written, so an interrupted upload can
leave it incomplete until a successful retry. The CSV saved in GitHub is unaffected.
History writes use fixed row ranges, making retries safe after a lost API response.
A same-date rerun replaces its summary; an older timestamp for that date is rejected.
Do not run concurrent manual uploads to the same workbook. The daily workflows
already share a GitHub Actions concurrency group to serialize writes.

Use the daily workflows to select fresh snapshots. A manual invocation can publish
an older CSV to Latest; its displayed scrape timestamp identifies the data age.
Capacity checks count allocated grid cells across every tab and never shrink or
delete historical grids. Errors still fail the workflow so publishing failures
remain visible.
