<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import Icon from "../../lib/icons/Icon.svelte";

    type Props = {
        title: string;
        open: boolean;
        onClose: () => void;
        width?: string;
        dismissable?: boolean;
        children?: import("svelte").Snippet;
    };

    let { title, open, onClose, width = "max-w-2xl", dismissable = true, children }: Props = $props();
</script>

{#if open}
    <div class="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" onclick={() => dismissable && onClose()} aria-hidden="true"></div>
        <div class="vc-dialog-frame relative flex max-h-[88vh] w-full flex-col rounded-2xl border border-white/10 bg-ink-900 shadow-2xl {width}">
            <div class="flex shrink-0 items-center justify-between border-b border-white/10 px-5 py-3">
                <h2 class="text-sm font-semibold tracking-wide text-slate-100">{title}</h2>
                {#if dismissable}
                    <button class="btn px-2" aria-label="close" onclick={onClose}>
                        <Icon name="x" size={14} />
                    </button>
                {/if}
            </div>
            <div class="overflow-y-auto p-5">
                {@render children?.()}
            </div>
        </div>
    </div>
{/if}
