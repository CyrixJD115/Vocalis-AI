import {
    ClientSetting,
    DefaultClientSettng,
    VoiceChangerClientSetting,
    WorkletNodeSetting,
    WorkletSetting,
} from "@vc-lib/const";
import { VoiceChangerClient } from "@vc-lib/VoiceChangerClient";
import { appState, idb } from "./appState.svelte";
import { serverState } from "./serverState.svelte";
import { toast } from "../toast.svelte";

export type PerformanceStats = {
    vol: number;
    responseTime: number;
    preprocessTime: number;
    mainprocessTime: number;
    postprocessTime: number;
};

export const DefaultPerformanceStats: PerformanceStats = {
    vol: 0,
    responseTime: 0,
    preprocessTime: 0,
    mainprocessTime: 0,
    postprocessTime: 0,
};

// Audio-side client state. The VoiceChangerClient (audio worklet + socket.io)
// needs an AudioContext, which requires a user gesture, so it is created
// lazily; REST-only interactions go through serverState instead.

class VCClientState {
    initialized = $state<boolean>(false);
    setting = $state<ClientSetting>(DefaultClientSettng);
    bufferingTime = $state<number>(0);
    performance = $state<PerformanceStats>(DefaultPerformanceStats);

    #client: VoiceChangerClient | null = null;
    #clientPromise: Promise<VoiceChangerClient> | null = null;

    get client(): VoiceChangerClient | null {
        return this.#client;
    }

    ensureClient = async (): Promise<VoiceChangerClient> => {
        if (this.#client) {
            return this.#client;
        }
        if (!this.#clientPromise) {
            this.#clientPromise = this.#createClient();
        }
        return this.#clientPromise;
    };

    #createClient = async (): Promise<VoiceChangerClient> => {
        // The AudioContext is created on the first user gesture. When start is
        // clicked, that gesture has already happened; but keep polling as a
        // safety net for programmatic paths.
        let ctx = appState.audioContext;
        for (let i = 0; i < 100 && !ctx; i++) {
            await new Promise((r) => setTimeout(r, 100));
            ctx = appState.audioContext;
        }
        if (!ctx) {
            throw new Error("AudioContext is not initialized. Interact with the page first.");
        }

        const client = new VoiceChangerClient(ctx, true, {
            notifySendBufferingTime: (val: number) => {
                this.bufferingTime = val;
            },
            notifyPerformanceStats: (responseTime: number, vol: number, perf: number[]) => {
                const [preprocessTime, mainprocessTime, postprocessTime] = perf;
                this.performance = {
                    vol,
                    responseTime,
                    preprocessTime: Math.ceil(preprocessTime * 1000),
                    mainprocessTime: Math.ceil(mainprocessTime * 1000),
                    postprocessTime: Math.ceil(postprocessTime * 1000),
                };
            },
            notifyException: (_: string, mes: string) => {
                toast.error(mes);
            },
        });
        await client.isInitialized();

        // Load persisted settings and merge them with the server's chunk size.
        const persisted = (await idb.getItem("clientSetting")) as ClientSetting | null;
        const loaded: ClientSetting = persisted
            ? { ...persisted, workletNodeSetting: { ...persisted.workletNodeSetting } }
            : { ...DefaultClientSettng, workletNodeSetting: { ...DefaultClientSettng.workletNodeSetting } };
        loaded.workletNodeSetting.inputChunkNum = serverState.serverSetting.serverReadChunkSize;

        this.setting = loaded;
        await client.updateClientSetting(loaded.voiceChangerClientSetting);
        client.updateWorkletNodeSetting(loaded.workletNodeSetting);
        await idb.setItem("clientSetting", this.#sanitizeForPersist(loaded));

        this.#client = client;
        this.initialized = true;
        console.log("[vcClient] client initialized");

        this.attachAudioElements();
        return client;
    };

    #sanitizeForPersist = (setting: ClientSetting): ClientSetting => {
        const storeData: ClientSetting = {
            ...setting,
            voiceChangerClientSetting: { ...setting.voiceChangerClientSetting },
            workletNodeSetting: { ...setting.workletNodeSetting },
            workletSetting: { ...setting.workletSetting },
        };
        if (typeof storeData.voiceChangerClientSetting.audioInput != "string") {
            storeData.voiceChangerClientSetting.audioInput = "none";
        }
        return storeData;
    };

    attachAudioElements = () => {
        if (!this.#client) {
            return;
        }
        const output = document.getElementById("audio-result") as HTMLAudioElement | null;
        if (output && output.paused) {
            output.srcObject = this.#client.stream;
            output.play().catch(() => {});
        }
        const monitor = document.getElementById("audio-monitor") as HTMLAudioElement | null;
        if (monitor && monitor.paused) {
            monitor.srcObject = this.#client.monitorStream;
            monitor.play().catch(() => {});
        }
    };

    start = async () => {
        const client = await this.ensureClient();
        await client.start();
        this.attachAudioElements();
    };

    stop = async () => {
        if (!this.#client) {
            return;
        }
        await this.#client.stop();
    };

    startOutputRecording = () => {
        this.#client?.startOutputRecording();
    };

    stopOutputRecording = async (): Promise<Float32Array> => {
        if (!this.#client) {
            return new Float32Array();
        }
        return this.#client.stopOutputRecording();
    };

    trancateBuffer = () => {
        this.#client?.trancateBuffer();
    };

    setVoiceChangerClientSetting = async (_voiceChangerClientSetting: VoiceChangerClientSetting) => {
        this.setting = { ...this.setting, voiceChangerClientSetting: _voiceChangerClientSetting };
        const client = this.#client;
        if (client) {
            try {
                await client.updateClientSetting(_voiceChangerClientSetting);
            } catch (e) {
                console.error(e);
                throw e;
            }
        }
        await idb.setItem("clientSetting", this.#sanitizeForPersist(this.setting));
    };

    setWorkletNodeSetting = (_workletNodeSetting: WorkletNodeSetting) => {
        this.setting = { ...this.setting, workletNodeSetting: _workletNodeSetting };
        this.#client?.updateWorkletNodeSetting(_workletNodeSetting);
        idb.setItem("clientSetting", this.#sanitizeForPersist(this.setting));
    };

    setWorkletSetting = (_workletSetting: WorkletSetting) => {
        this.setting = { ...this.setting, workletSetting: _workletSetting };
        idb.setItem("clientSetting", this.#sanitizeForPersist(this.setting));
    };

    getInfo = async () => {
        await this.ensureClient();
    };

    clearSetting = async () => {
        await idb.removeItem("clientSetting");
    };
}

export const vcClientState = new VCClientState();
