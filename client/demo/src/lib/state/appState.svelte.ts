import localforage from "localforage";
import { INDEXEDDB_DB_APP_NAME, INDEXEDDB_DB_NAME } from "@vc-lib/const";

export type AppGuiSetting = {
    type: string;
    id: string;
    front: {
        modelSlotControl: {
            name: string;
            options: {
                mainTitle?: string;
                subTitle?: string;
                detectors?: string[];
                inputChunkNums?: number[];
            };
        }[];
    };
};

const DefaultAppGuiSetting: AppGuiSetting = {
    type: "demo",
    id: "RVC",
    front: {
        modelSlotControl: [],
    },
};

// IndexedDB (localforage) shared with the python-side conventions.
localforage.config({
    driver: localforage.INDEXEDDB,
    name: INDEXEDDB_DB_APP_NAME,
    version: 1.0,
    storeName: INDEXEDDB_DB_NAME,
    description: "appStorage",
});

export const idb = {
    setItem: async (key: string, value: unknown) => {
        await localforage.setItem(`default_${key}`, value);
    },
    getItem: async (key: string) => {
        return await localforage.getItem(`default_${key}`);
    },
    removeItem: async (key: string) => {
        await localforage.removeItem(`default_${key}`);
    },
    removeDB: async () => {
        const keys = await localforage.keys();
        for (const key of keys) {
            await localforage.removeItem(key);
        }
    },
};

class AppState {
    // The AudioContext can only be created after a user gesture (browser policy).
    // It is created on the first pointer interaction, exactly like the original app.
    audioContext = $state<AudioContext | null>(null);
    appGuiSetting = $state<AppGuiSetting>(DefaultAppGuiSetting);
    guiSettingLoaded = $state<boolean>(false);
    version = $state<string>("");
    edition = $state<string>("");

    constructor() {
        const onFirstGesture = () => {
            this.#createAudioContext();
            document.removeEventListener("touchstart", onFirstGesture);
            document.removeEventListener("mousedown", onFirstGesture);
        };
        document.addEventListener("touchstart", onFirstGesture, { passive: true });
        document.addEventListener("mousedown", onFirstGesture, { passive: true });
    }

    #createAudioContext() {
        if (this.audioContext) {
            return;
        }
        const urlParams = new URLSearchParams(window.location.search);
        const sampleRate = parseInt(urlParams.get("sample_rate") || "48000") || 48000;
        this.audioContext = new AudioContext({ sampleRate });
        console.log("[appState] AudioContext created", sampleRate);
    }

    loadAppGuiSetting = async () => {
        try {
            const res = await fetch("/assets/gui_settings/GUI.json");
            const info = await res.json();
            this.appGuiSetting = info;
        } catch (e) {
            console.error("[appState] failed to load GUI.json", e);
        }
        this.guiSettingLoaded = true;
    };

    loadServerMeta = async () => {
        try {
            const version = await fetch("/version");
            this.version = await version.text();
        } catch (e) {
            console.warn("[appState] failed to load version", e);
        }
        try {
            const edition = await fetch("/edition");
            this.edition = await edition.text();
        } catch (e) {
            console.warn("[appState] failed to load edition", e);
        }
    };
}

export const appState = new AppState();
