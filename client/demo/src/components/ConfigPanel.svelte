<script lang="ts">
    import QualityArea from "./QualityArea.svelte";
    import ConvertArea from "./ConvertArea.svelte";
    import DeviceArea from "./DeviceArea.svelte";
    import ServerIOAnalyzer from "./ServerIOAnalyzer.svelte";
    import { guiState } from "../lib/state/guiState.svelte";

    let { detectors = [] }: { detectors?: string[] } = $props();
</script>

<div class="flex flex-col gap-4">
    <section class="card p-4">
        <div class="card-title mb-2">Quality &amp; Conversion</div>
        <QualityArea {detectors} />
        <div class="my-2 border-t border-white/[0.07]"></div>
        <ConvertArea />
    </section>

    <section class="card p-4">
        <div class="card-title mb-2">Audio &amp; Devices</div>
        <DeviceArea />
    </section>

    <section class="card p-4">
        <div class="card-title mb-2">ServerIO Analyzer</div>
        <ServerIOAnalyzer />
    </section>

    <section class="card p-4">
        <div class="flex flex-wrap items-center gap-2">
            <span class="control-label mr-1">more...</span>
            <button class="btn" onclick={() => (guiState.showMergeLabDialog = true)}>Merge Lab</button>
            <button class="btn" onclick={() => (guiState.showAdvancedSettingDialog = true)}>Advanced Setting</button>
            <button class="btn" onclick={() => (guiState.showServerInfoDialog = true)}>Server Info</button>
            <button class="btn" onclick={() => (guiState.showClientInfoDialog = true)}>Client Info</button>
        </div>
    </section>
</div>
