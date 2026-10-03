import {
    DefaultServerSetting,
    MergeModelRequest,
    OnnxExporterInfo,
    ServerInfo,
    ServerSettingKey,
    VoiceChangerServerSetting,
} from "@vc-lib/const";
import { ServerConfigurator } from "@vc-lib/client/ServerConfigurator";
import type { ModelUploadSetting } from "./uploadTypes";

// Server-side state. Talks to the python server over REST only, so it works
// before any user gesture (unlike the original app, which gated everything
// behind AudioContext creation).

export type {
    ModelAssetName,
    ModelFile,
    ModelFileKind,
    ModelUploadSetting,
} from "./uploadTypes";

class ServerState {
    serverSetting = $state<ServerInfo>(DefaultServerSetting);
    uploadProgress = $state<number>(0);
    isUploading = $state<boolean>(false);

    #configurator = new ServerConfigurator("");

    #setServerSetting = (info: ServerInfo) => {
        if (!info.modelSlots) {
            // サーバが情報を空で返したとき。Web版対策
            return;
        }
        this.serverSetting = info;
    };

    reloadServerInfo = async (): Promise<ServerInfo> => {
        const res = await this.#configurator.getSettings();
        this.#setServerSetting(res);
        return res;
    };

    updateServerSettings = async (setting: ServerInfo) => {
        for (const k of Object.values(ServerSettingKey)) {
            const key = k as keyof VoiceChangerServerSetting;
            const cur_v = this.serverSetting[key];
            const new_v = setting[key];
            if (cur_v != new_v) {
                const res = await this.#configurator.updateSettings(k, "" + new_v);
                this.#setServerSetting(res);
            }
        }
    };

    uploadModel = async (setting: ModelUploadSetting) => {
        this.uploadProgress = 0;
        this.isUploading = true;
        try {
            if (setting.isSampleMode == false) {
                const progRate = 1 / setting.files.length;
                for (let i = 0; i < setting.files.length; i++) {
                    const progOffset = 100 * i * progRate;
                    await this.#configurator.uploadFile2(setting.files[i].dir, setting.files[i].file, (progress: number, _end: boolean) => {
                        this.uploadProgress = progress * progRate + progOffset;
                    });
                }
            }
            const params = {
                ...setting,
                files: setting.files.map((f) => {
                    return { name: f.file.name, kind: f.kind, dir: f.dir };
                }),
            };
            await this.#configurator.loadModel(0, false, JSON.stringify(params));
        } finally {
            this.uploadProgress = 0;
            this.isUploading = false;
            await this.reloadServerInfo();
        }
    };

    uploadAssets = async (slot: number, name: string, file: File) => {
        await this.#configurator.uploadFile2("", file, () => {});
        const assetUploadSetting = {
            slot,
            name,
            file: file.name,
        };
        await this.#configurator.uploadAssets(JSON.stringify(assetUploadSetting));
        await this.reloadServerInfo();
    };

    getOnnx = async (): Promise<OnnxExporterInfo> => {
        return this.#configurator.export2onnx();
    };

    mergeModel = async (request: MergeModelRequest): Promise<ServerInfo> => {
        const serverInfo = await this.#configurator.mergeModel(request);
        this.#setServerSetting(serverInfo);
        return serverInfo;
    };

    updateModelDefault = async (): Promise<ServerInfo> => {
        const serverInfo = await this.#configurator.updateModelDefault();
        this.#setServerSetting(serverInfo);
        return serverInfo;
    };

    updateModelInfo = async (slot: number, key: string, val: string): Promise<ServerInfo> => {
        const serverInfo = await this.#configurator.updateModelInfo(slot, key, val);
        this.#setServerSetting(serverInfo);
        return serverInfo;
    };
}

export const serverState = new ServerState();
