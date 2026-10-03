<script lang="ts">
    import NumberInput from "./NumberInput.svelte";
    import { tooltip } from "../../lib/tooltip";

    type Props = {
        label: string;
        hint?: string;
        value: number;
        min: number;
        max: number;
        step?: number;
        disabled?: boolean;
        suffix?: string;
        showNumber?: boolean;
        labelWidth?: string;
        onValueChange?: (v: number) => void;
        children?: import("svelte").Snippet;
    };

    let {
        label,
        hint = "",
        value = $bindable(0),
        min,
        max,
        step = 1,
        disabled = false,
        suffix = "",
        showNumber = true,
        labelWidth = "w-28",
        onValueChange,
        children,
    }: Props = $props();

    let fillPct = $derived(((value - min) / (max - min)) * 100);
</script>

<div class="flex items-center gap-3 py-1">
    <div class={"control-label shrink-0 text-right " + labelWidth}>
        <span
            use:tooltip={hint || undefined}
            class={hint ? "cursor-help underline decoration-dotted decoration-slate-500 underline-offset-4" : ""}
        >
            {label}
        </span>
    </div>
    <input
        type="range"
        class="vc-slider min-w-0 flex-1"
        style={`--vc-fill: ${fillPct}%`}
        {min}
        {max}
        {step}
        {disabled}
        bind:value
        oninput={() => onValueChange?.(value)}
    />
    <div class="flex shrink-0 items-center justify-end gap-1.5 text-xs tabular-nums text-slate-300" class:opacity-40={disabled}>
        {#if showNumber}
            <NumberInput {value} {min} {max} {step} {disabled} {onValueChange} />
        {/if}
        {#if children}
            {@render children()}
        {/if}
        {#if suffix}
            <span class="w-7 text-left">{suffix}</span>
        {/if}
    </div>
</div>
