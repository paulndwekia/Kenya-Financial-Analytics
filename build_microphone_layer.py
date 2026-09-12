from pathlib import Path
import py_compile

BASE = Path(__file__).resolve().parent
VOICE = BASE / "jarvis_core" / "voice"

VOICE.mkdir(parents=True, exist_ok=True)


# ============================================================
# MICROPHONE CONFIGURATION
# ============================================================

(VOICE / "microphone_config.py").write_text(r'''
from dataclasses import dataclass


@dataclass
class MicrophoneConfig:

    sample_rate: int = 16000
    channels: int = 1

    # Length of each listening segment.
    chunk_seconds: float = 3.0

    # Small delay prevents the microphone loop
    # from consuming 100% CPU.
    loop_delay: float = 0.05

    # Audio recording device.
    device = None

    # Minimum amplitude considered meaningful.
    silence_threshold: float = 0.008
''', encoding="utf-8")


# ============================================================
# MICROPHONE CAPTURE
# ============================================================

(VOICE / "microphone.py").write_text(r'''
from pathlib import Path
import tempfile
import wave
import threading
import time


class Microphone:

    """
    Independent microphone capture layer.

    This class does NOT perform speech recognition.

    Its only job is:

        microphone -> WAV audio

    Recognition is handled separately.
    """

    def __init__(self, config=None):

        from microphone_config import MicrophoneConfig

        self.config = (
            config
            if config is not None
            else MicrophoneConfig()
        )

        self.recording = False
        self.error = None

        self._lock = threading.Lock()

    def check(self):

        try:

            import sounddevice as sd

            devices = sd.query_devices()

            input_devices = [
                device
                for device in devices
                if device.get("max_input_channels", 0) > 0
            ]

            if not input_devices:

                self.error = (
                    "No microphone input device was found."
                )

                return False

            return True

        except Exception as error:

            self.error = str(error)

            return False

    def devices(self):

        try:

            import sounddevice as sd

            return sd.query_devices()

        except Exception as error:

            self.error = str(error)

            return []

    def record(self, seconds=None):

        if seconds is None:

            seconds = self.config.chunk_seconds

        try:

            import sounddevice as sd
            import numpy as np

            sample_rate = (
                self.config.sample_rate
            )

            channels = (
                self.config.channels
            )

            self.recording = True

            audio = sd.rec(
                int(
                    seconds *
                    sample_rate
                ),
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
                device=self.config.device
            )

            sd.wait()

            self.recording = False

            # Convert floating point audio
            # into 16-bit PCM.

            audio = np.clip(
                audio,
                -1,
                1
            )

            pcm = (
                audio * 32767
            ).astype(
                np.int16
            )

            file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            )

            file.close()

            with wave.open(
                file.name,
                "wb"
            ) as wav:

                wav.setnchannels(
                    channels
                )

                wav.setsampwidth(2)

                wav.setframerate(
                    sample_rate
                )

                wav.writeframes(
                    pcm.tobytes()
                )

            return Path(file.name)

        except Exception as error:

            self.recording = False
            self.error = str(error)

            return None

    def record_async(
        self,
        seconds=None,
        callback=None
    ):

        def worker():

            result = self.record(
                seconds
            )

            if callback:

                callback(result)

        thread = threading.Thread(
            target=worker,
            daemon=True
        )

        thread.start()

        return thread

    def stop(self):

        self.recording = False

    def status(self):

        if self.recording:

            return "RECORDING"

        if self.error:

            return "ERROR"

        return "READY"
''', encoding="utf-8")


# ============================================================
# LISTENING CONTROLLER
# ============================================================

(VOICE / "listener.py").write_text(r'''
from pathlib import Path
import threading
import time


class JarvisListener:

    """
    Controls when Jarvis is allowed to listen.

    IMPORTANT:

    The listener checks the Jarvis state before
    recording.

    Therefore STANDBY really means:

        microphone capture stops.
    """

    def __init__(
        self,
        state_manager,
        microphone
    ):

        self.state = state_manager
        self.microphone = microphone

        self.running = False

        self.thread = None

        self.last_audio = None

        self.on_audio = None

    def start(self):

        if self.running:

            return

        self.running = True

        self.thread = threading.Thread(
            target=self._loop,
            daemon=True
        )

        self.thread.start()

    def stop(self):

        self.running = False

        self.microphone.stop()

    def _loop(self):

        while self.running:

            # ------------------------------------------------
            # STANDBY
            # ------------------------------------------------

            if not self.state.state.active:

                time.sleep(0.10)

                continue

            # ------------------------------------------------
            # ACTIVE
            # ------------------------------------------------

            if self.state.state.processing:

                time.sleep(0.05)

                continue

            audio_file = self.microphone.record()

            if audio_file is None:

                time.sleep(0.2)

                continue

            self.last_audio = audio_file

            if self.on_audio:

                try:

                    self.on_audio(
                        audio_file
                    )

                except Exception:

                    # Recognition errors must never
                    # kill the listener thread.

                    pass

    def status(self):

        if not self.running:

            return "STOPPED"

        if not self.state.state.active:

            return "STANDBY"

        if self.microphone.recording:

            return "LISTENING"

        return "READY"
''', encoding="utf-8")


