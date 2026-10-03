<script lang="ts">
    import { serverState } from "../lib/state/serverState.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { AUDIO_ELEMENT_FOR_SAMPLING_INPUT, AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT } from "../lib/const";

    let serverIORecording = $state(false);

    let serverSetting = $derived(serverState.serverSetting);

    let analyzerOptions = $derived(
        guiState.outputAudioDeviceInfo.filter((d) => d.deviceId != "none").map((d) => ({ value: d.deviceId, label: d.label })),
    );

    const onSioRecStart = async () => {
        serverIORecording = true;
        await serverState.updateServerSettings({ ...serverSetting, recordIO: 1 });
    };

    const onSioRecStop = async () => {
        serverIORecording = false;
        await serverState.updateServerSettings({ ...serverSetting, recordIO: 0 });
        const wavInput = document.getElementById(AUDIO_ELEMENT_FOR_SAMPLING_INPUT) as HTMLAudioElement | null;
        const wavOutput = document.getElementById(AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT) as HTMLAudioElement | null;
        for (const [el, src] of [
            [wavInput, "/tmp/in.wav"],
            [wavOutput, "/tmp/out.wav"],
        ] as const) {
            if (el) {
                el.src = `${src}?${Date.now()}`;
                el.controls = true;
                try {
                    el.setSinkId(guiState.audioOutputForAnalyzer);
                } catch (e) {
                    console.log(e);
                }
            }
        }
    };
</script>

<div class="flex flex-col gap-0.5">
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">SIO rec.</div>
        <div class="flex flex-1 gap-2">
            <button class="btn" class:btn-start-active={serverIORecording} onclick={onSioRecStart}>start</button>
            <button class="btn" class:btn-stop-active={serverIORecording} onclick={onSioRecStop}>stop</button>
        </div>
    </div>
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">output</div>
        <select
            class="field min-w-0 flex-1"
            value={guiState.audioOutputForAnalyzer}
            onchange={(e) => guiState.setAudioOutputForAnalyzer(e.currentTarget.value)}
        >
            <option value="default">default</option>
            {#each analyzerOptions as o (o.value)}
                <option value={o.value}>{o.label}</option>
            {/each}
        </select>
    </div>
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">in</div>
        <audio id={AUDIO_ELEMENT_FOR_SAMPLING_INPUT} controls class="h-8 min-w-0 flex-1"></audio>
    </div>
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">out</div>
        <audio id={AUDIO_ELEMENT_FOR_SAMPLING_OUTPUT} controls class="h-8 min-w-0 flex-1"></audio>
    </div>
</div>
