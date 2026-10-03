import {
    AUDIO_ELEMENT_FOR_PLAY_MONITOR,
    AUDIO_ELEMENT_FOR_PLAY_RESULT,
    AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK,
    AUDIO_ELEMENT_FOR_SAMPLING_INPUT,
    AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT,
    INDEXEDDB_KEY_AUDIO_MONITR,
    INDEXEDDB_KEY_AUDIO_OUTPUT,
} from "../const";
import { idb } from "./appState.svelte";
import { serverState } from "./serverState.svelte";
import { vcClientState } from "./vcClient.svelte";

export type TextInputResolve = {
    resolve: (value: string | PromiseLike<string>) => void;
};

class GuiState {
    isConverting = $state<boolean>(false);
    isAnalyzing = $state<boolean>(false);
    voiceChangerSettingsChanged = $state<boolean>(false);

    // Dialog visibility (replaces the DOM-checkbox state controls of the React app)
    showWaitingDialog = $state<boolean>(false);
    showStartingNoticeDialog = $state<boolean>(false);
    showModelSlotManagerDialog = $state<boolean>(false);
    showMergeLabDialog = $state<boolean>(false);
    showAdvancedSettingDialog = $state<boolean>(false);
    showServerInfoDialog = $state<boolean>(false);
    showClientInfoDialog = $state<boolean>(false);
    showPassThroughDialog = $state<boolean>(false);
    showTextInputDialog = $state<boolean>(false);

    #textInputResolve: TextInputResolve | null = null;

    // Devices
    inputAudioDeviceInfo = $state<MediaDeviceInfo[]>([]);
    outputAudioDeviceInfo = $state<MediaDeviceInfo[]>([]);
    audioInputForGUI = $state<string>("none");
    audioOutputForGUI = $state<string>("none");
    audioMonitorForGUI = $state<string>("none");
    fileInputEchoback = $state<boolean>(false);
    shareScreenEnabled = $state<boolean>(false);
    audioOutputForAnalyzer = $state<string>("default");

    #checkDeviceAvailable = false;
    #pollTimer: ReturnType<typeof setTimeout> | null = null;

