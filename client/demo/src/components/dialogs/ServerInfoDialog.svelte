<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { serverState } from "../../lib/state/serverState.svelte";
</script>

<Dialog title="Server Information" open={guiState.showServerInfoDialog} width="max-w-3xl" onClose={() => (guiState.showServerInfoDialog = false)}>
    <textarea class="field h-96 w-full resize-none font-mono text-xs" readonly value={JSON.stringify(serverState.serverSetting, null, 4)}></textarea>
</Dialog>
