<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { serverState } from "../../lib/state/serverState.svelte";

    const ok = async () => {
        await serverState.updateServerSettings({ ...serverState.serverSetting, passThrough: true });
        guiState.showPassThroughDialog = false;
    };
    const cancel = () => {
        guiState.showPassThroughDialog = false;
    };
</script>

<Dialog title="Enable Pass Through" open={guiState.showPassThroughDialog} width="max-w-md" onClose={cancel}>
    <p class="mb-4 text-sm text-slate-300">
        Pass through sends your input voice to the output <span class="font-semibold text-slate-100">without</span> voice conversion. Enable it?
    </p>
    <div class="flex justify-center gap-3">
        <button class="btn btn-accent px-8" onclick={ok}>OK</button>
        <button class="btn px-8" onclick={cancel}>Cancel</button>
    </div>
</Dialog>
