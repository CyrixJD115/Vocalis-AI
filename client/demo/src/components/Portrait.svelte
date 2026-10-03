<script lang="ts">
    import { serverState } from "../lib/state/serverState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { basename } from "../lib/utils";
    import { registerMessages, getMessage } from "../lib/i18n";
    import { openExternal } from "../lib/const";

    registerMessages("Portrait", {
        terms_of_use: { ja: "利用規約", en: "terms of use" },
    });

    const MAX_DATA_POINTS = 50;
    const SPARK_W = 160;
    const SPARK_H = 40;

    let perfHistory = $state<number[]>([]);

    let selected = $derived(serverState.serverSetting.modelSlots?.[serverState.serverSetting.modelSlotIndex]);
    let vcType = $derived(selected ? (serverState.serverSetting.useONNX ? (selected as any).modelTypeOnnx : (selected as any).modelType) : "");
    let volumeDb = $derived(Math.max(Math.round(20 * Math.log10(Math.max(vcClientState.performance.vol, 1e-10))), -90));
    let chunkTime = $derived((serverState.serverSetting.serverReadChunkSize * 128 * 1000) / 48000);
    let totalTime = $derived(Math.ceil(chunkTime + vcClientState.performance.responseTime + serverState.serverSetting.crossFadeOverlapSize * 1000));
    let mainprocessTime = $derived(vcClientState.performance.mainprocessTime);
    let perfColor = $derived(mainprocessTime > chunkTime ? "#ff4a4a" : mainprocessTime * 1.2 > chunkTime ? "#ffff00" : "#00ff00");

    // rolling perf history buffer, newest last
    $effect(() => {
        const t = vcClientState.performance.mainprocessTime;
        if (t > 0) {
            perfHistory = [...perfHistory.slice(-(MAX_DATA_POINTS - 1)), t];
        }
    });

    let sparkPoints = $derived.by(() => {
        if (perfHistory.length < 2) {
            return "";
        }
        const max = Math.max(...perfHistory, 1);
        return perfHistory
            .map((v, i) => {
                const x = (i / (MAX_DATA_POINTS - 1)) * SPARK_W;
                const y = SPARK_H - (v / max) * (SPARK_H - 4) - 2;
                return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
    });
</script>

{#if selected}
    <div class="relative overflow-hidden rounded-xl border border-white/10">
        <img
            src={
                selected.iconFile.length > 0
                    ? serverState.serverSetting.voiceChangerParams.model_dir + "/" + selected.slotIndex + "/" + basename(selected.iconFile)
                    : "./assets/icons/human.png"
            }
            alt={selected.name}
            class="aspect-square w-full object-cover opacity-80"
        />
        <div class="absolute inset-x-0 top-0 bg-gradient-to-b from-black/80 to-transparent p-3">
            <div class="flex flex-col gap-0.5 font-mono text-[11px] leading-tight text-slate-200 [text-shadow:0_1px_2px_rgba(0,0,0,0.8)]">
                <span class="text-accent-300">{vcType}</span>
                <span>vol(in): {volumeDb} dB</span>
                <span>ping: {vcClientState.performance.responseTime} ms</span>
                <span>total: {totalTime} ms</span>
                <span>
                    perf:
                    <span style={`color: ${perfColor}`}>{mainprocessTime}</span>
                    of {chunkTime.toFixed(1)} ms
                </span>
            </div>
        </div>
        <div class="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/80 to-transparent p-3">
            <svg viewBox="0 0 {SPARK_W} {SPARK_H}" class="h-10 w-40" preserveAspectRatio="none" aria-hidden="true">
                {#if sparkPoints}
                    <polyline points={sparkPoints} fill="none" stroke="rgb(75,192,192)" stroke-width="1.5" />
                {/if}
            </svg>
            {#if selected.termsOfUseUrl}
                <button
                    class="text-[10px] text-slate-300 underline decoration-dotted underline-offset-2 transition-colors hover:text-white"
                    onclick={() => openExternal(selected.termsOfUseUrl)}
                >
                    [{getMessage("Portrait", "terms_of_use")}]
                </button>
            {/if}
        </div>
    </div>
{:else}
    <div class="flex aspect-square w-full items-center justify-center rounded-xl border border-dashed border-white/15 bg-white/[0.02]">
        <span class="text-sm text-slate-600">no model selected</span>
    </div>
{/if}
