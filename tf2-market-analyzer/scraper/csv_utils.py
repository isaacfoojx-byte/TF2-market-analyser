import csv
from pathlib import Path

def save_csv(data, filename):

    if len(data) == 0:
        return

    fieldnames = data[0].keys()

    filepath = Path(filename)

    filepath.parent.mkdir(parents=True, exist_ok=True)

    print("Saving to:", Path(filename).resolve())

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(data)