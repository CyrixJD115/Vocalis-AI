export const AUDIO_ELEMENT_FOR_PLAY_RESULT = "audio-result";
export const AUDIO_ELEMENT_FOR_PLAY_MONITOR = "audio-monitor";
export const AUDIO_ELEMENT_FOR_TEST_CONVERTED = "audio-test-converted";
export const AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK = "audio-test-converted-echoback";
export const AUDIO_ELEMENT_FOR_SAMPLING_INPUT = "body-wav-container-wav-input";
export const AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT = "body-wav-container-wav-output";

export const INDEXEDDB_KEY_AUDIO_OUTPUT = "INDEXEDDB_KEY_AUDIO_OUTPUT";
export const INDEXEDDB_KEY_AUDIO_MONITR = "INDEXEDDB_KEY_AUDIO_MONITR";

export const MODEL_ICON_BLANK_URL = "/assets/icons/blank.png";

export const isDesktopApp = () => {
    return navigator.userAgent.indexOf("Electron") >= 0;
};

export const openExternal = (url: string) => {
    if (isDesktopApp()) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).electronAPI?.openBrowser(url);
    } else {
        window.open(url, "_blank", "noopener,noreferrer");
    }
};
