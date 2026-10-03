<script lang="ts">
    import { tooltip } from "../../lib/tooltip";

    export type SelectOption = { value: string; label: string; disabled?: boolean };

    type Props = {
        label?: string;
        hint?: string;
        options?: SelectOption[];
        value?: string;
        disabled?: boolean;
        labelWidth?: string;
        className?: string;
        onValueChange?: (v: string) => void;
    };

    let {
        label = "",
        hint = "",
        options = [],
        value = $bindable(""),
        disabled = false,
        labelWidth = "w-28",
        className = "w-full",
        onValueChange,
    }: Props = $props();

    let selectEl: HTMLSelectElement | null = $state(null);

    // Fully controlled select: re-apply the desired value after every change of
    // value OR options, so late-arriving device lists never lose the selection.
    $effect(() => {
        const v = String(value);
        const opts = options;
        if (selectEl && selectEl.value !== v && (opts.some((o) => o.value === v) || v === "")) {
            selectEl.value = v;
        }
    });

    const handleChange = (e: Event) => {
        value = (e.currentTarget as HTMLSelectElement).value;
        onValueChange?.(value);
    };
</script>

<div class="flex items-center gap-3 py-1">
    {#if label}
        <div class={"control-label shrink-0 text-right " + labelWidth}>
            <span
                use:tooltip={hint || undefined}
                class={hint ? "cursor-help underline decoration-dotted decoration-slate-500 underline-offset-4" : ""}
            >
                {label}
            </span>
        </div>
    {/if}
    <select
        bind:this={selectEl}
        class={"field min-w-0 " + className}
        {disabled}
        onchange={handleChange}
    >
        {#each options as o (o.value)}
            <option value={o.value} disabled={o.disabled}>{o.label}</option>
        {/each}
    </select>
</div>
