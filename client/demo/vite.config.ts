import { defineConfig, type Plugin } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import fs from "node:fs/promises";
import { build as esbuild } from "esbuild";

const VC_LIB_SRC = path.resolve(__dirname, "../lib/src");

// The shared client lib embeds its audio-worklet processor as a raw webpack
// import (`raw-loader!../worklet/dist/index.js`). Under Vite we bundle the
// worklet TypeScript directly with esbuild and serve it as a virtual module.
function vcWorkletPlugin(): Plugin {
    const VIRTUAL_ID = "virtual:vc-worklet";
    const RESOLVED_ID = "\0" + VIRTUAL_ID;
    let cached: string | null = null;
    return {
        name: "vc-worklet-bundler",
        enforce: "pre",
        resolveId(id) {
            if (id === VIRTUAL_ID) {
                return RESOLVED_ID;
            }
            return null;
        },
        async load(id) {
            if (id === RESOLVED_ID) {
                if (!cached) {
                    const result = await esbuild({
                        entryPoints: [path.resolve(__dirname, "../lib/worklet/src/voice-changer-worklet-processor.ts")],
                        bundle: true,
                        format: "iife",
                        platform: "browser",
                        minify: true,
                        write: false,
                        logLevel: "silent",
                    });
                    cached = `export default ${JSON.stringify(result.outputFiles[0].text)};`;
                }
                return cached;
            }
            // Rewrite the webpack-specific raw import in the lib source. This
            // must happen in `load` (not `transform`) so the dev-mode dependency
            // scanner never sees the unresolvable specifier.
            if (id.startsWith(VC_LIB_SRC) && id.endsWith("VoiceChangerClient.ts")) {
                const code = await fs.readFile(id, "utf-8");
                const replaced = code.replace(
                    /import\s+workerjs\s+from\s+["']raw-loader!\.\.\/worklet\/dist\/index\.js["'];?/,
                    `import workerjs from "${VIRTUAL_ID}";`,
                );
                if (replaced !== code) {
                    return replaced;
                }
            }
            return null;
        },
    };
}

// REST endpoints exposed by the python server (see server/sio/MMVC_SocketIOApp.py
// and client/lib/src/client/ServerRestClient.ts). Socket.IO traffic goes through
// the default /socket.io path; the VC websocket namespace is /test.
const API_PATHS = [
    "/info",
    "/performance",
    "/update_settings",
    "/upload_file",
    "/concat_uploaded_file",
    "/load_model",
    "/upload_model_assets",
    "/model_type",
    "/merge_model",
    "/update_model_default",
    "/update_model_info",
    "/onnx",
    "/version",
    "/edition",
    "/tmp",
    "/socket.io",
];

const proxyTarget = process.env.VC_SERVER_URL || "http://127.0.0.1:18888";

export default defineConfig({
    plugins: [tailwindcss(), svelte(), vcWorkletPlugin()],
    resolve: {
        alias: {
            "@vc-lib": VC_LIB_SRC,
        },
    },
    server: {
        port: 5173,
        proxy: Object.fromEntries(
            API_PATHS.map((p) => [
                p,
                {
                    target: proxyTarget,
                    changeOrigin: true,
                    // self-signed HTTPS certs when the backend runs with --https
                    secure: false,
                    // socket.io websocket upgrade
                    ws: true,
                },
            ]),
        ),
    },
    build: {
        outDir: "dist",
        emptyOutDir: true,
        chunkSizeWarningLimit: 2000,
    },
});
