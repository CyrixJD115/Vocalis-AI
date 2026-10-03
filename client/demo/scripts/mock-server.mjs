// Mock API server for UI development without the python backend.
// Serves the built dist/ plus canned /info, /version and /edition responses.
//
// Usage: node scripts/mock-server.mjs [port]   (default 8899)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.resolve(__dirname, "../dist");
const PORT = Number(process.argv[2] || 8899);

const info = {
    passThrough: false,
    inputSampleRate: 48000,
    crossFadeOverlapSize: 0.1,
    recordIO: 0,
    enableServerAudio: 0,
    serverAudioStated: 0,
    serverAudioSampleRate: 48000,
    serverInputAudioSampleRate: 48000,
    serverOutputAudioSampleRate: 48000,
    serverMonitorAudioSampleRate: 48000,
    serverInputAudioBufferSize: 1024 * 24,
    serverOutputAudioBufferSize: 1024 * 24,
    serverInputDeviceId: -1,
    serverOutputDeviceId: -1,
    serverMonitorDeviceId: -1,
    serverReadChunkSize: 96,
    serverInputAudioGain: 1.0,
    serverOutputAudioGain: 1.0,
    serverMonitorAudioGain: 1.0,
    asioInputChannel: -1,
    asioOutputChannel: -1,
    srcId: 0,
    dstId: 0,
    gpu: 0,
    f0Factor: 1.0,
    f0Detector: "rmvpe_onnx",
    tran: 0,
    formantShift: 0,
    useONNX: 0,
    silentThreshold: -75,
    extraConvertSize: 4,
    indexRatio: 0,
    protect: 0.5,
    modelSamplingRate: 48000,
    silenceFront: 1,
    forceFp32: 0,
    disableJit: 0,
    modelSlotIndex: 0,
    maxInputLength: 128 * 2048,
    status: "ok",
    gpus: [
        { id: 0, name: "NVIDIA GeForce RTX 3070", memory: 8589934592 },
        { id: -1, name: "cpu", memory: 0 },
    ],
    voiceChangerParams: { model_dir: "/models" },
    serverAudioInputDevices: [
        { index: 0, name: "Microsoft Sound Mapper - Input", hostAPI: "MME", maxInputChannels: 2, maxOutputChannels: 0, default_samplerate: 48000 },
        { index: 1, name: "Microphone (Realtek Audio)", hostAPI: "MME", maxInputChannels: 2, maxOutputChannels: 0, default_samplerate: 48000 },
        { index: 3, name: "ASIO Fireface", hostAPI: "ASIO", maxInputChannels: 12, maxOutputChannels: 0, default_samplerate: 48000 },
    ],
    serverAudioOutputDevices: [
        { index: 0, name: "Microsoft Sound Mapper - Output", hostAPI: "MME", maxInputChannels: 0, maxOutputChannels: 2, default_samplerate: 48000 },
        { index: 2, name: "Speakers (Realtek Audio)", hostAPI: "MME", maxInputChannels: 0, maxOutputChannels: 2, default_samplerate: 48000 },
        { index: 4, name: "ASIO Fireface", hostAPI: "ASIO", maxInputChannels: 0, maxOutputChannels: 12, default_samplerate: 48000 },
    ],
    sampleModels: [
        {
            id: "test1",
            voiceChangerType: "RVC",
            lang: "Japanese",
            tag: ["test"],
            name: "Amitaro (sample)",
            termsOfUseUrl: "https://example.com/terms",
            icon: "/models/samples/amitaro.png",
            credit: "",
            description: "",
            sampleRate: 40000,
            modelType: "pyTorchRVCv2",
            f0: true,
            indexUrl: "",
            featureUrl: "",
        },
        {
            id: "test2",
            voiceChangerType: "RVC",
            lang: "English",
            tag: ["test"],
            name: "English Voice (sample)",
            termsOfUseUrl: "",
            icon: "/models/samples/english.png",
            credit: "",
            description: "",
            sampleRate: 48000,
            modelType: "pyTorchRVCv2",
            f0: false,
            indexUrl: "",
            featureUrl: "",
        },
    ],
    modelSlots: [
        {
            slotIndex: 0,
            voiceChangerType: "RVC",
            name: "Amitaro v2",
            description: "",
            credit: "",
            termsOfUseUrl: "https://example.com/terms",
            iconFile: "icon.png",
            speakers: { 0: "Amitaro", 1: "inherit" },
            isONNX: false,
            modelFile: "amitaro_v2_40k.pth",
            modelFileOnnx: "",
            indexFile: "added_ivf2_amitaro.index",
            defaultIndexRatio: 0,
            defaultProtect: 0.5,
            defaultTune: 0,
            defaultFormantShift: 0,
            modelType: "pyTorchRVCv2",
            modelTypeOnnx: "onnxRVCv2Nono",
            embChannels: 256,
            f0: true,
            samplingRate: 40000,
            deprecated: false,
        },
        {
            slotIndex: 1,
            voiceChangerType: "RVC",
            name: "Tsukuyomi-chan",
            description: "",
            credit: "",
            termsOfUseUrl: "",
            iconFile: "",
            speakers: { 0: "Tsukuyomi" },
            isONNX: false,
            modelFile: "tsukuyomi_32k.pth",
            modelFileOnnx: "",
            indexFile: "",
            defaultIndexRatio: 0,
            defaultProtect: 0.5,
            defaultTune: 12,
            defaultFormantShift: 0,
            modelType: "pyTorchRVC",
            modelTypeOnnx: "onnxRVCNono",
            embChannels: 256,
            f0: true,
            samplingRate: 32000,
            deprecated: false,
        },
        {
            slotIndex: 2,
            voiceChangerType: "RVC",
            name: "",
            description: "",
            credit: "",
            termsOfUseUrl: "",
            iconFile: "",
            speakers: {},
            isONNX: false,
            modelFile: "",
            modelFileOnnx: "",
            indexFile: "",
            defaultIndexRatio: 0,
            defaultProtect: 0.5,
            defaultTune: 0,
            defaultFormantShift: 0,
            modelType: "pyTorchRVCv2",
            modelTypeOnnx: "",
            embChannels: 256,
            f0: true,
            samplingRate: 48000,
            deprecated: false,
        },
    ],
};

