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

VB_CABLE_SITE = "https://vb-audio.com/Cable/"
RECOMMENDED_SAMPLE_RATE = 48000

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
    "1. Download VB-Cable from https://vb-audio.com/Cable/ and run the installer as administrator.\n"
    "2. REBOOT (required), then open Vocalis and set AUDIO mode to 'server'.\n"
    "3. Set 'Output' to the cable PLAYBACK side - shown as 'CABLE Input (VB-Audio Virtual Cable)' or "
    "'Speakers (VB-Audio Virtual Cable)' depending on Windows version. Use 'Run diagnosis' to find it.\n"
    "4. Set 'Monitor' to your headphones/speakers to hear yourself.\n"
    "5. Keep input and output on the same API (recommended: Windows WASAPI) and S.R. = 48000.\n"
    "6. In Discord/OBS select the cable RECORDING side ('CABLE Output (VB-Audio Virtual Cable)') as the microphone.\n"
    "7. In Discord: disable Noise Suppression (Krisp) and Echo Cancellation, and disable automatic input sensitivity.\n"
    "'Run diagnosis' checks all of this automatically. VoiceMeeter (same site) is a bigger alternative with a mixer."
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


###########################################
# Windows diagnostics (VB-CABLE)
###########################################

# Patterns that identify the two sides of a virtual cable. The playback side
# ("CABLE Input", "Speakers (VB-Audio Virtual Cable)") is what Vocalis writes
# the converted voice into; the recording side ("CABLE Output") is what other
# apps (Discord, OBS) must select as their microphone.
VB_RENDER_PATTERNS = ["cable input", "vb-audio virtual cable", "vb-audio point", "voicemeeter input", "vocalis", "blackhole"]
VB_CAPTURE_PATTERNS = ["cable output", "vb-audio virtual cable", "vb-audio point", "voicemeeter output", "vocalis", "blackhole"]


