<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import { serverState } from "../../lib/state/serverState.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { toast } from "../../lib/toast.svelte";
    import { VoiceChangerType, type MergeElement, type RVCModelSlot } from "@vc-lib/const";
    import { downloadFile } from "../../lib/utils";

    type FilterItem = { type: string; samplingRate: number; embChannels: number };

    let currentFilter = $state("");
    let mergeElements = $state<MergeElement[]>([]);

    let modelSlots = $derived(serverState.serverSetting.modelSlots || []);
    let slotNameByIndex = $derived(new Map(modelSlots.map((x) => [x.slotIndex, x.name])));

    // Distinct model "types" among RVC pytorch slots
    let filterItems = $derived.by(() => {
        const items: Record<string, FilterItem> = {};
        for (const x of modelSlots) {
            if (x.voiceChangerType != "RVC") {
                continue;
            }
            const slot = x as RVCModelSlot;
            if (!slot.modelFile || slot.modelFile.length == 0 || slot.isONNX) {
                continue;
            }
            const key = `${slot.modelType},${slot.samplingRate},${slot.embChannels}`;
            items[key] = { type: slot.modelType, samplingRate: slot.samplingRate, embChannels: slot.embChannels };
        }
        return items;
    });

    let filterKeys = $derived(Object.keys(filterItems));

    // Keep the current filter valid
    $effect(() => {
        if (filterKeys.length > 0 && !filterKeys.includes(currentFilter)) {
            currentFilter = filterKeys[0];
        }
    });

    let models = $derived(
        modelSlots.filter((x) => {
            if (x.voiceChangerType != "RVC") {
                return false;
            }
            const slot = x as RVCModelSlot;
            if (!slot.modelFile || slot.modelFile.length == 0 || slot.isONNX) {
                return false;
            }
            const item = filterItems[currentFilter];
            if (!item) {
                return false;
            }
            return slot.modelType == item.type && slot.samplingRate == item.samplingRate && slot.embChannels == item.embChannels;
        }),
    );

    // Reset merge elements when the filtered model set changes
    $effect(() => {
        mergeElements = models.map((x) => ({ slotIndex: x.slotIndex, strength: 0 }));
    });

    const onMergeElementsChanged = (slotIndex: number, val: number) => {
        mergeElements = mergeElements.map((x) => (x.slotIndex == slotIndex ? { slotIndex, strength: val } : x));
    };

    const onMergeClicked = async () => {
        const validMergeElements = mergeElements.filter((x) => x.strength > 0);
        await serverState.mergeModel({
            voiceChangerType: VoiceChangerType.RVC,
            command: "mix",
            files: validMergeElements,
        });
        downloadFile("/tmp/merged.pth", "merged.pth");
        toast.info("Check your browser downloads for the merged model.");
    };
</script>

<Dialog title="Merge Lab" open={guiState.showMergeLabDialog} width="max-w-2xl" onClose={() => (guiState.showMergeLabDialog = false)}>
    <div class="flex flex-col gap-4">
        <div class="flex items-center gap-3">
            <span class="control-label">Type</span>
            <select class="field w-72" bind:value={currentFilter}>
                {#each filterKeys as key (key)}
                    <option value={key}>{key}</option>
                {/each}
            </select>
        </div>

        {#if models.length === 0}
            <div class="py-6 text-center text-sm text-slate-500">No mergeable models for this type.</div>
        {:else}
            <div class="flex flex-col gap-2">
                {#each models as model (model.slotIndex)}
                    {@const element = mergeElements.find((x) => x.slotIndex == model.slotIndex)}
                    <div class="flex items-center gap-3 rounded-xl border border-white/[0.07] bg-black/20 px-3 py-2">
                        <span class="w-40 shrink-0 truncate text-sm text-slate-200" title={model.name}>{slotNameByIndex.get(model.slotIndex) || model.name}</span>
                        <input
                            type="range"
                            class="vc-slider min-w-0 flex-1"
                            style={`--vc-fill: ${element?.strength ?? 0}%`}
                            min={0}
                            max={100}
                            step={1}
                            value={element?.strength ?? 0}
                            oninput={(e) => onMergeElementsChanged(model.slotIndex, Number(e.currentTarget.value))}
                        />
                        <span class="w-10 shrink-0 text-right text-xs tabular-nums text-slate-300">{element?.strength ?? 0}</span>
                    </div>
                {/each}
            </div>
        {/if}

        <p class="text-xs text-slate-500">Check your browser downloads for the merged model.</p>
        <div class="flex justify-center">
            <button class="btn btn-accent px-8" disabled={models.length === 0} onclick={onMergeClicked}>merge</button>
        </div>
    </div>
</Dialog>
