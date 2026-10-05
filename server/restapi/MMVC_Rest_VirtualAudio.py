import logging
from dataclasses import asdict

from fastapi import APIRouter, Form
from voice_changer.Local import VirtualAudioHelper
from voice_changer.Local.AudioDeviceList import list_audio_device
from voice_changer.VoiceChangerManager import VoiceChangerManager

import sounddevice as sd

logger = logging.getLogger(__name__)


class MMVC_Rest_VirtualAudio:
    def __init__(self, voiceChangerManager: VoiceChangerManager):
        self.voiceChangerManager = voiceChangerManager
        self.router = APIRouter()
        self.router.add_api_route("/virtual_audio/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/virtual_audio/create", self.post_create, methods=["POST"])
        self.router.add_api_route("/virtual_audio/remove", self.post_remove, methods=["POST"])
        self.router.add_api_route("/virtual_audio/diagnose", self.get_diagnose, methods=["GET"])
        self.router.add_api_route("/virtual_audio/apply_recommendations", self.post_apply_recommendations, methods=["POST"])

    def _device_names(self) -> list[str]:
        try:
            inputs, outputs = list_audio_device()
            return [d.name for d in inputs] + [d.name for d in outputs]
        except Exception as e:  # NOQA: BLE001
            logger.warning(f"[virtual_audio] device enumeration failed: {e}")
            return []

    def _all_devices(self) -> list[dict]:
        try:
            inputs, outputs = list_audio_device()
            return [asdict(d) for d in inputs] + [asdict(d) for d in outputs]
        except Exception as e:  # NOQA: BLE001
            logger.warning(f"[virtual_audio] device enumeration failed: {e}")
            return []

    def _refresh_device_cache_if_safe(self):
        # PortAudio snapshots the device list at init. Re-initialize it so a
        # newly created sink shows up, but never while a stream is open.
        if not self.voiceChangerManager.server_audio.running:
            try:
                sd._terminate()
                sd._initialize()
            except Exception as e:  # NOQA: BLE001
                logger.warning(f"[virtual_audio] PortAudio re-init failed: {e}")

    def _with_devices(self, data: dict) -> dict:
        devices = self._device_names()
        detected = VirtualAudioHelper.detect_virtual_devices(devices)
        data["detectedDevices"] = detected
        if detected:
            data["virtualDeviceDetected"] = True
        data["deviceCacheRefreshed"] = not self.voiceChangerManager.server_audio.running
        return data

    def get_status(self):
        try:
            data = VirtualAudioHelper.get_status(self._device_names())
            return self._with_devices(data)
        except Exception as e:  # NOQA: BLE001
            logger.exception(e)
            return {"status": "ERROR", "message": str(e)}

    def get_diagnose(self):
        """Run read-only virtual audio diagnostics (VB-CABLE on Windows)."""
        try:
            devices = self._all_devices()
            if VirtualAudioHelper._get_platform() == "Windows":
                data = VirtualAudioHelper.diagnose_windows(devices)
            else:
                data = VirtualAudioHelper.get_status(self._device_names())
            recommendation = VirtualAudioHelper.recommend_routing(devices) if VirtualAudioHelper._get_platform() == "Windows" else {}

            # Settings-aware checks: catch the classic wiring mistakes.
            settings = self.voiceChangerManager.settings
            if VirtualAudioHelper._get_platform() == "Windows" and data.get("virtualDeviceDetected"):
                in_dev = next((d for d in devices if d["index"] == settings.serverInputDeviceId), None)
                out_dev = next((d for d in devices if d["index"] == settings.serverOutputDeviceId), None)
                checks = data.get("checks", [])
                if settings.serverOutputDeviceId != -1 and out_dev:
                    lowered = out_dev["name"].lower()
                    if "cable output" in lowered or "microphone" in lowered:
                        checks.append({
                            "id": "output_wrong_side", "severity": "error",
                            "label": f"Output device is '{out_dev['name']}' - this is the RECORDING side of the cable",
                            "detail": "Vocalis must write into the PLAYBACK side (e.g. 'Speakers (VB-Audio Virtual Cable)' / 'CABLE Input').",
                            "fix": "Use 'Apply recommended routing' below or pick the cable playback side as Output.",
                        })
                if in_dev and out_dev and in_dev["hostAPI"] != out_dev["hostAPI"]:
                    checks.append({
                        "id": "hostapi_mismatch", "severity": "error",
                        "label": f"Input ({in_dev['hostAPI']}) and output ({out_dev['hostAPI']}) use different audio APIs",
                        "detail": "Windows cannot open devices from different APIs in one stream; audio will not start.",
                        "fix": "Use 'Apply recommended routing' below or select both devices from the same API (Windows WASAPI recommended).",
                    })
                if settings.serverAudioSampleRate != VirtualAudioHelper.RECOMMENDED_SAMPLE_RATE:
                    checks.append({
                        "id": "sample_rate", "severity": "warn",
                        "label": f"Server sample rate is {settings.serverAudioSampleRate} Hz (recommended: 48000 Hz)",
                        "detail": "48000 Hz is the native rate of most modern devices and of VB-CABLE; it avoids extra resampling.",
                        "fix": "Use 'Apply recommended routing' below or set S.R. = 48000 in the Device area.",
                    })
                data["checks"] = checks

            data["recommendation"] = recommendation
            data["currentSelection"] = {
                "enableServerAudio": settings.enableServerAudio,
                "inputDeviceIndex": settings.serverInputDeviceId,
                "outputDeviceIndex": settings.serverOutputDeviceId,
                "monitorDeviceIndex": settings.serverMonitorDeviceId,
                "sampleRate": settings.serverAudioSampleRate,
            }
            return data
        except Exception as e:  # NOQA: BLE001
            logger.exception(e)
            return {"status": "ERROR", "message": str(e)}

    def post_apply_recommendations(self):
        """One-click fix inside the app (no admin rights required):
        enable server audio, select mic + cable playback side on the same host
        API, and set the sample rate to 48000. Monitor is left untouched.
        """
        try:
            self._refresh_device_cache_if_safe()
            devices = self._all_devices()
            rec = VirtualAudioHelper.recommend_routing(devices)
            if not rec:
                return {"status": "ERROR", "message": "No virtual audio device or suitable microphone found. Install VB-CABLE first (see guide)."}
            manager = self.voiceChangerManager
            manager.update_settings("enableServerAudio", 1)
            manager.update_settings("serverAudioSampleRate", rec["sampleRate"])
            manager.update_settings("serverInputDeviceId", rec["inputDeviceIndex"])
            manager.update_settings("serverOutputDeviceId", rec["outputDeviceIndex"])
            logger.info(
                f"[virtual_audio] applied recommended routing: input '{rec['inputDeviceName']}' ({rec['inputDeviceIndex']}), "
                f"output '{rec['outputDeviceName']}' ({rec['outputDeviceIndex']}), {rec['hostAPI']}, {rec['sampleRate']} Hz"
            )
            return {
                "status": "OK",
                "message": (
                    f"Routing set: input '{rec['inputDeviceName']}' -> output '{rec['outputDeviceName']}' "
                    f"[{rec['hostAPI']}] @ {rec['sampleRate']} Hz. Press START, then select the cable recording side "
                    f"in Discord/OBS as your microphone."
                ),
                "recommendation": rec,
            }
        except Exception as e:  # NOQA: BLE001
            logger.exception(e)
            return {"status": "ERROR", "message": str(e)}

    def post_create(self, name: str = Form(default="")):
        try:
            data = VirtualAudioHelper.create_virtual_device()
            if data.get("created"):
                self._refresh_device_cache_if_safe()
            return self._with_devices(data)
        except Exception as e:  # NOQA: BLE001
            logger.exception(e)
            return {"status": "ERROR", "message": str(e)}

    def post_remove(self):
        try:
            data = VirtualAudioHelper.remove_virtual_device()
            if data.get("removed"):
                self._refresh_device_cache_if_safe()
            return self._with_devices(data)
        except Exception as e:  # NOQA: BLE001
            logger.exception(e)
            return {"status": "ERROR", "message": str(e)}
