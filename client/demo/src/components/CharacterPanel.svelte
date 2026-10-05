<script lang="ts">
    import Portrait from "./Portrait.svelte";
    import SliderRow from "./ui/SliderRow.svelte";
    import SelectRow, { type SelectOption } from "./ui/SelectRow.svelte";
    import Icon from "../lib/icons/Icon.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { toast } from "../lib/toast.svelte";
    import { registerMessages, getMessage } from "../lib/i18n";

    registerMessages("CharacterArea", {
        save_default: { ja: "設定保存", en: "save setting" },
    });

    let serverSetting = $derived(serverState.serverSetting);
    let selected = $derived(serverSetting.modelSlots?.[serverSetting.modelSlotIndex]);

    const onStartClicked = async () => {
        if (serverSetting.modelSlotIndex === -1 || !selected) {
            toast.warn("Select a voice model first.");
            return;
        }
        if (serverSetting.enableServerAudio != 1) {
            const clientSetting = vcClientState.setting.voiceChangerClientSetting;
            if (!clientSetting.audioInput || clientSetting.audioInput == "none") {
                toast.warn("Select an audio input device.");
                return;
            }
            if (guiState.audioOutputForGUI == "none") {
                toast.warn("Select an audio output device.");
                return;
            }
            guiState.isConverting = true;
            try {
                await vcClientState.start();
            } catch (e) {
                guiState.isConverting = false;
                console.error(e);
                toast.error("Failed to start voice conversion.");
            }
        } else {
            if (serverSetting.serverInputDeviceId == -1) {
                toast.warn("Select an audio input device.");
                return;
            }
            if (serverSetting.serverOutputDeviceId == -1) {
                toast.warn("Select an audio output device.");
                return;
            }
            guiState.isConverting = true;
            try {
                // Establish the socket connection so server-mode errors and
                // volume stats are received, then tell the server to open its
                // own audio stream (mic -> model -> output device).
                await vcClientState.ensureClient();
                await serverState.updateServerSettings({ ...serverSetting, serverAudioStated: 1 });
            } catch (e) {
                guiState.isConverting = false;
                console.error(e);
                toast.error("Failed to start voice conversion.");
            }
        }
    };

    const onStopClicked = async () => {
        guiState.isConverting = false;
        if (serverSetting.enableServerAudio != 1) {
            await vcClientState.stop();
        } else {
            await serverState.updateServerSettings({ ...serverSetting, serverAudioStated: 0 });
        }
    };

    const onPassThroughClicked = async () => {
        if (!serverSetting.passThrough) {
            if (vcClientState.setting.voiceChangerClientSetting.passThroughConfirmationSkip) {
                await serverState.updateServerSettings({ ...serverSetting, passThrough: true });
                guiState.showPassThroughDialog = false;
            } else {
                guiState.showPassThroughDialog = true;
            }
        } else {
            await serverState.updateServerSettings({ ...serverSetting, passThrough: false });
        }
    };

    const gainSource = (clientVal: number, serverVal: number) => (serverSetting.enableServerAudio != 1 ? clientVal : serverVal);

    const onGainChange = async (kind: "in" | "out" | "mon", val: number) => {
        if (serverSetting.enableServerAudio != 1) {
            const c = vcClientState.setting.voiceChangerClientSetting;
            await vcClientState.setVoiceChangerClientSetting({
                ...c,
                inputGain: kind == "in" ? val : c.inputGain,
                outputGain: kind == "out" ? val : c.outputGain,
                monitorGain: kind == "mon" ? val : c.monitorGain,
            });
        } else {
            await serverState.updateServerSettings({
                ...serverSetting,
                serverInputAudioGain: kind == "in" ? val : serverSetting.serverInputAudioGain,
                serverOutputAudioGain: kind == "out" ? val : serverSetting.serverOutputAudioGain,
                serverMonitorAudioGain: kind == "mon" ? val : serverSetting.serverMonitorAudioGain,
            });
        }
    };

    let speakerOptions: SelectOption[] = $derived(
        selected
            ? Object.keys(selected.speakers || {}).map((key) => ({
                  value: key,
                  label: `${selected.speakers[Number(key)]}[${key}]`,
              }))
            : [],
    );
</script>