    #reloadDeviceInfoInternal = async (): Promise<[MediaDeviceInfo[], MediaDeviceInfo[]]> => {
        // デバイスチェックの空振り
        if (!this.#checkDeviceAvailable) {
            try {
                const ms = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
                ms.getTracks().forEach((x) => {
                    x.stop();
                });
                this.#checkDeviceAvailable = true;
            } catch (e) {
                console.warn("Enumerate device error::", e);
            }
        }
        const mediaDeviceInfos = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = mediaDeviceInfos.filter((x) => x.kind == "audioinput");
        audioInputs.push({ deviceId: "none", groupId: "none", kind: "audioinput", label: "none", toJSON: () => {} } as MediaDeviceInfo);
        audioInputs.push({ deviceId: "file", groupId: "file", kind: "audioinput", label: "file", toJSON: () => {} } as MediaDeviceInfo);
        audioInputs.push({ deviceId: "screen", groupId: "screen", kind: "audioinput", label: "system(only win)", toJSON: () => {} } as MediaDeviceInfo);
        const audioOutputs = mediaDeviceInfos.filter((x) => x.kind == "audiooutput");
        audioOutputs.push({ deviceId: "none", groupId: "none", kind: "audiooutput", label: "none", toJSON: () => {} } as MediaDeviceInfo);
        return [audioInputs, audioOutputs];
    };

    reloadDeviceInfo = async () => {
        const audioInfo = await this.#reloadDeviceInfoInternal();
        this.inputAudioDeviceInfo = audioInfo[0];
        this.outputAudioDeviceInfo = audioInfo[1];
    };

    startDevicePolling = () => {
        const pollDevices = async () => {
            const checkDeviceDiff = (knownDeviceIds: Set<string>, newDeviceIds: Set<string>) => {
                const deleted = new Set([...knownDeviceIds].filter((x) => !newDeviceIds.has(x)));
                const added = new Set([...newDeviceIds].filter((x) => !knownDeviceIds.has(x)));
                return { deleted, added };
            };
            try {
                const audioInfo = await this.#reloadDeviceInfoInternal();
                const knownAudioinputIds = new Set(this.inputAudioDeviceInfo.map((x) => x.deviceId));
                const newAudioinputIds = new Set(audioInfo[0].map((x) => x.deviceId));
                const knownAudiooutputIds = new Set(this.outputAudioDeviceInfo.map((x) => x.deviceId));
                const newAudiooutputIds = new Set(audioInfo[1].map((x) => x.deviceId));
                const audioInputDiff = checkDeviceDiff(knownAudioinputIds, newAudioinputIds);
                const audioOutputDiff = checkDeviceDiff(knownAudiooutputIds, newAudiooutputIds);
                if (audioInputDiff.deleted.size > 0 || audioInputDiff.added.size > 0) {
                    this.inputAudioDeviceInfo = audioInfo[0];
                }
                if (audioOutputDiff.deleted.size > 0 || audioOutputDiff.added.size > 0) {
                    this.outputAudioDeviceInfo = audioInfo[1];
                }
                this.#syncCachedInputDevice();
            } catch (err) {
                console.error("An error occurred during enumeration of devices:", err);
            }
            this.#pollTimer = setTimeout(pollDevices, 1000 * 3);
        };
        pollDevices();
    };

    stopDevicePolling = () => {
        if (this.#pollTimer) {
            clearTimeout(this.#pollTimer);
            this.#pollTimer = null;
        }
    };

    ////////////////
    // setters
    ////////////////
    setAudioInputForGUI = (val: string) => {
        this.audioInputForGUI = val;
    };
    setAudioOutputForGUI = (val: string) => {
        this.audioOutputForGUI = val;
        idb.setItem(INDEXEDDB_KEY_AUDIO_OUTPUT, val);
        this.applyOutputRouting();
    };
    setAudioMonitorForGUI = (val: string) => {
        this.audioMonitorForGUI = val;
        idb.setItem(INDEXEDDB_KEY_AUDIO_MONITR, val);
        this.applyMonitorRouting();
    };
    setAudioOutputForAnalyzer = (val: string) => {
        this.audioOutputForAnalyzer = val;
        this.setAnalyzerSinkId(val);
    };
    setFileInputEchoback = (val: boolean) => {
        this.fileInputEchoback = val;
        const echoback = document.getElementById(AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK) as HTMLAudioElement | null;
        if (echoback) {
            echoback.volume = val ? 1 : 0;
        }
        this.applyOutputRouting();
    };
    setVoiceChangerSettingsChanged = (val: boolean) => {
        this.voiceChangerSettingsChanged = val;
    };

    ////////////////
    // text input dialog (promise resolver)
    ////////////////
    requestTextInput = async (): Promise<string> => {
        const p = new Promise<string>((resolve) => {
            this.#textInputResolve = { resolve };
        });
        this.showTextInputDialog = true;
        return p;
    };
    resolveTextInput = (text: string) => {
        this.#textInputResolve?.resolve(text);
        this.#textInputResolve = null;
        this.showTextInputDialog = false;
    };

    ////////////////
    // audio routing
    ////////////////
    loadPersistedOutputDevices = async () => {
        const output = await idb.getItem(INDEXEDDB_KEY_AUDIO_OUTPUT);
        if (output) {
            this.audioOutputForGUI = output as string;
        }
        const monitor = await idb.getItem(INDEXEDDB_KEY_AUDIO_MONITR);
        if (monitor) {
            this.audioMonitorForGUI = monitor as string;
        }
    };

    applyOutputRouting = () => {
        this.#routeElements([AUDIO_ELEMENT_FOR_PLAY_RESULT, AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK], this.audioOutputForGUI, this.fileInputEchoback ? 1 : 0, true);
    };

    applyMonitorRouting = () => {
        this.#routeElements([AUDIO_ELEMENT_FOR_PLAY_MONITOR], this.audioMonitorForGUI, 1, false);
    };

    #routeElements = (elemIds: string[], deviceId: string, volume: number, echobackFirst: boolean) => {
        navigator.mediaDevices.enumerateDevices().then((mediaDeviceInfos) => {
            for (const elemId of elemIds) {
                const audio = document.getElementById(elemId) as HTMLAudioElement | null;
                if (!audio) {
                    continue;
                }
                let vol = volume;
                if (serverState.serverSetting.enableServerAudio != 0) {
                    audio.volume = 0;
                    continue;
                }
                if (deviceId == "none") {
                    audio.setSinkId("")
                        .then(() => {
                            audio.volume = 0;
                        })
                        .catch((e) => {
                            console.error("catch:" + e);
                        });
                    continue;
                }
                const device = mediaDeviceInfos.find((x) => x.kind == "audiooutput" && x.deviceId == deviceId);
                if (device) {
                    audio.setSinkId(device.deviceId)
                        .catch((e) => {
                            console.error("catch:" + e);
                        });
                } else {
                    console.warn("No audio output device. use default");
                }
                if (echobackFirst && elemId == AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK) {
                    vol = this.fileInputEchoback ? 1 : 0;
                }
                audio.volume = vol;
            }
        });
    };

    setAnalyzerSinkId = (deviceId: string) => {
        for (const elemId of [AUDIO_ELEMENT_FOR_SAMPLING_INPUT, AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT]) {
            const audio = document.getElementById(elemId) as HTMLAudioElement | null;
            if (!audio) {
                continue;
            }
            try {
                audio.setSinkId(deviceId);
            } catch (e) {
                console.log(e);
            }
        }
    };

    ////////////////
    // startup
    ////////////////
    // The persisted client input device is only meaningful once the device list
    // has been enumerated; re-check on every poll like the React effect did.
    #syncCachedInputDevice = () => {
        const clientSetting = vcClientState.setting.voiceChangerClientSetting;
        if (typeof clientSetting.audioInput == "string" && this.inputAudioDeviceInfo.some((x) => x.deviceId == clientSetting.audioInput)) {
            this.audioInputForGUI = clientSetting.audioInput;
        }
    };

    initialize = async () => {
        await this.loadPersistedOutputDevices();
        this.startDevicePolling();
        setTimeout(() => {
            this.showStartingNoticeDialog = true;
        }, 100);
    };
}

export const guiState = new GuiState();
