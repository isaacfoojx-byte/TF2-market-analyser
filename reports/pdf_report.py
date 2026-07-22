from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.lib.enums import TA_CENTER

from reports.report_config import (
    OUTPUT_DIR,
    PDF_FILENAME,
)



def save_pdf(report):

    filename = OUTPUT_DIR / PDF_FILENAME

    document = SimpleDocTemplate(str(filename))

    styles = getSampleStyleSheet()

    heading = styles["Heading1"]
    heading.alignment = TA_CENTER

    body = styles["BodyText"]

    story = []

    lines = report.splitlines()

    i = 0

    while i < len(lines):

        line = lines[i]

        # -------------------------------------------------
        # Blank line
        # -------------------------------------------------

        if not line.strip():

            story.append(Spacer(1, 8))
            i += 1
            continue

        # -------------------------------------------------
        # Detect section headings
        #
        # =====================
        # Title
        # =====================
        # -------------------------------------------------

        if (
            line.startswith("=")
            and i + 1 < len(lines)
            and i + 2 < len(lines)
            and lines[i + 2].startswith("=")
        ):

            story.append(
                Paragraph(
                    lines[i + 1],
                    heading
                )
            )

            story.append(Spacer(1, 12))

            i += 3
            continue

        # -------------------------------------------------
        # Preserve spacing in tables
        # -------------------------------------------------

        text = line.replace(" ", "&nbsp;")

        story.append(
            Paragraph(
                text,
                body
            )
        )

        i += 1

    document.build(story)

    return filename


