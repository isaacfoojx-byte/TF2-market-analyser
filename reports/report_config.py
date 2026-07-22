from pathlib import Path

# =============================================================================
# Directories
# =============================================================================

OUTPUT_DIR = Path("generated/reports")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# =============================================================================
# Formatting
# =============================================================================

REPORT_WIDTH = 60

ENCODING = "utf-8"

# =============================================================================
# Filenames
# =============================================================================

TEXT_FILENAME = "comparison_report.txt"

MARKDOWN_FILENAME = "comparison_report.md"

PDF_FILENAME = "comparison_report.pdf"