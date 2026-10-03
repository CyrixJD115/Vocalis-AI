<script lang="ts">
    type Props = {
        value: number;
        min: number;
        max: number;
        step?: number;
        disabled?: boolean;
        className?: string;
        onValueChange?: (val: number) => void;
    };

    let { value = $bindable(0), min, max, step = 1, disabled = false, className = "", onValueChange }: Props = $props();

    let text = $state(String(value));
    let lastEmitted = value;

    // Sync from external value changes (server reload, slider drag, clamping)
    $effect(() => {
        if (value !== lastEmitted) {
            lastEmitted = value;
            text = String(value);
        }
    });

    const handleInput = (e: Event) => {
        text = (e.currentTarget as HTMLInputElement).value;
        const t = text.trim();
        if (t === "" || t === "-") {
            return;
        }
        const v = Number(t);
        if (Number.isNaN(v)) {
            return;
        }
        const clamped = Math.min(max, Math.max(min, v));
        lastEmitted = clamped;
        value = clamped;
        onValueChange?.(clamped);
    };

    const handleBlur = () => {
        text = String(value);
        lastEmitted = value;
    };
</script>

<input
    type="text"
    inputmode="decimal"
    class={"field w-20 text-right tabular-nums " + className}
    {disabled}
    value={text}
    oninput={handleInput}
    onblur={handleBlur}
/>
