"""Cross-platform virtual audio device support.

The goal: route the converted voice into a virtual microphone that other apps
(Discord, OBS, VTube Studio, ...) can pick up as a regular input device, while
the user keeps hearing themselves through the monitor device.

Each OS needs a different strategy:

- Linux (PipeWire / PulseAudio): a null sink can be created and removed from
  userspace with `pactl`. Fully automated by Vocalis: we create a sink named
  "Vocalis AI Output" that shows up as both an output device (Vocalis writes
  the converted voice to it) and a source (other apps record from it).

- macOS: virtual devices require a kernel-adjacent audio driver. The
  recommended one is BlackHole (open source, free). When Homebrew is
  available Vocalis can run the install with one click; otherwise the user
  installs the .pkg manually once.

- Windows: virtual devices require a signed driver, so no process can create
  one at runtime. VB-Cable (free) is the standard choice; Vocalis detects it
  once installed and the UI guides the one-time setup.

Detection scans the PortAudio device list for well-known virtual device names
so the UI can confirm "your virtual device is ready" on every OS.
"""

import logging
import platform
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)

VIRTUAL_SINK_NAME = "vocalis_ai_out"
VIRTUAL_SINK_DESCRIPTION = "Vocalis AI Output"
BLACKHOLE_PACKAGE = "blackhole-2ch"

# Substrings (lowercase) of virtual audio device names we recognize.
KNOWN_VIRTUAL_DEVICE_PATTERNS = [
    "vocalis",
    "vb-audio",
    "vb-cable",
    "cable input",
    "cable output",
    "voicemeeter",
    "blackhole",
    "soundflower",
    "loopback",
    "virtual audio cable",
    "virtualaudio",
    "virtual audio",
]

WINDOWS_GUIDE = (
    "Windows needs a one-time driver install (apps cannot create audio devices at runtime):\n"
    "1. Download VB-Cable from https://vb-audio.com/Cable/ and run the installer.\n"
    "2. Reboot, then open Vocalis and set AUDIO mode to 'server'.\n"
    "3. Set 'Output' to 'CABLE Input (VB-Audio Virtual Cable)'.\n"
    "4. Set 'Monitor' to your headphones/speakers.\n"
    "5. In Discord/OBS/VTube Studio select 'CABLE Output' as the microphone.\n"
    "VoiceMeeter (same site) is a bigger alternative with a mixer."
)

MACOS_GUIDE = (
    "macOS needs a one-time driver install. Recommended: BlackHole (open source, free).\n"
    "1. Click 'Install BlackHole' below if Homebrew is available (or run: brew install --cask blackhole-2ch).\n"
    "2. Otherwise download the .pkg from https://existential.audio/blackhole/ and install it.\n"
    "3. Restart Vocalis, set AUDIO mode to 'server'.\n"
    "4. Set 'Output' to 'BlackHole 2ch' and 'Monitor' to your headphones.\n"
    "5. In Discord/OBS/VTube Studio select 'BlackHole 2ch' as the microphone."
)

LINUX_GUIDE = (
    "Vocalis can create a virtual device for you (PipeWire/PulseAudio):\n"
    "1. Click 'Create virtual device' below.\n"
    "2. Set 'Output' to 'Vocalis AI Output'.\n"
    "3. Set 'Monitor' to your headphones.\n"
    "4. In Discord/OBS/VTube Studio select 'Vocalis AI Output' (or 'Monitor of Vocalis AI Output') as the microphone."
)

# pactl load-module output is just the module index
_MODULE_INDEX_RE = re.compile(r"^\s*(\d+)\s*$")


