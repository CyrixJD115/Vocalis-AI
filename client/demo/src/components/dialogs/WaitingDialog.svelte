<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
</script>

<Dialog title="Operation in progress" open={guiState.showWaitingDialog} dismissable={false} width="max-w-md" onClose={() => {}}>
    <div class="flex items-center gap-3 py-2">
        <div class="vc-spin h-5 w-5 shrink-0 rounded-full border-2 border-accent-400 border-t-transparent"></div>
        <span class="text-sm text-slate-300">Waiting for the operation to complete...</span>
    </div>
</Dialog>