# ============================================================
# MICROPHONE TEST
# ============================================================

(BASE / "test_microphone.py").write_text(r'''
from pathlib import Path
import sys


BASE = Path(__file__).resolve().parent
VOICE = BASE / "jarvis_core" / "voice"
CORE = BASE / "jarvis_core"

sys.path.insert(
    0,
    str(VOICE)
)

sys.path.insert(
    0,
    str(CORE)
)


from microphone import Microphone
from microphone_config import MicrophoneConfig


print()
print("=" * 70)
print("JARVIS MICROPHONE TEST")
print("=" * 70)
print()

config = MicrophoneConfig()

microphone = Microphone(
    config
)


# ============================================================
# CHECK DEVICE
# ============================================================

print(
    "[1/4] Checking microphone..."
)

if not microphone.check():

    print()
    print(
        "[ERROR] Microphone check failed."
    )

    print(
        microphone.error
    )

    raise SystemExit(1)


print(
    "[OK] Microphone detected."
)

print()


# ============================================================
# SHOW INPUT DEVICES
# ============================================================

print(
    "[2/4] Available microphone devices"
)

print("-" * 70)

devices = microphone.devices()

for number, device in enumerate(devices):

    if device.get(
        "max_input_channels",
        0
    ) > 0:

        print(
            f"[{number}] "
            f"{device.get('name')}"
        )

print()


# ============================================================
# RECORD TEST
# ============================================================

print(
    "[3/4] Recording a short test."
)

print(
    "Speak normally for 3 seconds."
)

print()

audio = microphone.record(
    seconds=3
)

if audio is None:

    print(
        "[ERROR] Recording failed."
    )

    print(
        microphone.error
    )

    raise SystemExit(1)


print(
    "[OK] Audio captured."
)

print(
    "Temporary audio file:"
)

print(
    audio
)

print()


# ============================================================
# FINAL
# ============================================================

print(
    "[4/4] Microphone system..."
)

print(
    "Status:",
    microphone.status()
)

print()

print("=" * 70)
print("MICROPHONE TEST COMPLETE")
print("=" * 70)
print()

print(
    "The microphone capture layer is working."
)

print(
    "Speech recognition will be connected next."
)

print()
''', encoding="utf-8")


# ============================================================
# LISTENER TEST
# ============================================================

(BASE / "test_listener.py").write_text(r'''
from pathlib import Path
import sys
import time


BASE = Path(__file__).resolve().parent
VOICE = BASE / "jarvis_core" / "voice"
CORE = BASE / "jarvis_core"

sys.path.insert(
    0,
    str(VOICE)
)

sys.path.insert(
    0,
    str(CORE)
)

from microphone import Microphone
from microphone_config import MicrophoneConfig
from listener import JarvisListener
from state_manager import StateManager


print()
print("=" * 70)
print("JARVIS LISTENER CONTROL TEST")
print("=" * 70)
print()


state = StateManager()

# Always begin safely in standby.

state.standby()

microphone = Microphone(
    MicrophoneConfig()
)

listener = JarvisListener(
    state,
    microphone
)


print(
    "[1/5] Starting listener..."
)

listener.start()

print(
    "[OK] Listener thread running."
)

print(
    "State:",
    listener.status()
)

print()


print(
    "[2/5] Testing standby..."
)

state.standby()

time.sleep(1)

print(
    "Listener state:",
    listener.status()
)

assert (
    listener.status() == "STANDBY"
)

print(
    "[OK] Standby prevents listening."
)

print()


print(
    "[3/5] Activating Jarvis..."
)

state.activate()

print(
    "[OK] Jarvis activated."
)

print(
    "State:",
    listener.status()
)

print()


print(
    "[4/5] Testing activation..."
)

time.sleep(0.5)

print(
    "Listener:",
    listener.status()
)

print(
    "Microphone:",
    microphone.status()
)

print()


print(
    "[5/5] Returning to standby..."
)

state.standby()

time.sleep(0.5)

listener.stop()

print(
    "[OK] Listener stopped safely."
)

print()

print("=" * 70)
print("LISTENER CONTROL TEST COMPLETE")
print("=" * 70)
print()

print(
    "ACTIVATE / STANDBY control is ready."
)

print()
''', encoding="utf-8")


# ============================================================
# INSTALL REQUIRED PACKAGES
# ============================================================

print()
print("=" * 70)
print("JARVIS MICROPHONE LAYER")
print("=" * 70)
print()

import subprocess

packages = [
    "sounddevice",
    "numpy"
]

for package in packages:

    print(
        f"Checking {package}..."
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            package
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:

        print(
            f"[OK] {package}"
        )

    else:

        print(
            f"[WARNING] Could not install {package}"
        )

    print()


# ============================================================
# SYNTAX CHECK
# ============================================================

print(
    "Checking new Python files..."
)

files = [
    VOICE / "microphone_config.py",
    VOICE / "microphone.py",
    VOICE / "listener.py",
    BASE / "test_microphone.py",
    BASE / "test_listener.py"
]

for file in files:

    py_compile.compile(
        str(file),
        doraise=True
    )

print(
    "[OK] Syntax checks passed."
)

print()
print("=" * 70)
print("MICROPHONE LAYER INSTALLED")
print("=" * 70)
print()

