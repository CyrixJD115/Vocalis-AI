<script lang="ts">
    import { toastState } from "../lib/toast.svelte";

    const styles: Record<string, string> = {
        info: "border-sky-400/40 bg-sky-950/90 text-sky-100",
        success: "border-emerald-400/40 bg-emerald-950/90 text-emerald-100",
        warn: "border-amber-400/40 bg-amber-950/90 text-amber-100",
        error: "border-rose-400/40 bg-rose-950/90 text-rose-100",
    };
</script>

<div class="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
    {#each toastState.toasts as t (t.id)}
        <div
            class="pointer-events-auto rounded-xl border px-4 py-3 text-sm shadow-xl backdrop-blur transition-all duration-300 {styles[t.kind]}"
            class:opacity-0={t.leaving}
            class:translate-x-4={t.leaving}
        >
            {t.message}
        </div>
    {/each}
</div>
