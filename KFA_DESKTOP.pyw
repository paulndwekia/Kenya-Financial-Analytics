from pathlib import Path
import subprocess
import socket
import time
import webbrowser
import logging
import sys

BASE = Path(__file__).resolve().parent
PYTHON = BASE / ".venv" / "Scripts" / "python.exe"
APP = BASE / "app.py"

HOST = "127.0.0.1"
PORT = 8504
URL = f"http://{HOST}:{PORT}"

LOG_FILE = BASE / "kfa_desktop_launcher.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def port_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)

    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def main():

    logging.info("Kenya Financial Analytics launcher started.")

    # -----------------------------------------------------
    # Validate installation
    # -----------------------------------------------------

    if not PYTHON.exists():

        logging.error(
            "Virtual environment Python not found: %s",
            PYTHON
        )

        raise SystemExit(
            "Kenya Financial Analytics Python environment was not found."
        )

    if not APP.exists():

        logging.error(
            "app.py not found: %s",
            APP
        )

        raise SystemExit(
            "Kenya Financial Analytics app.py was not found."
        )

    # -----------------------------------------------------
    # If the dashboard is already running, just open it.
    # -----------------------------------------------------

    if port_open(HOST, PORT):

        logging.info(
            "Dashboard already running on %s",
            URL
        )

        webbrowser.open(URL)
        return

    # -----------------------------------------------------
    # Launch Streamlit
    # -----------------------------------------------------

    command = [
        str(PYTHON),
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.address",
        HOST,
        "--server.port",
        str(PORT),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    logging.info(
        "Starting Streamlit: %s",
        command
    )

    creationflags = 0

    if sys.platform.startswith("win"):

        creationflags = (
            subprocess.CREATE_NO_WINDOW
        )

    process = subprocess.Popen(
        command,
        cwd=str(BASE),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    logging.info(
        "Streamlit process started. PID=%s",
        process.pid
    )

    # -----------------------------------------------------
    # Wait for Streamlit to become available
    # -----------------------------------------------------

    for _ in range(40):

        if port_open(HOST, PORT):

            logging.info(
                "Dashboard is ready."
            )

            webbrowser.open(URL)
            return

        time.sleep(0.5)

    # -----------------------------------------------------
    # Failed startup
    # -----------------------------------------------------

    logging.error(
        "Streamlit did not become available after 20 seconds."
    )

    raise SystemExit(
        "Kenya Financial Analytics could not start. "
        f"Check {LOG_FILE.name}."
    )


if __name__ == "__main__":
    main()