def _run(cmd: list[str], timeout: float = 120.0) -> tuple[int, str]:
    """Run a command, capturing combined output. Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output.strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"command timed out: {cmd[0]}"
    except Exception as e:  # NOQA: BLE001
        logger.exception(e)
        return 1, str(e)


def _get_platform() -> str:
    return platform.system()  # 'Windows' | 'Darwin' | 'Linux'


def _pactl_path() -> str | None:
    return shutil.which("pactl")


def _brew_path() -> str | None:
    return shutil.which("brew")


def _list_sinks() -> list[str]:
    code, out = _run(["pactl", "list", "short", "sinks"], timeout=10)
    if code != 0:
        return []
    return [line for line in out.splitlines() if line.strip()]


def _sink_exists() -> bool:
    return any(VIRTUAL_SINK_NAME in line.split() for line in _list_sinks())


def _find_module_by_args() -> list[int]:
    """Indices of every loaded module-null-sink owned by us (name-tagged).

    `pactl list short modules` prints: index, name, argument, usage counter
    (tab separated) - the index we need for `unload-module` is column 0.
    """
    code, out = _run(["pactl", "list", "short", "modules"], timeout=10)
    if code != 0:
        return []
    indexes = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "module-null-sink" in line and f"sink_name={VIRTUAL_SINK_NAME}" in line:
            try:
                indexes.append(int(parts[0]))
            except ValueError:
                pass
    return indexes


def detect_virtual_devices(device_names: list[str]) -> list[str]:
    """Return the subset of device names that look like virtual audio devices."""
    found = []
    for name in device_names:
        lowered = name.lower()
        if any(pat in lowered for pat in KNOWN_VIRTUAL_DEVICE_PATTERNS):
            found.append(name)
    return found


def _status_common(capability: str) -> dict:
    return {
        "status": "OK",
        "platform": _get_platform(),
        "capability": capability,  # 'manage' | 'install' | 'guide'
        "virtualDeviceDetected": False,
        "detectedDevices": [],
        "sinkName": VIRTUAL_SINK_NAME,
        "guide": "",
    }


def get_status(device_names: list[str] | None = None) -> dict:
    plat = _get_platform()
    detected = detect_virtual_devices(device_names or [])

    if plat == "Linux":
        data = _status_common("manage" if _pactl_path() else "guide")
        data["guide"] = LINUX_GUIDE
        if _pactl_path():
            data["sinkLoaded"] = _sink_exists()
            data["virtualDeviceDetected"] = _sink_exists() or bool(detected)
        else:
            data["sinkLoaded"] = False
            data["guide"] = (
                "pactl was not found. Install PipeWire/PulseAudio tools "
                "(e.g. 'sudo pacman -S libpulse' or 'sudo apt install pulseaudio-utils'), "
                "or create a sink manually:\n"
                "pactl load-module module-null-sink sink_name=vocalis_ai_out "
                "sink_properties=device.description='Vocalis AI Output'"
            )
    elif plat == "Darwin":
        brew = _brew_path()
        data = _status_common("install" if brew else "guide")
        data["guide"] = MACOS_GUIDE
        data["brewAvailable"] = bool(brew)
    else:
        data = _status_common("guide")
        data["guide"] = WINDOWS_GUIDE

    data["detectedDevices"] = detected
    if detected:
        data["virtualDeviceDetected"] = True
    return data


def create_virtual_device() -> dict:
    """Create the virtual device where the OS allows it; return a status dict."""
    plat = _get_platform()
    if plat == "Linux":
        pactl = _pactl_path()
        if not pactl:
            return {**_status_common("guide"), "status": "ERROR", "message": "pactl not found. See the guide for manual setup.", "guide": LINUX_GUIDE}
        if _sink_exists():
            data = get_status()
            data["message"] = f"Virtual device '{VIRTUAL_SINK_DESCRIPTION}' already exists."
            data["created"] = True
            return data
        code, out = _run([
            "pactl", "load-module", "module-null-sink",
            f"sink_name={VIRTUAL_SINK_NAME}",
            f"sink_properties=device.description='{VIRTUAL_SINK_DESCRIPTION}'",
        ], timeout=10)
        if code != 0:
            return {**get_status(), "status": "ERROR", "message": f"pactl failed: {out}", "created": False}
        # Optional: also expose a loopback-free source: null sinks automatically
        # provide a .monitor source, which is what other apps should record from.
        data = get_status()
        data["created"] = True
        data["message"] = (
            f"Created '{VIRTUAL_SINK_DESCRIPTION}'. Select it as 'Output' in server audio mode; "
            f"other apps should record from '{VIRTUAL_SINK_DESCRIPTION}' (its monitor source)."
        )
        return data

    if plat == "Darwin":
        brew = _brew_path()
        if not brew:
            return {**get_status(), "status": "ERROR", "message": "Homebrew not found. Install BlackHole manually (see guide).", "created": False}
        code, out = _run(["brew", "install", "--cask", BLACKHOLE_PACKAGE], timeout=600)
        data = get_status()
        if code != 0:
            data["status"] = "ERROR"
            data["message"] = f"brew install failed: {out}"
            data["created"] = False
            return data
        data["created"] = True
        data["message"] = "BlackHole installed. Restart Vocalis (so the device list refreshes), then select 'BlackHole 2ch' as 'Output'."
        return data

    # Windows: not possible without a driver install
    return {**get_status(), "status": "ERROR", "message": WINDOWS_GUIDE, "created": False}


def remove_virtual_device() -> dict:
    plat = _get_platform()
    if plat == "Linux":
        indexes = _find_module_by_args()
        if not indexes:
            return {**get_status(), "status": "ERROR", "message": f"No '{VIRTUAL_SINK_DESCRIPTION}' sink is loaded.", "removed": False}
        for idx in indexes:
            _run(["pactl", "unload-module", str(idx)], timeout=10)
        data = get_status()
        data["removed"] = not _sink_exists()
        data["message"] = f"Removed '{VIRTUAL_SINK_DESCRIPTION}'." if data["removed"] else "Unload was issued; the sink may still appear until streams close."
        return data
    if plat == "Darwin":
        brew = _brew_path()
        if not brew:
            return {**get_status(), "status": "ERROR", "message": "Homebrew not found. Uninstall BlackHole manually.", "removed": False}
        code, out = _run(["brew", "uninstall", "--cask", BLACKHOLE_PACKAGE], timeout=600)
        data = get_status()
        data["removed"] = code == 0
        data["message"] = "BlackHole uninstalled." if code == 0 else f"brew uninstall failed: {out}"
        if code != 0:
            data["status"] = "ERROR"
        return data
    return {**get_status(), "status": "ERROR", "message": "On Windows, uninstall VB-Cable from the system settings.", "removed": False}