<section class="card flex flex-col gap-4 p-4">
    <div class="card-title">Voice</div>

    <div class="flex flex-col gap-4 lg:flex-row">
        <div class="w-full max-w-64 shrink-0 lg:w-56">
            <Portrait />
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-3">
            {#if selected}
                <div class="flex items-center justify-between gap-2">
                    <div class="min-w-0">
                        <div class="control-label">Name</div>
                        <div class="truncate text-lg font-medium text-slate-100" title={selected.name}>{selected.name}</div>
                    </div>
                    <button class="btn btn-accent" onclick={() => serverState.updateModelDefault()} title="Save current settings as the model defaults">
                        <Icon name="check" size={14} />
                        {getMessage("CharacterArea", "save_default")}
                    </button>
                </div>
            {/if}

            <div class="grid grid-cols-3 gap-2">
                <button class="btn btn-start h-10 text-sm font-semibold" class:btn-start-active={guiState.isConverting} onclick={onStartClicked}>
                    start
                </button>
                <button class="btn btn-stop h-10 text-sm font-semibold" class:btn-stop-active={!guiState.isConverting} onclick={onStopClicked}>
                    stop
                </button>
                <button
                    class="btn h-10 text-sm font-semibold"
                    class:btn-stop-active={serverSetting.passThrough}
                    class:vc-blink={serverSetting.passThrough}
                    onclick={onPassThroughClicked}
                >
                    passthru
                </button>
            </div>

            <div class="rounded-xl border border-white/[0.07] bg-black/20 p-2">
                <SliderRow
                    label="in"
                    labelWidth="w-12"
                    hint="Input volume."
                    min={0.1}
                    max={2.5}
                    step={0.01}
                    showNumber={false}
                    value={gainSource(vcClientState.setting.voiceChangerClientSetting.inputGain, serverSetting.serverInputAudioGain)}
                    onValueChange={(v) => onGainChange("in", v)}
                >
                    <span class="w-12 text-left tabular-nums">{Math.round(gainSource(vcClientState.setting.voiceChangerClientSetting.inputGain, serverSetting.serverInputAudioGain) * 100)}%</span>
                </SliderRow>
                <SliderRow
                    label="out"
                    labelWidth="w-12"
                    hint="Output volume."
                    min={0.1}
                    max={4.0}
                    step={0.01}
                    showNumber={false}
                    value={gainSource(vcClientState.setting.voiceChangerClientSetting.outputGain, serverSetting.serverOutputAudioGain)}
                    onValueChange={(v) => onGainChange("out", v)}
                >
                    <span class="w-12 text-left tabular-nums">{Math.round(gainSource(vcClientState.setting.voiceChangerClientSetting.outputGain, serverSetting.serverOutputAudioGain) * 100)}%</span>
                </SliderRow>
                <SliderRow
                    label="mon"
                    labelWidth="w-12"
                    hint="Monitor volume."
                    min={0.1}
                    max={4.0}
                    step={0.01}
                    showNumber={false}
                    value={gainSource(vcClientState.setting.voiceChangerClientSetting.monitorGain, serverSetting.serverMonitorAudioGain)}
                    onValueChange={(v) => onGainChange("mon", v)}
                >
                    <span class="w-12 text-left tabular-nums">{Math.round(gainSource(vcClientState.setting.voiceChangerClientSetting.monitorGain, serverSetting.serverMonitorAudioGain) * 100)}%</span>
                </SliderRow>
            </div>

            {#if selected}
                <div class="flex flex-col gap-1 rounded-xl border border-white/[0.07] bg-black/20 p-2">
                    <SliderRow
                        label="PITCH"
                        hint="Pitch shift alters the tone of voice. If your voice is low-pitched (f.e., male voice) and model is high-pitched (f.e., a female voice model), increase this setting (i.e., set to 12). Otherwise, decrease this setting (i.e., set to -12)."
                        min={-50}
                        max={50}
                        step={1}
                        value={serverSetting.tran}
                        onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, tran: v })}
                    />
                    {#if selected.voiceChangerType == "RVC"}
                        <SliderRow
                            label="FORMANT"
                            hint="Formant shift alters harmonic frequencies and changes the voice timbre without affecting the pitch."
                            min={-5}
                            max={5}
                            step={0.1}
                            value={serverSetting.formantShift}
                            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, formantShift: v })}
                        />
                        <SliderRow
                            label="INDEX"
                            hint="Index embeds accent of the model's voice into your voice. Disabled when set to 0. Note that this setting increases CPU usage."
                            min={0}
                            max={1}
                            step={0.1}
                            disabled={!selected.indexFile}
                            value={serverSetting.indexRatio}
                            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, indexRatio: v })}
                        />
                    {/if}
                    <SelectRow
                        label={selected.voiceChangerType == "RVC" ? "SPEAKER" : ""}
                        value={String(serverSetting.dstId)}
                        options={speakerOptions}
                        onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, dstId: Number(v) })}
                    />
                </div>
            {/if}
        </div>
    </div>
</section>
