from datetime import datetime
from pathlib import Path

from reports.report_config import (
    REPORT_WIDTH,
    ENCODING,
)

def section(title):

    return "\n".join([
        "=" * REPORT_WIDTH,
        title,
        "=" * REPORT_WIDTH,
        ""
    ])

def subsection(title):

    return "\n".join([
        title,
        "-" * REPORT_WIDTH
    ])

def dataframe(df):

    return df.to_string(index=False)


def timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

def save_text(report, filename):

    filename = Path(filename)

    with open(
        filename,
        "w",
        encoding=ENCODING
    ) as file:

        file.write(report)

    return filename