def _classify_virtual_devices(devices: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split virtual devices into (playback side, recording side).

    `devices` are dicts with at least name/hostAPI/index/maxInputChannels/
    maxOutputChannels/default_samplerate (ServerAudioDevice fields). VB-CABLE
    names are truncated by PortAudio on some host APIs (f.e. MME), so prefix
    matching is used.
    """
    def channels(d: dict, kind: str) -> int:
        return int(d.get(f"max{kind}Channels", d.get(f"max_{kind.lower()}_channels", 0)) or 0)

    render, capture = [], []
    for d in devices:
        lowered = d["name"].lower()
        is_virtual = any(pat in lowered for pat in KNOWN_VIRTUAL_DEVICE_PATTERNS)
        if not is_virtual:
            continue
        entry = {
            "index": d["index"],
            "name": d["name"],
            "hostAPI": d["hostAPI"],
            "defaultSampleRate": int(d.get("default_samplerate", 0) or 0),
        }
        if channels(d, "Output") > 0 and any(lowered.startswith(p) or p in lowered for p in VB_RENDER_PATTERNS):
            if "cable output" not in lowered and "voicemeeter output" not in lowered:
                render.append(entry)
        if channels(d, "Input") > 0 and any(lowered.startswith(p) or p in lowered for p in VB_CAPTURE_PATTERNS):
            if "cable input" not in lowered and "voicemeeter input" not in lowered and "speakers" not in lowered:
                capture.append(entry)
    return render, capture


def _read_registry_value(root, path: str, value: str):
    import winreg
    try:
        with winreg.OpenKey(root, path) as key:
            data, _type = winreg.QueryValueEx(key, value)
            return data
    except OSError:
        return None
    except Exception as e:  # NOQA: BLE001
        logger.warning(f"[virtual_audio] registry read {path}\\{value} failed: {e}")
        return None


def _vb_cable_registry_info() -> dict:
    """Read VB-CABLE driver settings from the registry (readable without admin)."""
    import winreg
    info = {"internalSampleRate": None, "maxLatencySamples": None, "driverVersion": None}
    sr = _read_registry_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VB-Audio\Cable", "VBAudioCableWDM_SR")
    if isinstance(sr, int):
        info["internalSampleRate"] = sr
    latency = _read_registry_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VB-Audio\Cable", "VBAudioCableWDM")
    if isinstance(latency, int):
        info["maxLatencySamples"] = latency

    # Driver version from the audio device class key (DriverDesc matches).
    class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_path) as ck:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(ck, i)
                except OSError:
                    break
                i += 1
                desc = _read_registry_value(winreg.HKEY_LOCAL_MACHINE, f"{class_path}\\{sub}", "DriverDesc")
                if desc and "vb-audio" in str(desc).lower():
                    ver = _read_registry_value(winreg.HKEY_LOCAL_MACHINE, f"{class_path}\\{sub}", "DriverVersion")
                    if ver:
                        info["driverVersion"] = str(ver)
                    break
    except OSError:
        pass
    return info


def _parse_wave_format_blob(blob: bytes) -> dict | None:
    """Decode PKEY_AudioEngine_DeviceFormat (VT_BLOB + WAVEFORMATEXTENSIBLE)."""
    import struct
    if not blob or len(blob) < 8 + 16:
        return None
    try:
        # VT_BLOB header: type(2) + padding(2) + cbSize(4), then WAVEFORMATEX
        wfx = blob[8:]
        tag, channels, rate, _avg, _align, bits = struct.unpack_from("<HHIIHH", wfx, 0)
        return {"channels": channels, "sampleRate": rate, "bitsPerSample": bits, "tag": tag}
    except Exception:  # NOQA: BLE001
        return None


def _endpoint_formats_matching(substrs: list[str]) -> dict:
    """Read default endpoint formats from the MMDevices registry (best-effort).

    Matches on both DeviceDesc ({a45c254e...},2 - f.e. 'CABLE Output') and
    FriendlyName ({a45c254e...},14 - f.e. 'Speakers (VB-Audio Virtual Cable)'),
    since render endpoints usually carry the cable name only in the latter.
    """
    import winreg
    result = {"render": None, "capture": None}
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio"
    for kind in ("Render", "Capture"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{kind}") as k:
                i = 0
                while True:
                    try:
                        endpoint = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        with winreg.OpenKey(k, f"{endpoint}\\Properties") as pk:
                            j = 0
                            names: list[str] = []
                            fmt = None
                            while True:
                                try:
                                    vname, vdata, _vtype = winreg.EnumValue(pk, j)
                                except OSError:
                                    break
                                j += 1
                                if vname.endswith("{a45c254e-df1c-4efd-8020-67d146a850e0},2") or vname.endswith("{a45c254e-df1c-4efd-8020-67d146a850e0},14") or vname.endswith("{b3f8fa53-0004-438e-9003-51a46e139bfc},6"):
                                    if isinstance(vdata, str):
                                        names.append(vdata)
                                elif vname.endswith("{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0"):
                                    fmt = vdata if isinstance(vdata, bytes) else None
                            if fmt and any(any(s in n.lower() for s in substrs) for n in names):
                                parsed = _parse_wave_format_blob(fmt)
                                if parsed:
                                    result[kind.lower()] = parsed
                    except OSError:
                        continue
        except OSError:
            continue
    return result


def diagnose_windows(devices: list[dict]) -> dict:
    """Collect VB-CABLE state and common misconfigurations on Windows.

    `devices` is the full PortAudio device list (dicts as produced by
    list_audio_device). Everything here is read-only and works without
    administrator rights.
    """
    render, capture = _classify_virtual_devices(devices)
    detected = bool(render or capture)
    checks: list[dict] = []

    def add(check_id: str, severity: str, label: str, detail: str = "", fix: str = ""):
        checks.append({"id": check_id, "severity": severity, "label": label, "detail": detail, "fix": fix})

    reg = _vb_cable_registry_info() if detected else {}
    is_vb = any("vb-audio" in d["name"].lower() or "cable" in d["name"].lower() for d in render + capture)

    if not detected:
        add("driver", "error", "No virtual audio device found",
            "VB-CABLE (or an alternative virtual cable) is not installed or not present in the audio device list.",
            "Install VB-CABLE from https://vb-audio.com/Cable/ (run the setup as administrator) and REBOOT, then restart Vocalis.")
    else:
        preferred_render = next((d for d in render if "WASAPI" in d["hostAPI"]), render[0] if render else None)
        preferred_capture = next((d for d in capture if "WASAPI" in d["hostAPI"]), capture[0] if capture else None)
        if reg.get("driverVersion"):
            add("driver", "info", f"VB-CABLE driver version: {reg['driverVersion']}",
                "Driver Pack 45 (driver 3.3.1.7, Oct 2024) or newer is recommended for Windows 10/11.",
                "If audio issues persist, reinstall the latest driver pack from https://vb-audio.com/Cable/ as administrator and reboot.")
        if is_vb and reg.get("internalSampleRate") and reg["internalSampleRate"] != RECOMMENDED_SAMPLE_RATE:
            add("internal_sr", "warn",
                f"VB-CABLE Internal SR is {reg['internalSampleRate']} Hz (recommended: 48000 Hz)",
                "The cable still works (it resamples internally), but 48000 Hz avoids extra conversion and latency.",
                "Run tools/windows-fix-vbcable.ps1 as administrator (or set 48000 in the VB-CABLE Control Panel) and reboot.")
        if render:
            add("render_side", "ok", f"Playback side found: {preferred_render['name']} [{preferred_render['hostAPI']}]",
                "This is the device Vocalis must use as 'Output' in server audio mode.")
        else:
            add("render_side", "error", "Virtual cable playback side not found",
                "The device other apps record from exists, but the playback side Vocalis writes into was not found.",
                "Check that the cable device is enabled in Windows Sound settings (mmsys.cpl).")
        if capture:
            add("capture_side", "ok", f"Recording side found: {preferred_capture['name']} [{preferred_capture['hostAPI']}]",
                "This is the microphone Discord/OBS must select (Discord error 3002 means it is receiving silence from it).")
        else:
            add("capture_side", "error", "Virtual cable recording side not found",
                "Discord and other apps have no virtual microphone to record from.",
                "Check that the cable recording device is enabled in Windows Sound settings (mmsys.cpl > Recording tab).")
        if is_vb:
            fmts = _endpoint_formats_matching(["vb-audio virtual cable", "cable"])
            r, c = fmts["render"], fmts["capture"]
            if r and c and r["sampleRate"] != c["sampleRate"]:
                add("endpoint_rates", "warn",
                    f"Cable endpoints use different rates: playback {r['sampleRate']} Hz vs recording {c['sampleRate']} Hz",
                    "VB-CABLE converts automatically, so this is not fatal, but setting both to 48000 Hz in mmsys.cpl > Advanced gives the best quality and latency.",
                    "Open mmsys.cpl, Advanced tab of both cable devices, set '2 channel 16 bit 48000 Hz'.")

    return {
        "status": "OK",
        "platform": "Windows",
        "virtualDeviceDetected": detected,
        "renderSide": render,
        "captureSide": capture,
        "registry": reg if detected else None,
        "checks": checks,
        "discordTips": [
            "In Discord: Voice & Video > Input Device = the cable RECORDING side (e.g. 'CABLE Output (VB-Audio Virtual Cable)'), not 'Default'.",
            "Disable Discord 'Noise Suppression' (Krisp) and 'Echo Cancellation'; they can silence virtual-microphone audio. Input Profile 'Studio' works well.",
            "Disable 'Automatically determine input sensitivity' and set the threshold manually.",
            "Error 3002 in Discord means 'no input detected': the cable is receiving silence, usually because Vocalis is not running/started or the wrong output device is selected.",
        ],
    }


def recommend_routing(devices: list[dict]) -> dict:
    """Best (inputDeviceIndex, outputDeviceIndex) pair for cable routing on Windows.

    Prefers WASAPI (lowest latency, rate conversion handled), then
    DirectSound, then MME. Input = system default microphone (non-virtual),
    output = the cable playback side, both from the same host API.
    """
    render, _ = _classify_virtual_devices(devices)
    if not render:
        return {}
    api_priority = ["WASAPI", "DirectSound", "MME", "WDM-KS"]
    best_api = None
    for api in api_priority:
        outs = [d for d in render if api.lower() in d["hostAPI"].lower()]
        if outs:
            best_api = api
            break
    if best_api is None:
        return {}
    out_dev = [d for d in render if best_api.lower() in d["hostAPI"].lower()][0]

    def in_channels(d: dict) -> int:
        return int(d.get("maxInputChannels", d.get("max_input_channels", 0)) or 0)

    def out_channels(d: dict) -> int:
        return int(d.get("maxOutputChannels", d.get("max_output_channels", 0)) or 0)

    candidates = [
        d for d in devices
        if in_channels(d) > 0
        and out_channels(d) == 0
        and not any(p in d["name"].lower() for p in KNOWN_VIRTUAL_DEVICE_PATTERNS)
        and best_api.lower() in d["hostAPI"].lower()
    ]
    if not candidates:
        return {}
    in_dev = candidates[0]
    return {
        "inputDeviceIndex": in_dev["index"],
        "outputDeviceIndex": out_dev["index"],
        "hostAPI": out_dev["hostAPI"],
        "sampleRate": RECOMMENDED_SAMPLE_RATE,
        "inputDeviceName": in_dev["name"],
        "outputDeviceName": out_dev["name"],
    }


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
