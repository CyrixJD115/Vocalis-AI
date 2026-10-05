<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { serverState } from "../../lib/state/serverState.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { toast } from "../../lib/toast.svelte";
    import { openExternal } from "../../lib/const";

    type VirtualAudioStatus = {
        status: string;
        platform: string; // "Windows" | "Darwin" | "Linux"
        capability: string; // "manage" | "install" | "guide"
        virtualDeviceDetected: boolean;
        detectedDevices: string[];
        sinkName: string;
        sinkLoaded?: boolean;
        brewAvailable?: boolean;
        guide: string;
        message?: string;
        created?: boolean;
        removed?: boolean;
        deviceCacheRefreshed?: boolean;
    };

    type DiagCheck = {
        id: string;
        severity: "ok" | "info" | "warn" | "error";
        label: string;
        detail?: string;
        fix?: string;
    };

    type DiagnoseResult = {
        status: string;
        platform?: string;
        virtualDeviceDetected?: boolean;
        checks?: DiagCheck[];
        discordTips?: string[];
        recommendation?: {
            inputDeviceIndex: number;
            outputDeviceIndex: number;
            hostAPI: string;
            sampleRate: number;
            inputDeviceName: string;
            outputDeviceName: string;
        } | null;
        currentSelection?: {
            inputDeviceIndex: number;
            outputDeviceIndex: number;
            sampleRate: number;
        };
        message?: string;
    };

    let status: VirtualAudioStatus | null = $state(null);
    let diagnosis: DiagnoseResult | null = $state(null);
    let diagnosing = $state(false);
    let applying = $state(false);
    let loading = $state(false);
    let error = $state("");

    const platformLabel = (p: string) => (p == "Darwin" ? "macOS" : p == "Windows" ? "Windows" : p == "Linux" ? "Linux" : p);

    const fetchStatus = async () => {
        loading = true;
        error = "";
        try {
            const res = await fetch("/virtual_audio/status");
            status = (await res.json()) as VirtualAudioStatus;
        } catch (e) {
            error = String(e);
        } finally {
            loading = false;
        }
    };

    const postAction = async (path: string) => {
        loading = true;
        error = "";
        try {
            const body = new FormData();
            const res = await fetch(path, { method: "POST", body });
            status = (await res.json()) as VirtualAudioStatus;
            // device lists may have changed on the server side
            await serverState.reloadServerInfo();
            if (status.status == "OK" && status.message) {
                toast.info(status.message);
            } else if (status.status != "OK" && status.message) {
                toast.error(status.message);
            }
        } catch (e) {
            error = String(e);
        } finally {
            loading = false;
        }
    };

    const runDiagnosis = async () => {
        diagnosing = true;
        error = "";
        try {
            const res = await fetch("/virtual_audio/diagnose");
            diagnosis = (await res.json()) as DiagnoseResult;
        } catch (e) {
            error = String(e);
        } finally {
            diagnosing = false;
        }
    };

    const applyRecommendations = async () => {
        applying = true;
        error = "";
        try {
            const body = new FormData();
            const res = await fetch("/virtual_audio/apply_recommendations", { method: "POST", body });
            const data = (await res.json()) as DiagnoseResult;
            if (data.status == "OK" && data.message) {
                toast.info(data.message);
            } else if (data.message) {
                toast.error(data.message);
            }
            await serverState.reloadServerInfo();
            await runDiagnosis();
        } catch (e) {
            error = String(e);
        } finally {
            applying = false;
        }
    };

    const severityClass = (s: string) =>
        s == "error"
            ? "text-red-400 border-red-500/30 bg-red-500/5"
            : s == "warn"
              ? "text-amber-300 border-amber-500/30 bg-amber-500/5"
              : s == "ok"
                ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/5"
                : "text-slate-300 border-white/10 bg-black/20";

    $effect(() => {
        if (guiState.showVirtualAudioDialog) {
            fetchStatus();
            runDiagnosis();
        }
    });

    const close = () => (guiState.showVirtualAudioDialog = false);
</script>

