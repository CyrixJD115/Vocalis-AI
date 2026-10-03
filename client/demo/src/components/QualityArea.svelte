<script lang="ts">
    import SliderRow from "./ui/SliderRow.svelte";
    import SelectRow, { type SelectOption } from "./ui/SelectRow.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { appState } from "../lib/state/appState.svelte";

    let { detectors = [] }: { detectors?: string[] } = $props();

    let serverSetting = $derived(serverState.serverSetting);
    let isConverting = $derived(guiState.isConverting);
    let enableServerAudio = $derived(serverSetting.enableServerAudio == 1);
    let clientSetting = $derived(vcClientState.setting.voiceChangerClientSetting);

    let f0Options: SelectOption[] = $derived(
        detectors.map((x) => {
            const recommended = ["crepe_full_onnx", "crepe_tiny_onnx", "rmvpe_onnx", "fcpe_onnx"];
            const disabled = appState.edition.indexOf("DirectML") >= 0 && !recommended.includes(x);
            return { value: x, label: disabled ? `${x}(N/A)` : x, disabled };
        }),
    );

    const onF0Changed = async (v: string) => {
        guiState.showWaitingDialog = true;
        try {
            await serverState.updateServerSettings({ ...serverSetting, f0Detector: v as any });
        } finally {
            guiState.showWaitingDialog = false;
        }
    };
</script>

<div class="flex flex-col gap-0.5">
    <!-- NOISE -->
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">NOISE</div>
        <div class="flex flex-1 items-center gap-4 text-sm">
            <label class="flex items-center gap-1.5" class:opacity-40={enableServerAudio}>
                <input
                    type="checkbox"
                    class="vc-check"
                    disabled={enableServerAudio}
                    checked={clientSetting.echoCancel}
                    onchange={(e) => vcClientState.setVoiceChangerClientSetting({ ...clientSetting, echoCancel: e.currentTarget.checked })}
                />
                Echo
            </label>
            <label class="flex items-center gap-1.5" class:opacity-40={enableServerAudio}>
                <input
                    type="checkbox"
                    class="vc-check"
                    disabled={enableServerAudio}
                    checked={clientSetting.noiseSuppression}
                    onchange={(e) => vcClientState.setVoiceChangerClientSetting({ ...clientSetting, noiseSuppression: e.currentTarget.checked })}
                />
                Sup1
            </label>
            <label class="flex items-center gap-1.5" class:opacity-40={enableServerAudio}>
                <input
                    type="checkbox"
                    class="vc-check"
                    disabled={enableServerAudio}
                    checked={clientSetting.noiseSuppression2}
                    onchange={(e) => vcClientState.setVoiceChangerClientSetting({ ...clientSetting, noiseSuppression2: e.currentTarget.checked })}
                />
                Sup2
            </label>
        </div>
    </div>
    <SelectRow
        label="F0 Det."
        hint="F0 Detector. A pitch extraction algorithm."
        value={String(serverSetting.f0Detector)}
        options={f0Options}
        disabled={isConverting}
        onValueChange={(v) => onF0Changed(v)}
    />
    <SliderRow
        label="In. Sens."
        hint="Input sensitivity. The input volume required to activate the voice changer."
        min={-90}
        max={-60}
        step={1}
        suffix="dB"
        value={serverSetting.silentThreshold}
        onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, silentThreshold: v })}
    />
</div>