const MIME = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
    ".wav": "audio/wav",
};

const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
    if (url.pathname === "/version") {
        res.writeHead(200).end("2.0.0-mock");
        return;
    }
    if (url.pathname === "/edition") {
        res.writeHead(200).end("cuda-mock");
        return;
    }
    if (url.pathname === "/info") {
        res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(info));
        return;
    }
    if (url.pathname === "/update_settings" && req.method === "POST") {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => {
            const body = Buffer.concat(chunks).toString();
            const contentType = req.headers["content-type"] || "";
            if (contentType.includes("multipart/form-data")) {
                // extract key/val fields from the multipart body
                const boundary = contentType.split("boundary=")[1];
                const fields = {};
                for (const part of body.split(`--${boundary}`)) {
                    const m = part.match(/name="([^"]+)"\r?\n\r?\n/);
                    if (m) {
                        fields[m[1]] = part.slice(m.index + m[0].length).replace(/\r?\n+$/, "");
                    }
                }
                if (fields.key !== undefined) {
                    let val = fields.val;
                    try {
                        val = JSON.parse(val);
                    } catch {}
                    info[fields.key] = val;
                }
            } else {
                const params = new URLSearchParams(body);
                if (params.has("key")) {
                    let val = params.get("val");
                    try {
                        val = JSON.parse(val);
                    } catch {}
                    info[params.get("key")] = val;
                }
            }
            res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(info));
        });
        return;
    }
    if (url.pathname.startsWith("/tmp/")) {
        res.writeHead(404).end("not found (mock)");
        return;
    }
    if (url.pathname.startsWith("/models/")) {
        // serve mock model assets from /tmp/vcmock when present
        const mockFile = path.join("/tmp/vcmock", url.pathname);
        if (fs.existsSync(mockFile)) {
            res.writeHead(200, { "Content-Type": MIME[path.extname(mockFile)] || "application/octet-stream" });
            res.end(fs.readFileSync(mockFile));
        } else {
            res.writeHead(404).end("not found");
        }
        return;
    }
    // static files
    let file = path.join(DIST, decodeURIComponent(url.pathname));
    if (url.pathname === "/" || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        file = path.join(DIST, "index.html");
    }
    try {
        const data = fs.readFileSync(file);
        res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" });
        res.end(data);
    } catch {
        res.writeHead(404).end("not found");
    }
});

server.listen(PORT, () => {
    console.log(`[mock] serving ${DIST} at http://127.0.0.1:${PORT}`);
});
