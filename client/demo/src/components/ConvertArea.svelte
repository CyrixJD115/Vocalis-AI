<script lang="ts">
    import SliderRow from "./ui/SliderRow.svelte";
    import Icon from "../lib/icons/Icon.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { appState } from "../lib/state/appState.svelte";
    import { tooltip } from "../lib/tooltip";

    let serverSetting = $derived(serverState.serverSetting);
    let isConverting = $derived(guiState.isConverting);
    let workletNodeSetting = $derived(vcClientState.setting.workletNodeSetting);

    let chunkMs = $derived(((serverSetting.serverReadChunkSize * 128 * 1000) / 48000).toFixed(1));

    const onChunkChanged = async (val: number) => {
        vcClientState.setWorkletNodeSetting({ ...workletNodeSetting, inputChunkNum: val });
        vcClientState.trancateBuffer();
        await serverState.updateServerSettings({ ...serverSetting, serverReadChunkSize: val });
        guiState.setVoiceChangerSettingsChanged(true);
    };

    let gpuOptions = $derived(
        (serverSetting.gpus || []).map((g) => ({
            value: String(g.id),
            label: `${g.name}${g.memory ? `(${(g.memory / 1024 / 1024 / 1024).toFixed(0)}GB)` : ""}`,
        })),
    );

    let gpuSelectEl: HTMLSelectElement | null = $state(null);
    // Controlled select: re-apply after gpus/value changes.
    $effect(() => {
        void gpuOptions;
        void serverSetting.gpu;
        if (gpuSelectEl) {
            gpuSelectEl.value = String(serverSetting.gpu);
        }
    });

    const onGpuChanged = async (v: string) => {
        guiState.showWaitingDialog = true;
        try {
            await serverState.updateServerSettings({ ...serverSetting, gpu: Number(v) });
            guiState.setVoiceChangerSettingsChanged(false);
        } finally {
            guiState.showWaitingDialog = false;
        }
    };
</script>

<div class="flex flex-col gap-0.5">
    <SliderRow
        label="CHUNK"
        hint="Chunk size is an audio buffer. Controls the delay and GPU usage. More chunk - more delay, less GPU usage. Less chunk - vice versa."
        min={1}
        max={1024}
        step={1}
        value={serverSetting.serverReadChunkSize}
        disabled={isConverting}
        onValueChange={(v) => onChunkChanged(v)}
    >
        <span class="w-16 whitespace-nowrap text-left tabular-nums">{chunkMs} ms</span>
    </SliderRow>
    <SliderRow
        label="EXTRA"
        hint="Extra is an extra audio history that will be used for voice conversion. Does not affect the delay. More extra - better voice quality, more GPU usage. Less extra - vice versa."
        min={0.1}
        max={5}
        step={0.1}
        suffix="s"
        value={serverSetting.extraConvertSize}
        disabled={isConverting}
        onValueChange={(v) => {
            serverState.updateServerSettings({ ...serverSetting, extraConvertSize: v });
            guiState.setVoiceChangerSettingsChanged(true);
        }}
    />
    <div class="flex items-center gap-3 py-1">
        <div class="control-label flex w-28 shrink-0 items-center justify-end gap-1.5">
            {#if appState.edition === "DirectML" && serverSetting.gpu !== -1 && guiState.voiceChangerSettingsChanged}
                <span use:tooltip={"Change to CPU then back to GPU."} class="cursor-help text-amber-400">
                    <Icon name="warning" size={13} />
                </span>
            {/if}
            <span>GPU</span>
        </div>
        <select bind:this={gpuSelectEl} class="field min-w-0 flex-1" disabled={isConverting} onchange={(e) => onGpuChanged(e.currentTarget.value)}>
            {#each gpuOptions as g (g.value)}
                <option value={g.value}>{g.label}</option>
            {/each}
        </select>
    </div>
</div>
