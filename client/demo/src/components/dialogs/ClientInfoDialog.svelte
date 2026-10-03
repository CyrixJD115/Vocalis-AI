<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { vcClientState } from "../../lib/state/vcClient.svelte";
    import { appState } from "../../lib/state/appState.svelte";

    let clientInfo = $derived.by(() => {
        const ctx = appState.audioContext;
        const ctxInfo = ctx
            ? {
                  sampleRate: ctx.sampleRate,
                  baseLatency: ctx.baseLatency,
                  currentTime: ctx.currentTime,
                  outputLatency: (ctx as AudioContext & { outputLatency?: number }).outputLatency,
                  sinkId: (ctx as AudioContext & { sinkId?: string }).sinkId,
                  state: ctx.state,
              }
            : "AudioContext is not initialized yet. Interact with the page first.";
        return JSON.stringify(vcClientState.setting, null, 4) + "\n" + JSON.stringify(ctxInfo, null, 4);
    });
</script>

<Dialog title="Client Information" open={guiState.showClientInfoDialog} width="max-w-3xl" onClose={() => (guiState.showClientInfoDialog = false)}>
    <textarea class="field h-96 w-full resize-none font-mono text-xs" readonly value={clientInfo}></textarea>
</Dialog>
