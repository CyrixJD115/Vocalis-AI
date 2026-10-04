<script lang="ts">
    import Icon from "../lib/icons/Icon.svelte";
    import SelectRow, { type SelectOption } from "./ui/SelectRow.svelte";
    import SliderRow from "./ui/SliderRow.svelte";
    import ServerDeviceSelect from "./ui/ServerDeviceSelect.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { appState } from "../lib/state/appState.svelte";
    import { toast } from "../lib/toast.svelte";
    import {
        AUDIO_ELEMENT_FOR_PLAY_MONITOR,
        AUDIO_ELEMENT_FOR_PLAY_RESULT,
        AUDIO_ELEMENT_FOR_TEST_CONVERTED,
        AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK,
    } from "../lib/const";
    import { downloadRecord, fileSelectorAsDataURL } from "../lib/utils";

    let inputHostApi = $state("ALL");
    let outputHostApi = $state("ALL");
    let monitorHostApi = $state("ALL");
    let audioSrcNode: MediaElementAudioSourceNode | null = null;
    let mediaElement: HTMLAudioElement | null = null;
    let displayMediaStream: MediaStream | null = null;
    let outputRecordingStarted = $state(false);

    let serverSetting = $derived(serverState.serverSetting);
    let enableServerAudio = $derived(serverSetting.enableServerAudio == 1);
    let isConverting = $derived(guiState.isConverting);
    let clientSetting = $derived(vcClientState.setting.voiceChangerClientSetting);

    let inputDeviceOptions: SelectOption[] = $derived(guiState.inputAudioDeviceInfo.map((d) => ({ value: d.deviceId, label: d.label })));
    let outputDeviceOptions: SelectOption[] = $derived(guiState.outputAudioDeviceInfo.map((d) => ({ value: d.deviceId, label: d.label })));
    let serverInputDevices = $derived(serverSetting.serverAudioInputDevices || []);
    let serverOutputDevices = $derived(serverSetting.serverAudioOutputDevices || []);

    let currentServerInput = $derived(
        serverInputDevices.find((x) => (x.hostAPI == inputHostApi || inputHostApi == "ALL") && x.index == serverSetting.serverInputDeviceId),
    );
    let currentServerOutput = $derived(
        serverOutputDevices.find((x) => (x.hostAPI == outputHostApi || outputHostApi == "ALL") && x.index == serverSetting.serverOutputDeviceId),
    );

    const setDeviceMode = async (mode: "client" | "server") => {
        const target = mode == "server" ? 1 : 0;
        if (serverSetting.enableServerAudio == target) {
            return;
        }
        await serverState.updateServerSettings({ ...serverSetting, enableServerAudio: target });
        guiState.setVoiceChangerSettingsChanged(true);
        guiState.applyOutputRouting();
        guiState.applyMonitorRouting();
    };

    const onClientInputChanged = async (val: string) => {
        guiState.setAudioInputForGUI(val);
        try {
            await vcClientState.setVoiceChangerClientSetting({ ...clientSetting, audioInput: val });
        } catch (e) {
            console.error(e);
            toast.error(String(e));
            guiState.setAudioInputForGUI("none");
            await vcClientState.setVoiceChangerClientSetting({ ...clientSetting, audioInput: null });
        }
    };

    const onFileLoadClicked = async () => {
        const [, dataURL] = await fileSelectorAsDataURL("");
        const audio = document.getElementById(AUDIO_ELEMENT_FOR_TEST_CONVERTED) as HTMLAudioElement | null;
        if (!audio || !appState.audioContext) {
            return;
        }
        audio.pause();
        audio.srcObject = null;
        audio.src = dataURL;
        audio.play();
        if (!audioSrcNode || mediaElement !== audio) {
            audioSrcNode = appState.audioContext.createMediaElementSource(audio);
            mediaElement = audio;
        }
        const dst = appState.audioContext.createMediaStreamDestination();
        audioSrcNode.connect(dst);
        try {
            await vcClientState.setVoiceChangerClientSetting({ ...clientSetting, audioInput: dst.stream });
        } catch (e) {
            console.error(e);
        }
        const echoback = document.getElementById(AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK) as HTMLAudioElement | null;
        if (echoback) {
            echoback.srcObject = dst.stream;
            echoback.play();
            echoback.volume = 0;
        }
        guiState.setFileInputEchoback(false);
    };

    const onSelectScreenClicked = async () => {
        if (displayMediaStream) {
            displayMediaStream.getTracks().forEach((t) => t.stop());
            displayMediaStream = null;
        }
        if (guiState.shareScreenEnabled) {
            guiState.shareScreenEnabled = false;
            return;
        }
        try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            if ((window as any).electronAPI) {
                displayMediaStream = await navigator.mediaDevices.getUserMedia({
                    // @ts-expect-error electron-only constraints
                    audio: { mandatory: { chromeMediaSource: "desktop" } },
                    // @ts-expect-error electron-only constraints
                    video: { mandatory: { chromeMediaSource: "desktop" } },
                });
            } else {
                displayMediaStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
            }
        } catch (e) {
            console.error(e);
            return;
        }
        if (!displayMediaStream || displayMediaStream.getAudioTracks().length == 0) {
            displayMediaStream?.getTracks().forEach((t) => t.stop());
            displayMediaStream = null;
            toast.warn("No audio in the captured screen. Select a source with audio sharing enabled.");
            return;
        }
        try {
            await vcClientState.setVoiceChangerClientSetting({ ...clientSetting, audioInput: displayMediaStream });
        } catch (e) {
            console.error(e);
        }
        guiState.shareScreenEnabled = true;
    };

    const onOutputRecordingStart = () => {
        outputRecordingStarted = true;
        vcClientState.startOutputRecording();
    };

    const onOutputRecordingStop = async () => {
        outputRecordingStarted = false;
        const record = await vcClientState.stopOutputRecording();
        if (record.length === 0) {
            toast.error("No audio was recorded. Make sure voice conversion is started before recording.");
            return;
        }
        if (appState.audioContext) {
            downloadRecord(record, appState.audioContext.sampleRate);
        }
    };

    // Re-attach converted/monitor streams once the client becomes ready
    $effect(() => {
        if (vcClientState.initialized) {
            vcClientState.attachAudioElements();
        }
    });
