from pathlib import Path
import subprocess
import sys
import json
from datetime import datetime

ROOT = Path.cwd()

IMPORTER = ROOT / "cbk_auto_importer.py"
STATUS_FILE = ROOT / "cbk_refresh_status.json"
LOG_FILE = ROOT / "cbk_refresh.log"


def save_status(status, message, output=""):

    data = {
        "status": status,
        "message": message,
        "last_attempt": datetime.now().isoformat(
            timespec="seconds"
        ),
        "importer": str(IMPORTER),
        "output": output[-5000:]
    }

    STATUS_FILE.write_text(
        json.dumps(
            data,
            indent=4
        ),
        encoding="utf-8"
    )


print()
print("=" * 70)
print("KENYA FINANCIAL ANALYTICS")
print("CBK AUTOMATIC DATA REFRESH")
print("=" * 70)
print()

if not IMPORTER.exists():

    message = (
        "cbk_auto_importer.py was not found."
    )

    print("[ERROR]", message)

    save_status(
        "ERROR",
        message
    )

    raise SystemExit(1)


print(
    "Running existing CBK importer..."
)

print()

try:

    process = subprocess.run(
        [
            sys.executable,
            str(IMPORTER)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    output = (
        process.stdout
        + "\n"
        + process.stderr
    )

    print(output)

    LOG_FILE.write_text(
        output,
        encoding="utf-8"
    )

    if process.returncode == 0:

        save_status(
            "SUCCESS",
            "CBK refresh completed successfully.",
            output
        )

        print()
        print("=" * 70)
        print("CBK REFRESH SUCCESSFUL")
        print("=" * 70)

    else:

        save_status(
            "FAILED",
            (
                "CBK importer exited with "
                f"code {process.returncode}."
            ),
            output
        )

        print()
        print("=" * 70)
        print("CBK REFRESH FAILED")
        print("=" * 70)

        raise SystemExit(
            process.returncode
        )

except Exception as error:

    save_status(
        "ERROR",
        str(error)
    )

    print()
    print("=" * 70)
    print("CBK REFRESH ERROR")
    print("=" * 70)
    print()
    print(error)

    raise


print()
print(
    "Status file:",
    STATUS_FILE.resolve()
)

print(
    "Log file:",
    LOG_FILE.resolve()
)

print()
