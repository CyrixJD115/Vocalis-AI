export const trimfileName = (name: string, length: number) => {
    const trimmed = name.replace(/^.*[\\\/]/, "");
    return trimmed.length > length ? trimmed.substring(0, length) + "..." : trimmed;
};

export const checkExtention = (filename: string, acceptExtentions: string[]) => {
    const ext = filename.split(".").pop() || "";
    return acceptExtentions.includes(ext);
};

export const basename = (path: string) => {
    return path.split(/[\/\\]/).pop() || path;
};

export const fileSelector = async (accept: string): Promise<File> => {
    return new Promise<File>((resolve) => {
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = accept;
        fileInput.onchange = () => {
            if (fileInput.files && fileInput.files.length > 0) {
                resolve(fileInput.files[0]);
            }
        };
        fileInput.click();
    });
};

export const fileSelectorAsDataURL = async (accept: string): Promise<[File, string]> => {
    return new Promise<[File, string]>((resolve) => {
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = accept;
        fileInput.onchange = () => {
            if (fileInput.files && fileInput.files.length > 0) {
                const file = fileInput.files[0];
                const reader = new FileReader();
                reader.onload = () => {
                    resolve([file, reader.result as string]);
                };
                reader.readAsDataURL(file);
            }
        };
        fileInput.click();
    });
};

export const downloadFile = (url: string, filename: string) => {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    link.remove();
};

export const downloadRecord = (record: Float32Array, sampleRate: number) => {
    // 16bit mono PCM WAV
    const buffer = new ArrayBuffer(44 + record.length * 2);
    const view = new DataView(buffer);
    const writeString = (offset: number, str: string) => {
        for (let i = 0; i < str.length; i++) {
            view.setUint8(offset + i, str.charCodeAt(i));
        }
    };
    writeString(0, "RIFF");
    view.setUint32(4, 36 + record.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, record.length * 2, true);
    let offset = 44;
    for (let i = 0; i < record.length; i++) {
        const s = Math.max(-1, Math.min(1, record[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
        offset += 2;
    }
    const blob = new Blob([view], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    downloadFile(url, "output.wav");
    URL.revokeObjectURL(url);
};

export const createDummyMediaStream = (ctx: AudioContext) => {
    const gain = ctx.createGain();
    gain.gain.value = 0.0;
    gain.connect(ctx.destination);
    const stream = (gain as unknown as { stream?: MediaStream }).stream;
    // MediaStreamAudioDestinationNode is the reliable way to obtain a silent stream.
    const dst = ctx.createMediaStreamDestination();
    gain.connect(dst);
    return dst.stream;
};
