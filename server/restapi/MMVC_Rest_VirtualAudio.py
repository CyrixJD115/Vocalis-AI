import logging

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

    def _device_names(self) -> list[str]:
        try:
            inputs, outputs = list_audio_device()
            return [d.name for d in inputs] + [d.name for d in outputs]
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