<Dialog title="Virtual Audio Routing" open={guiState.showVirtualAudioDialog} width="max-w-2xl" onClose={close}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="leading-relaxed text-slate-300">
            Route your converted voice into other apps:
            <span class="text-slate-100">mic &rarr; Vocalis (model + enhancer) &rarr; virtual audio device &rarr; Discord / OBS / VTube Studio</span>.
            Those apps only hear the converted voice, while you keep listening through the <span class="text-slate-100">Monitor</span> device.
        </p>

        <ol class="ml-4 list-decimal space-y-1 text-slate-400">
            <li>Create (or install) a virtual audio device below.</li>
            <li>Set AUDIO mode to <span class="text-slate-100">server</span> and pick the virtual device as <span class="text-slate-100">Output</span>.</li>
            <li>Pick your headphones as <span class="text-slate-100">Monitor</span> so you hear yourself.</li>
            <li>In Discord/OBS/VTube Studio, select the virtual device as the microphone/input.</li>
        </ol>

        {#if loading && !status}
            <p class="text-slate-500">checking this system...</p>
        {/if}
        {#if error}
            <p class="text-red-400">{error}</p>
        {/if}

        {#if status}
            <div class="rounded-lg border border-white/10 bg-black/20 p-3">
                <div class="mb-2 flex items-center gap-2">
                    <span class="rounded bg-white/10 px-2 py-0.5 text-xs text-slate-200">{platformLabel(status.platform)}</span>
                    {#if status.virtualDeviceDetected}
                        <span class="rounded bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-300">virtual device detected</span>
                    {:else}
                        <span class="rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300">no virtual device yet</span>
                    {/if}
                </div>
                {#if status.detectedDevices.length > 0}
                    <p class="text-xs text-slate-400">
                        detected: {status.detectedDevices.join(", ")}
                    </p>
                {/if}

                {#if status.capability == "manage"}
                    <div class="mt-2 flex flex-wrap gap-2">
                        <button class="btn" disabled={loading} onclick={() => postAction("/virtual_audio/create")}>
                            {status.sinkLoaded ? "re-check" : "create virtual device"}
                        </button>
                        {#if status.sinkLoaded}
                            <button class="btn" disabled={loading} onclick={() => postAction("/virtual_audio/remove")}>remove</button>
                        {/if}
                    </div>
                    {#if status.sinkLoaded}
                        <p class="mt-2 text-xs text-emerald-300">"Vocalis AI Output" is live. Choose it as Output in server audio mode.</p>
                    {/if}
                {:else if status.capability == "install"}
                    <div class="mt-2 flex flex-wrap gap-2">
                        <button class="btn" disabled={loading} onclick={() => postAction("/virtual_audio/create")}>install BlackHole (Homebrew)</button>
                    </div>
                    <p class="mt-2 text-xs text-slate-500">Runs "brew install --cask blackhole-2ch". May ask for your password.</p>
                {:else}
                    <p class="mt-2 text-xs text-slate-500">Setup on this OS is manual (one-time driver install) - follow the steps below.</p>
                {/if}

                {#if status.deviceCacheRefreshed === false}
                    <p class="mt-2 text-xs text-amber-400">
                        Server audio is running, so the device list will only refresh after audio is stopped. Stop and restart audio to see the new device.
                    </p>
                {/if}
            </div>
        {/if}

        {#if diagnosis && (diagnosis.checks?.length || diagnosis.recommendation)}
            <div class="rounded-lg border border-white/10 bg-black/20 p-3">
                <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">diagnosis</div>
                    <div class="flex gap-2">
                        <button class="btn" onclick={runDiagnosis} disabled={diagnosing}>{diagnosing ? "checking..." : "re-run diagnosis"}</button>
                        {#if diagnosis.recommendation}
                            <button class="btn btn-accent" onclick={applyRecommendations} disabled={applying || loading}>
                                {applying ? "applying..." : "apply recommended routing"}
                            </button>
                        {/if}
                    </div>
                </div>

                {#if diagnosis.recommendation}
                    <p class="mb-2 text-xs text-slate-400">
                        Recommended: <span class="text-slate-100">{diagnosis.recommendation.inputDeviceName}</span> &rarr;
                        <span class="text-slate-100">{diagnosis.recommendation.outputDeviceName}</span>
                        [{diagnosis.recommendation.hostAPI}] @ {diagnosis.recommendation.sampleRate} Hz.
                        "Apply" selects it for you (monitor device is not touched); then press <span class="text-slate-100">start</span>.
                    </p>
                {/if}

                <div class="flex flex-col gap-1.5">
                    {#each diagnosis.checks || [] as check (check.id)}
                        <div class={`rounded border px-2.5 py-1.5 text-xs leading-relaxed ${severityClass(check.severity)}`}>
                            <div>{check.label}</div>
                            {#if check.detail}
                                <div class="text-slate-500">{check.detail}</div>
                            {/if}
                            {#if check.fix}
                                <div class="text-slate-400">Fix: {check.fix}</div>
                            {/if}
                        </div>
                    {/each}
                </div>

                {#if diagnosis.discordTips?.length}
                    <details class="mt-2 text-xs text-slate-400">
                        <summary class="cursor-pointer select-none text-slate-300">Discord tips (error 3002, silence, noise suppression)</summary>
                        <ul class="ml-4 mt-1 list-disc space-y-1">
                            {#each diagnosis.discordTips as tip}
                                <li>{tip}</li>
                            {/each}
                        </ul>
                    </details>
                {/if}
            </div>
        {/if}

        {#if status?.guide}
            <div>
                <div class="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    setup guide ({platformLabel(status?.platform || "")})
                </div>
                <pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-black/30 p-3 text-xs leading-relaxed text-slate-300">{status.guide}</pre>
            </div>
        {/if}

        <div class="flex flex-wrap gap-3 text-xs">
            <button class="btn" onclick={() => openExternal("https://vb-audio.com/Cable/")}>VB-Cable (Windows)</button>
            <button class="btn" onclick={() => openExternal("https://existential.audio/blackhole/")}>BlackHole (macOS)</button>
            <button class="btn" onclick={fetchStatus} disabled={loading}>refresh status</button>
        </div>

        <p class="text-xs leading-relaxed text-slate-500">
            Tip: on every OS, also make sure the <span class="text-slate-300">monitor</span> output is NOT set to the virtual device, otherwise other
            apps would hear your monitoring too. Windows names differ per app ("CABLE Output" is the mic side, "CABLE Input" is the speaker side).
        </p>
    </div>
</Dialog>
