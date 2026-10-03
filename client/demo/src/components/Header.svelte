<script lang="ts">
    import Icon from "../lib/icons/Icon.svelte";
    import { appState, idb } from "../lib/state/appState.svelte";
    import { vcClientState } from "../lib/state/vcClient.svelte";
    import { INDEXEDDB_KEY_AUDIO_OUTPUT, INDEXEDDB_KEY_AUDIO_MONITR, isDesktopApp, openExternal } from "../lib/const";

    let { mainTitle = "Realtime Voice Changer Client", subTitle = "" }: { mainTitle?: string; subTitle?: string } = $props();

    const onClearSettingClicked = async () => {
        if (!window.confirm("This will remove all settings and reload the page. Continue?")) {
            return;
        }
        await vcClientState.clearSetting();
        await idb.removeItem(INDEXEDDB_KEY_AUDIO_OUTPUT);
        await idb.removeItem(INDEXEDDB_KEY_AUDIO_MONITR);
        await idb.removeDB();
        location.reload();
    };
</script>

<header class="mb-4 flex flex-wrap items-center justify-between gap-3">
    <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 class="text-xl font-semibold tracking-wide text-slate-100 md:text-2xl">{mainTitle}</h1>
        {#if subTitle}
            <span class="text-sm text-slate-400">{subTitle}</span>
        {/if}
        {#if appState.version}
            <span class="chip">v{appState.version}</span>
        {/if}
        {#if appState.edition}
            <span class="chip">{appState.edition}</span>
        {/if}
    </div>
    <div class="flex items-center gap-2">
        <button
            class="btn"
            onclick={() => openExternal("https://github.com/deiteris/voice-changer")}
            aria-label="Github"
            title="Github"
        >
            <Icon name="github" size={18} />
        </button>
        <button class="btn" onclick={onClearSettingClicked}>clear setting</button>
    </div>
</header>
