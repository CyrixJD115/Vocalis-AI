<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { appState } from "../../lib/state/appState.svelte";
    import { isDesktopApp, openExternal } from "../../lib/const";

    const repoUrl = "https://github.com/deiteris/voice-changer";
</script>

<Dialog title="Welcome to Realtime Voice Changer!" open={guiState.showStartingNoticeDialog} dismissable={false} width="max-w-xl" onClose={() => {}}>
    <div class="flex flex-col gap-3 text-sm text-slate-300">
        <p>
            Thank you for using this application!<br />
            If you like this application, leave a star or file an issue in the Github repository.
        </p>
        <p>
            {#if isDesktopApp()}
                <button class="text-accent-300 underline underline-offset-2" onclick={() => openExternal(repoUrl)}>Click here</button>
            {:else}
                <a class="text-accent-300 underline underline-offset-2" href={repoUrl} target="_blank" rel="noopener noreferrer">Click here</a>
            {/if}
            to open the repository.
        </p>
        {#if appState.edition.indexOf("DirectML") >= 0}
            <div class="rounded-xl border border-amber-400/30 bg-amber-950/30 p-3 text-amber-100">
                <p class="mb-1">DirectML version is an experimental version. There are the known issues as follows.</p>
                <p>
                    (1) When some settings are changed, conversion process becomes slow even when using GPU. If this occurs, reset the GPU value to -1 and then
                    back to 0.
                </p>
            </div>
        {/if}
        <p class="mt-1">Click "Start" to start using the application.</p>
        <div class="mt-2 flex justify-center">
            <button class="btn btn-accent px-8" onclick={() => (guiState.showStartingNoticeDialog = false)}>Start</button>
        </div>
    </div>
</Dialog>
