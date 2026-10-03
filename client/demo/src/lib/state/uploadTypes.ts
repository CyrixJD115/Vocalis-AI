// Types shared by the model upload UI (mirrors the lib's useServerSetting types,
// which are React-hook tied in the original client library).

import type { VoiceChangerType } from "@vc-lib/const";

export const ModelAssetName = {
    iconFile: "iconFile",
} as const;
export type ModelAssetName = (typeof ModelAssetName)[keyof typeof ModelAssetName];

export const ModelFileKind = {
    rvcModel: "rvcModel",
    rvcIndex: "rvcIndex",
} as const;
export type ModelFileKind = (typeof ModelFileKind)[keyof typeof ModelFileKind];

export type ModelFile = {
    file: File;
    kind: ModelFileKind;
    dir: string;
};

export type ModelUploadSetting = {
    voiceChangerType: VoiceChangerType;
    slot: number;
    isSampleMode: boolean;
    sampleId: string | null;

    files: ModelFile[];
    params: any;
};
