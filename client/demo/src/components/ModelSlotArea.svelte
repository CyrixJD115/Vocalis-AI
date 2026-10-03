<script lang="ts">
    import Icon from "../lib/icons/Icon.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { guiState } from "../lib/state/guiState.svelte";
    import { basename } from "../lib/utils";

    type SortType = "slot" | "name";
    let sortType: SortType = $state("slot");

    let modelSlots = $derived(serverState.serverSetting.modelSlots || []);
    let sortedSlots = $derived(
        sortType == "slot"
            ? modelSlots
            : [...modelSlots].sort((a, b) => a.name.localeCompare(b.name)),
    );

    const selectSlot = async (slotIndex: number) => {
        if (slotIndex === serverState.serverSetting.modelSlotIndex) {
            return;
        }
        guiState.showWaitingDialog = true;
        try {
            await serverState.updateServerSettings({ ...serverState.serverSetting, modelSlotIndex: slotIndex });
        } finally {
            guiState.showWaitingDialog = false;
        }
    };

    const iconUrl = (iconFile: string) => {
        if (iconFile.length > 0) {
            return serverState.serverSetting.voiceChangerParams.model_dir + "/" + iconFile;
        }
        return "./assets/icons/human.png";
    };
</script>

<section class="card p-4">
    <div class="mb-3 flex items-center justify-between">
        <div class="card-title">Voice Models</div>
        <div class="flex items-center gap-2">
            <div class="flex overflow-hidden rounded-lg border border-white/10">
                <button
                    class={"px-2 py-1.5 transition-colors " + (sortType == "slot" ? "bg-white/10 text-white" : "text-slate-500")}
                    onclick={() => (sortType = "slot")}
                    title="Sort by slot"
                    aria-label="Sort by slot"
                >
                    <Icon name="sort-numeric" size={15} />
                </button>
                <button
                    class={"border-l border-white/10 px-2 py-1.5 transition-colors " + (sortType == "name" ? "bg-white/10 text-white" : "text-slate-500")}
                    onclick={() => (sortType = "name")}
                    title="Sort by name"
                    aria-label="Sort by name"
                >
                    <Icon name="sort-alpha" size={15} />
                </button>
            </div>
            <button class="btn" onclick={() => (guiState.showModelSlotManagerDialog = true)}>
                <Icon name="pencil" size={14} />
                edit
            </button>
        </div>
    </div>

    {#if sortedSlots.length === 0}
        <div class="py-6 text-center text-sm text-slate-500">No models loaded. Use <span class="text-slate-300">edit</span> to upload or download models.</div>
    {:else}
        <div class="flex gap-2 overflow-x-auto pb-1">
            {#each sortedSlots as slot (slot.slotIndex)}
                {#if slot.modelFile && slot.modelFile.length > 0}
                    {@const name = slot.name.length > 8 ? slot.name.substring(0, 7) + "..." : slot.name}
                    {@const selected = slot.slotIndex == serverState.serverSetting.modelSlotIndex}
                    <button
                        class={
                            "group relative flex w-24 shrink-0 flex-col items-center gap-1.5 rounded-xl border p-2 transition-all " +
                            (selected
                                ? "border-accent-400 bg-accent-400/10 ring-2 ring-accent-400/40"
                                : "border-white/10 bg-white/[0.04] hover:border-white/25")
                        }
                        onclick={() => selectSlot(slot.slotIndex)}
                    >
                        <div class="relative h-16 w-16 overflow-hidden rounded-lg bg-ink-800">
                            {#if slot.iconFile.length > 0}
                                <img src={iconUrl(`${slot.slotIndex}/${basename(slot.iconFile)}`)} alt={slot.name} class="h-full w-full object-cover opacity-80" />
                            {:else}
                                <div class="flex h-full w-full items-center justify-center text-[10px] text-slate-600">no image</div>
                            {/if}
                            <span class="absolute bottom-0 left-0 right-0 truncate bg-black/60 px-1 text-center text-[9px] text-accent-300">
                                {slot.voiceChangerType}
                            </span>
                        </div>
                        <span class="w-full truncate text-center text-xs text-slate-300" title={slot.name}>{name}</span>
                    </button>
                {/if}
            {/each}
        </div>
    {/if}
</section>
