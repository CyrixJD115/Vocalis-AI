<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";

    let text = $state("");

    const ok = () => {
        const val = text;
        text = "";
        guiState.resolveTextInput(val);
    };
    const cancel = () => {
        text = "";
        guiState.resolveTextInput("");
    };
</script>

<Dialog title="Input Dialog" open={guiState.showTextInputDialog} width="max-w-md" onClose={cancel}>
    <form class="flex flex-col gap-4" onsubmit={(e) => { e.preventDefault(); ok(); }}>
        <label class="flex items-center gap-3 text-sm text-slate-300">
            <span class="shrink-0">Input Text:</span>
            <input class="field flex-1" type="text" bind:value={text} />
        </label>
        <div class="flex justify-end gap-2">
            <button type="button" class="btn" onclick={cancel}>cancel</button>
            <button type="submit" class="btn btn-accent">ok</button>
        </div>
    </form>
</Dialog>
