<script lang="ts">
    type ServerAudioDevice = {
        index: number;
        name: string;
        hostAPI: string;
        maxInputChannels: number;
        maxOutputChannels: number;
        default_samplerate: number;
    };

    type Props = {
        devices?: ServerAudioDevice[];
        deviceId?: number;
        monitorMode?: boolean;
        label?: string;
        onDeviceChange?: (v: number) => void;
    };

    let { devices = [], deviceId = -1, monitorMode = false, label = "", onDeviceChange }: Props = $props();

    let hostApi = $state("ALL");
    let selectEl: HTMLSelectElement | null = $state(null);

    let apis = $derived([...new Set(devices.map((x) => x.hostAPI))]);
    let filtered = $derived(devices.filter((x) => x.hostAPI == hostApi || hostApi == "ALL"));
    let current = $derived(devices.find((x) => (x.hostAPI == hostApi || hostApi == "ALL") && x.index == deviceId));

    // Controlled select: re-apply after device list / filter / id changes.
    $effect(() => {
        void current;
        void hostApi;
        void filtered.length;
        void monitorMode;
        if (selectEl) {
            selectEl.value = String(current ? current.index : -1);
        }
    });
</script>

<div class="flex items-center gap-2 py-1">
    <div class="control-label w-28 shrink-0 text-right">{label}</div>
    <select class="field w-32 shrink-0" bind:value={hostApi}>
        <option value="ALL">ALL</option>
        {#each apis as api (api)}
            <option value={api}>{api}</option>
        {/each}
    </select>
    <select
        bind:this={selectEl}
        class="field min-w-0 flex-1"
        onchange={(e) => onDeviceChange?.(Number(e.currentTarget.value))}
    >
        {#if monitorMode}
            <option value="-1">none</option>
        {/if}
        {#each filtered as device (device.index)}
            <option value={String(device.index)}>[{device.hostAPI}]{device.name}</option>
        {/each}
        {#if !monitorMode}
            <option value="-1">none</option>
        {/if}
    </select>
</div>