</script>

<div class="flex flex-col gap-0.5">
    <!-- hidden audio elements driven by the worklet streams / file input -->
    <audio id={AUDIO_ELEMENT_FOR_PLAY_RESULT} class="hidden"></audio>
    <audio id={AUDIO_ELEMENT_FOR_PLAY_MONITOR} class="hidden"></audio>
    <audio id={AUDIO_ELEMENT_FOR_TEST_CONVERTED_ECHOBACK} class="hidden"></audio>

    <!-- AUDIO mode -->
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">AUDIO</div>
        <div class="flex flex-1 items-center gap-4">
            <label class="flex cursor-pointer items-center gap-1.5 text-sm">
                <input
                    type="radio"
                    name="device-mode"
                    class="vc-radio"
                    checked={!enableServerAudio}
                    disabled={isConverting}
                    onchange={() => setDeviceMode("client")}
                />
                client
            </label>
            <label class="flex cursor-pointer items-center gap-1.5 text-sm">
                <input
                    type="radio"
                    name="device-mode"
                    class="vc-radio"
                    checked={enableServerAudio}
                    disabled={isConverting}
                    onchange={() => setDeviceMode("server")}
                />
                server
            </label>
        </div>
        <button class="btn px-2" title="Virtual audio routing setup" aria-label="Virtual audio routing setup" onclick={() => (guiState.showVirtualAudioDialog = true)}>
            <Icon name="link" size={14} />
        </button>
        <button class="btn px-2" title="Reload devices" aria-label="Reload devices" onclick={() => guiState.reloadDeviceInfo()}>
            <Icon name="refresh" size={14} />
        </button>
    </div>

    {#if !enableServerAudio}
        <!-- client input -->
        <SelectRow label="Input" value={guiState.audioInputForGUI} options={inputDeviceOptions} onValueChange={(v) => onClientInputChanged(v)} />
    {:else}
        <!-- server input -->
        <ServerDeviceSelect
            label="Input"
            devices={serverInputDevices}
            deviceId={serverSetting.serverInputDeviceId}
            onDeviceChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverInputDeviceId: v })}
        />
        {#if currentServerInput?.hostAPI === "ASIO"}
            <SelectRow
                label="Ch. (in)"
                value={String(serverSetting.asioInputChannel)}
                disabled={isConverting}
                options={[
                    { value: "-1", label: "default" },
                    ...Array.from({ length: currentServerInput.maxInputChannels }, (_, i) => ({ value: String(i), label: String(i) })),
                ]}
                onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, asioInputChannel: Number(v) })}
            />
        {/if}
    {/if}

    {#if !enableServerAudio && guiState.audioInputForGUI == "file"}
        <!-- file input row -->
        <div class="flex items-center gap-2 py-1 pl-[calc(7rem+0.75rem)]">
            <audio id={AUDIO_ELEMENT_FOR_TEST_CONVERTED} controls controlslist="nodownload noplaybackrate" class="h-8 min-w-0 flex-1"></audio>
            <button class="btn px-2" title="Load audio file" aria-label="Load audio file" onclick={onFileLoadClicked}>
                <Icon name="folder" size={14} />
            </button>
            <button
                class="btn"
                class:btn-accent={guiState.fileInputEchoback}
                onclick={() => guiState.setFileInputEchoback(!guiState.fileInputEchoback)}
                title="Echo the file input to the selected output device"
            >
                echo{guiState.fileInputEchoback}
            </button>
        </div>
    {/if}

    {#if !enableServerAudio && guiState.audioInputForGUI == "screen"}
        <!-- screen input row -->
        <div class="flex items-center gap-2 py-1 pl-[calc(7rem+0.75rem)]">
            <button class="btn" class:btn-accent={guiState.shareScreenEnabled} onclick={onSelectScreenClicked}>
                <Icon name="screen" size={14} />
                capture
            </button>
        </div>
    {/if}

    {#if !enableServerAudio}
        <!-- client output / monitor -->
        <SelectRow label="Output" value={guiState.audioOutputForGUI} options={outputDeviceOptions} onValueChange={(v) => guiState.setAudioOutputForGUI(v)} />
        <SelectRow label="Monitor" value={guiState.audioMonitorForGUI} options={outputDeviceOptions} onValueChange={(v) => guiState.setAudioMonitorForGUI(v)} />
    {:else}
        <!-- server output -->
        <ServerDeviceSelect
            label="Output"
            devices={serverOutputDevices}
            deviceId={serverSetting.serverOutputDeviceId}
            onDeviceChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverOutputDeviceId: v })}
        />
        {#if currentServerOutput?.hostAPI === "ASIO"}
            <SelectRow
                label="Ch. (out)"
                value={String(serverSetting.asioOutputChannel)}
                disabled={isConverting}
                options={[
                    { value: "-1", label: "default" },
                    ...Array.from({ length: currentServerOutput.maxOutputChannels }, (_, i) => ({ value: String(i), label: String(i) })),
                ]}
                onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, asioOutputChannel: Number(v) })}
            />
        {/if}
        <!-- server monitor -->
        <ServerDeviceSelect
            label="Monitor"
            devices={serverOutputDevices}
            deviceId={serverSetting.serverMonitorDeviceId}
            monitorMode
            onDeviceChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverMonitorDeviceId: v })}
        />
        <!-- server sample rate -->
        <SelectRow
            label="S.R."
            hint="Sample rate (Hz) used by the input/output/monitor devices. 48000 is the safest choice; 44100 matches most music gear. All devices must support the selected rate."
            value={String(serverSetting.serverAudioSampleRate)}
            options={[16000, 32000, 44100, 48000, 96000, 192000].map((sr) => ({ value: String(sr), label: `${sr} Hz` }))}
            onValueChange={(v) => {
                serverState.updateServerSettings({ ...serverSetting, serverAudioSampleRate: Number(v) });
                guiState.setVoiceChangerSettingsChanged(true);
            }}
        />
        <!-- server gains -->
        <SliderRow
            label="Gain (in)"
            hint="Input gain applied to the microphone signal before conversion."
            min={0}
            max={4}
            step={0.05}
            suffix="x"
            value={serverSetting.serverInputAudioGain}
            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverInputAudioGain: v })}
        />
        <SliderRow
            label="Gain (out)"
            hint="Output gain applied to the converted signal before it goes to the output device."
            min={0}
            max={4}
            step={0.05}
            suffix="x"
            value={serverSetting.serverOutputAudioGain}
            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverOutputAudioGain: v })}
        />
        <SliderRow
            label="Gain (mon)"
            hint="Monitor gain applied to your own monitoring feed only. Other apps never hear this."
            min={0}
            max={4}
            step={0.05}
            suffix="x"
            value={serverSetting.serverMonitorAudioGain}
            onValueChange={(v) => serverState.updateServerSettings({ ...serverSetting, serverMonitorAudioGain: v })}
        />
    {/if}

    {#if !enableServerAudio}
        <!-- output recorder -->
        <div class="flex items-center gap-3 py-1">
            <div class="control-label w-28 shrink-0 text-right">REC.</div>
            <div class="flex flex-1 gap-2">
                <button class="btn" class:btn-start-active={!outputRecordingStarted} onclick={onOutputRecordingStart}>start</button>
                <button class="btn" class:btn-stop-active={outputRecordingStarted} onclick={onOutputRecordingStop}>stop</button>
            </div>
        </div>
    {/if}
</div>
