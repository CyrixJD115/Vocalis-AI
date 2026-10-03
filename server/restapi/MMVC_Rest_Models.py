import os
import shutil
import uuid
import zipfile

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from const import UPLOAD_DIR
from settings import get_settings
from restapi.mods.FileUploader import sanitize_filename
from voice_changer.VoiceChangerManager import VoiceChangerManager
from voice_changer.utils.LoadModelParams import LoadModelParams, LoadModelParamFile

import logging
logger = logging.getLogger(__name__)

MODEL_EXTS = {".pth", ".onnx", ".safetensors"}
INDEX_EXTS = {".index"}
ICON_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


class MMVC_Rest_Models:
    """Script-friendly model management API.

    GET    /api/models          - list installed models
    POST   /api/models          - upload a model (loose files or a .zip) and add it
    DELETE /api/models/{slot}   - remove a model
    """

    def __init__(self, voiceChangerManager: VoiceChangerManager):
        self.voiceChangerManager = voiceChangerManager
        self.router = APIRouter()
        self.router.add_api_route("/api/models", self.list_models, methods=["GET"])
        self.router.add_api_route("/api/models", self.upload_model, methods=["POST"])
        self.router.add_api_route("/api/models/{slot}", self.delete_model, methods=["DELETE"])

    def list_models(self):
        slots = self.voiceChangerManager.modelSlotManager.getAllSlotInfo(reload=True)
        models = []
        for i, slotInfo in enumerate(slots):
            if slotInfo.voiceChangerType is None:
                continue
            models.append({
                "slot": i,
                "name": slotInfo.name,
                "voiceChangerType": slotInfo.voiceChangerType,
                "description": slotInfo.description,
                "credit": slotInfo.credit,
                "iconFile": slotInfo.iconFile,
                "modelFile": getattr(slotInfo, "modelFile", ""),
                "indexFile": getattr(slotInfo, "indexFile", ""),
                "samplingRate": getattr(slotInfo, "samplingRate", -1),
                "version": getattr(slotInfo, "version", ""),
                "deprecated": getattr(slotInfo, "deprecated", False),
            })
        return {
            "selected": self.voiceChangerManager.settings.modelSlotIndex,
            "models": models,
        }

    async def upload_model(
        self,
        file: list[UploadFile] = File(...),
        slot: int = Form(-1),
        name: str = Form(""),
        activate: bool = Form(False),
    ):
        # Files are staged in a temporary directory under UPLOAD_DIR; the
        # manager moves model/index files into the slot directory.
        staging = uuid.uuid4().hex
        staging_dir = os.path.join(UPLOAD_DIR, staging)
        os.makedirs(staging_dir, exist_ok=True)
        model_file: str | None = None
        index_file: str | None = None
        icon_file: str | None = None

        def stage(data, filename: str):
            nonlocal model_file, index_file, icon_file
            filename = sanitize_filename(filename)
            if not filename:
                return
            ext = os.path.splitext(filename)[1].lower()
            if ext in MODEL_EXTS and model_file is None:
                model_file = filename
            elif ext in INDEX_EXTS and index_file is None:
                index_file = filename
            elif ext in ICON_EXTS and icon_file is None:
                icon_file = filename
            else:
                return
            with open(os.path.join(staging_dir, filename), "wb") as f:
                f.write(data)

        try:
            for upload in file:
                if upload.filename and upload.filename.lower().endswith(".zip"):
                    try:
                        with zipfile.ZipFile(upload.file) as z:
                            for member in z.infolist():
                                if member.is_dir():
                                    continue
                                # basename() also protects against path traversal
                                stage(z.read(member), os.path.basename(member.filename))
                    except zipfile.BadZipFile:
                        raise HTTPException(status_code=400, detail=f"{upload.filename} is not a valid zip archive")
                else:
                    stage(upload.file.read(), upload.filename or "")

            if model_file is None:
                raise HTTPException(
                    status_code=400,
                    detail="No RVC model file found. Provide a .pth/.onnx/.safetensors file or a .zip containing one.",
                )

            if slot < 0:
                slots = self.voiceChangerManager.modelSlotManager.getAllSlotInfo(reload=True)
                slot = next((i for i, s in enumerate(slots) if s.voiceChangerType is None), None)
                if slot is None:
                    raise HTTPException(status_code=409, detail="No free model slot")

            files = [LoadModelParamFile(name=model_file, kind="rvcModel", dir=staging)]
            if index_file is not None:
                files.append(LoadModelParamFile(name=index_file, kind="rvcIndex", dir=staging))
            params = LoadModelParams(
                voiceChangerType="RVC",
                slot=slot,
                isSampleMode=False,
                sampleId="",
                files=files,
                params={},
            )
            await self.voiceChangerManager.load_model(params)

            if name:
                self.voiceChangerManager.modelSlotManager.update_model_info(slot, "name", name)
            if icon_file is not None:
                slot_dir = os.path.join(get_settings().model_dir, str(slot))
                shutil.copy(os.path.join(staging_dir, icon_file), os.path.join(slot_dir, icon_file))
                self.voiceChangerManager.modelSlotManager.update_model_info(slot, "iconFile", os.path.join(slot_dir, icon_file))

            if activate:
                self.voiceChangerManager.update_settings("modelSlotIndex", slot)

            slots = self.voiceChangerManager.modelSlotManager.getAllSlotInfo(reload=True)
            model_name = name or slots[slot].name
            logger.info(f"Model '{model_name}' added to slot {slot}" + (" and activated" if activate else ""))
            return {
                "status": "OK",
                "slot": slot,
                "name": model_name,
                "indexFile": index_file,
                "activated": activate,
            }
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def delete_model(self, slot: int):
        slots = self.voiceChangerManager.modelSlotManager.getAllSlotInfo(reload=True)
        if slot < 0 or slot >= len(slots) or slots[slot].voiceChangerType is None:
            raise HTTPException(status_code=404, detail=f"Model slot {slot} is empty")
        try:
            self.voiceChangerManager.delete_model(slot)
        except OSError as e:
            raise HTTPException(
                status_code=409,
                detail=f"Could not delete model files (they may be locked by a running conversion): {e}",
            )
        return {"status": "OK", "deleted": slot, "selected": self.voiceChangerManager.settings.modelSlotIndex}
