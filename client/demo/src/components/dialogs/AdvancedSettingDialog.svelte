<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import SliderRow from "../ui/SliderRow.svelte";
    import SelectRow, { type SelectOption } from "../ui/SelectRow.svelte";
    import { tooltip } from "../../lib/tooltip";
    import { serverState } from "../../lib/state/serverState.svelte";
    import { vcClientState } from "../../lib/state/vcClient.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";

    let serverSetting = $derived(serverState.serverSetting);
    let clientSetting = $derived(vcClientState.setting.voiceChangerClientSetting);
    let workletNodeSetting = $derived(vcClientState.setting.workletNodeSetting);
    let isConverting = $derived(guiState.isConverting);

    const boolOptions: SelectOption[] = [
        { value: "0", label: "off" },
        { value: "1", label: "on" },
    ];

    const updateServerWithWaiting = async (patch: Record<string, unknown>, clearChanged = false) => {
        guiState.showWaitingDialog = true;
        try {
            await serverState.updateServerSettings({ ...serverSetting, ...patch });
            if (clearChanged) {
                guiState.setVoiceChangerSettingsChanged(false);
            }
        } finally {
            guiState.showWaitingDialog = false;
        }
    };
</script>

<Dialog title="Advanced Setting" open={guiState.showAdvancedSettingDialog} width="max-w-2xl" onClose={() => (guiState.showAdvancedSettingDialog = false)}>
    <div class="flex flex-col gap-0.5">
        <SelectRow
            label="Protocol"
            hint="Communication protocol between the user interface and server. 'sio' is the recommended."
            value={workletNodeSetting.protocol}
            options={[
                { value: "sio", label: "sio" },
                { value: "rest", label: "rest" },
            ]}
            onValueChange={(v) => vcClientState.setWorkletNodeSetting({ ...workletNodeSetting, protocol: v as "sio" | "rest" })}
        />
        <SliderRow
            label="Crossfade"
            hint="Crossfade duration between converted audio chunks. Longer values make the transition between chunks smoother."
            min={0.05}
            max={0.2}
            step={0.01}
            suffix="s"
            value={serverSetting.crossFadeOverlapSize}
            disabled={isConverting}
            onValueChange={(v) => {
                serverState.updateServerSettings({ ...serverSetting, crossFadeOverlapSize: v });
                guiState.setVoiceChangerSettingsChanged(true);
            }}
        />
        <SelectRow
            label="SilenceFront"
            hint="An optimization option that removes 'Extra' part during pitch extraction. Recommended to keep it 'on'."
            value={String(serverSetting.silenceFront)}
            options={boolOptions}
            disabled={isConverting}
            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, silenceFront: Number(v) })}
        />
        <SelectRow
            label="Force FP32"
            hint="A debugging option that forces inference with full precision instead of half precision. Has no effect if GPU does not support FP16 (indicated in the command line logs). Set to 'off' only if you experience issues in FP16 mode."
            value={String(serverSetting.forceFp32)}
            options={boolOptions}
            disabled={isConverting}
            onValueChange={(v) => updateServerWithWaiting({ forceFp32: Number(v) }, true)}
        />
        <SelectRow
            label="Disable JIT"
            hint="A debugging option that disables Just-in-Time (JIT) compilation for PyTorch models. Disabling this option will reduce model loading time, but may decrease performance. Has no effect on DirectML devices."
            value={String(serverSetting.disableJit)}
            options={boolOptions}
            disabled={isConverting}
            onValueChange={(v) => updateServerWithWaiting({ disableJit: Number(v) }, true)}
        />
        <div class="flex items-center gap-3 py-1">
            <div class="control-label w-28 shrink-0 text-right">
                <span
                    use:tooltip={"Automatically converts models into ONNX format. Note that model conversion is performed once and may take 1-2 minutes. Recommended for DirectML version and inference on CPU."}
                    class="cursor-help underline decoration-dotted decoration-slate-500 underline-offset-4"
                >
                    ONNX
                </span>
            </div>
            <label class="flex flex-1 items-center gap-2 text-sm">
                <input
                    type="checkbox"
                    class="vc-check"
                    disabled={isConverting}
                    checked={Boolean(serverSetting.useONNX)}
                    onchange={(e) => updateServerWithWaiting({ useONNX: Number(e.currentTarget.checked) })}
                />
                <span class="text-slate-400">convert models to ONNX automatically (1-2 min per model)</span>
            </label>
        </div>
        <SliderRow
            label="Protect"
            hint="Voiceless consonants protection. Has no effect when set to 0.5 or when 'Index' is inactive."
            min={0}
            max={0.5}
            step={0.01}
            value={serverSetting.protect || 0}
            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, protect: v })}
        />
        <SelectRow
            label="Skip PT conf."
            value={clientSetting.passThroughConfirmationSkip ? "1" : "0"}
            options={[
                { value: "0", label: "No" },
                { value: "1", label: "Yes" },
            ]}
            onValueChange={(v) => vcClientState.setVoiceChangerClientSetting({ ...clientSetting, passThroughConfirmationSkip: v == "1" })}
        />
    </div>
</Dialog>
