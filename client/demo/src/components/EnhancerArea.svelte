<script lang="ts">
    import SliderRow from "./ui/SliderRow.svelte";
    import SelectRow, { type SelectOption } from "./ui/SelectRow.svelte";
    import { serverState } from "../lib/state/serverState.svelte";
    import { guiState } from "../lib/state/guiState.svelte";

    let serverSetting = $derived(serverState.serverSetting);

    const boolOptions: SelectOption[] = [
        { value: "0", label: "off" },
        { value: "1", label: "on" },
    ];

    const upd = async (patch: Record<string, unknown>) => {
        guiState.showWaitingDialog = true;
        try {
            await serverState.updateServerSettings({ ...serverSetting, ...patch });
        } finally {
            guiState.showWaitingDialog = false;
        }
    };

    // One click starting points. Everything stays tunable afterwards.
    const presets = {
        clean: {
            enhancerEnabled: 1,
            enhancerGateEnabled: 1,
            enhancerGateThreshold: -60,
            enhancerHpEnabled: 1,
            enhancerHpFreq: 80,
            enhancerLpEnabled: 0,
            enhancerNrEnabled: 1,
            enhancerNrAmount: 45,
            enhancerDeEssEnabled: 1,
            enhancerDeEssAmount: 3,
            enhancerEqEnabled: 0,
            enhancerEqLow: 0,
            enhancerEqMid: 0,
            enhancerEqHigh: 0,
            enhancerCompEnabled: 0,
            enhancerCompThreshold: -24,
            enhancerCompRatio: 4,
            enhancerCompAttack: 10,
            enhancerCompRelease: 100,
            enhancerCompMakeup: 0,
            enhancerLimiterEnabled: 1,
            enhancerLimiterCeiling: -1,
        },
        broadcast: {
            enhancerEnabled: 1,
            enhancerGateEnabled: 1,
            enhancerGateThreshold: -55,
            enhancerHpEnabled: 1,
            enhancerHpFreq: 90,
            enhancerLpEnabled: 1,
            enhancerLpFreq: 14000,
            enhancerNrEnabled: 1,
            enhancerNrAmount: 60,
            enhancerDeEssEnabled: 1,
            enhancerDeEssAmount: 4,
            enhancerEqEnabled: 1,
            enhancerEqLow: 1.5,
            enhancerEqMid: 0,
            enhancerEqHigh: 2,
            enhancerCompEnabled: 1,
            enhancerCompThreshold: -26,
            enhancerCompRatio: 4,
            enhancerCompAttack: 10,
            enhancerCompRelease: 120,
            enhancerCompMakeup: 3,
            enhancerLimiterEnabled: 1,
            enhancerLimiterCeiling: -1,
        },
        off: {
            enhancerEnabled: 0,
        },
    };

    const applyPreset = (name: keyof typeof presets) => upd(presets[name]);

    const setBool = (key: string, v: string) => upd({ [key]: Number(v) });
    const setNum = (key: string, v: number) => upd({ [key]: v });
</script>

<div class="flex flex-col gap-0.5">
    <!-- master + presets -->
    <div class="flex items-center gap-3 py-1">
        <div class="control-label w-28 shrink-0 text-right">
            <span
                class="cursor-help underline decoration-dotted decoration-slate-500 underline-offset-4"
                title="Post-processing chain applied to the converted voice on the server. Works in both client and server audio mode, and on passthrough."
            >
                ENHANCER
            </span>
        </div>
        <select class="field w-24" value={serverSetting.enhancerEnabled ? "1" : "0"} onchange={(e) => setBool("enhancerEnabled", e.currentTarget.value)}>
            <option value="0">off</option>
            <option value="1">on</option>
        </select>
        <div class="flex flex-1 gap-2">
            <button class="btn" onclick={() => applyPreset("clean")} title="Light cleanup: gate, high-pass, noise reduction, de-esser, limiter">clean</button>
            <button class="btn" onclick={() => applyPreset("broadcast")} title="Dense streaming sound: adds EQ, low-pass and compression">broadcast</button>
            <button class="btn" onclick={() => applyPreset("off")}>bypass</button>
        </div>
    </div>

    {#if serverSetting.enhancerEnabled}
        <!-- Noise Reduction -->
        <SelectRow
            label="NR"
            hint="Spectral noise reduction. Removes steady background noise (fans, keyboard, hum). Start around 40-60; too much makes the voice watery."
            value={String(serverSetting.enhancerNrEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerNrEnabled", v)}
        />
        {#if serverSetting.enhancerNrEnabled}
            <SliderRow
                label="Amount"
                hint="Noise reduction strength."
                min={0}
                max={100}
                step={1}
                suffix="%"
                value={serverSetting.enhancerNrAmount}
                onValueChange={(v) => setNum("enhancerNrAmount", v)}
            />
        {/if}

        <!-- Gate -->
        <SelectRow
            label="GATE"
            hint="Noise gate. Mutes the output when nobody is speaking, so listeners hear pure silence instead of the noise floor."
            value={String(serverSetting.enhancerGateEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerGateEnabled", v)}
        />
        {#if serverSetting.enhancerGateEnabled}
            <SliderRow
                label="Thresh"
                hint="Gate threshold. Everything quieter than this is muted."
                min={-90}
                max={-30}
                step={1}
                suffix="dB"
                value={serverSetting.enhancerGateThreshold}
                onValueChange={(v) => setNum("enhancerGateThreshold", v)}
            />
        {/if}

        <!-- High-pass / Low-pass -->
        <SelectRow
            label="HP"
            hint="High-pass filter. Removes rumble, plosive pops and mic handling noise below the cutoff."
            value={String(serverSetting.enhancerHpEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerHpEnabled", v)}
        />
        {#if serverSetting.enhancerHpEnabled}
            <SliderRow
                label="Freq"
                hint="High-pass cutoff. 70-100 Hz is typical for voice."
                min={40}
                max={300}
                step={5}
                suffix="Hz"
                value={serverSetting.enhancerHpFreq}
                onValueChange={(v) => setNum("enhancerHpFreq", v)}
            />
        {/if}
        <SelectRow
            label="LP"
            hint="Low-pass filter. Tames hiss and high-frequency artifacts above the cutoff."
            value={String(serverSetting.enhancerLpEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerLpEnabled", v)}
        />
        {#if serverSetting.enhancerLpEnabled}
            <SliderRow
                label="Freq"
                hint="Low-pass cutoff. 12000-16000 Hz keeps voice airy; 8000 Hz sounds like a phone call."
                min={4000}
                max={20000}
                step={500}
                suffix="Hz"
                value={serverSetting.enhancerLpFreq}
                onValueChange={(v) => setNum("enhancerLpFreq", v)}
            />
        {/if}

        <!-- De-esser -->
        <SelectRow
            label="DE-ESS"
            hint="De-esser. Compresses sharp 's'/'sh' sibilance above ~5 kHz so converted voices don't stab ears."
            value={String(serverSetting.enhancerDeEssEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerDeEssEnabled", v)}
        />
        {#if serverSetting.enhancerDeEssEnabled}
            <SliderRow
                label="Amount"
                hint="De-essing amount. 2-4 is subtle; above 6 lisps start to appear."
                min={0}
                max={10}
                step={0.5}
                value={serverSetting.enhancerDeEssAmount}
                onValueChange={(v) => setNum("enhancerDeEssAmount", v)}
            />
        {/if}

        <!-- EQ -->
        <SelectRow
            label="EQ"
            hint="Three-band equalizer to shape the converted voice."
            value={String(serverSetting.enhancerEqEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerEqEnabled", v)}
        />
        {#if serverSetting.enhancerEqEnabled}
            <SliderRow
                label="Low"
                hint="Low shelf at 180 Hz. Adds warmth or removes boominess."
                min={-12}
                max={12}
                step={0.5}
                suffix="dB"
                value={serverSetting.enhancerEqLow}
                onValueChange={(v) => setNum("enhancerEqLow", v)}
            />
            <SliderRow
                label="Mid"
                hint="Peak filter at 1.2 kHz. Presence/body of the voice."
                min={-12}
                max={12}
                step={0.5}
                suffix="dB"
                value={serverSetting.enhancerEqMid}
                onValueChange={(v) => setNum("enhancerEqMid", v)}
            />
            <SliderRow
                label="High"
                hint="High shelf at 4 kHz. Brightness/air."
                min={-12}
                max={12}
                step={0.5}
                suffix="dB"
                value={serverSetting.enhancerEqHigh}
                onValueChange={(v) => setNum("enhancerEqHigh", v)}
            />
        {/if}

        <!-- Compressor -->
        <SelectRow
            label="COMP"
            hint="Compressor. Evens out loud and quiet parts so streaming apps stop auto-gaining you. Applies after the EQ."
            value={String(serverSetting.enhancerCompEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerCompEnabled", v)}
        />
        {#if serverSetting.enhancerCompEnabled}
            <SliderRow
                label="Thresh"
                hint="Compression starts above this level."
                min={-60}
                max={0}
                step={1}
                suffix="dB"
                value={serverSetting.enhancerCompThreshold}
                onValueChange={(v) => setNum("enhancerCompThreshold", v)}
            />
            <SliderRow
                label="Ratio"
                hint="Compression ratio. 4:1 is gentle leveling, 10:1 is heavy."
                min={1}
                max={20}
                step={0.5}
                suffix=":1"
                value={serverSetting.enhancerCompRatio}
                onValueChange={(v) => setNum("enhancerCompRatio", v)}
            />
            <SliderRow
                label="Attack"
                hint="How fast compression engages."
                min={1}
                max={100}
                step={1}
                suffix="ms"
                value={serverSetting.enhancerCompAttack}
                onValueChange={(v) => setNum("enhancerCompAttack", v)}
            />
            <SliderRow
                label="Release"
                hint="How fast compression lets go."
                min={10}
                max={500}
                step={10}
                suffix="ms"
                value={serverSetting.enhancerCompRelease}
                onValueChange={(v) => setNum("enhancerCompRelease", v)}
            />
            <SliderRow
                label="Makeup"
                hint="Makeup gain added after compression."
                min={0}
                max={24}
                step={0.5}
                suffix="dB"
                value={serverSetting.enhancerCompMakeup}
                onValueChange={(v) => setNum("enhancerCompMakeup", v)}
            />
        {/if}

        <!-- Limiter -->
        <SelectRow
            label="LIMIT"
            hint="Brickwall limiter. Guarantees the output never exceeds the ceiling - recommended always on when boosting anything."
            value={String(serverSetting.enhancerLimiterEnabled)}
            options={boolOptions}
            onValueChange={(v) => setBool("enhancerLimiterEnabled", v)}
        />
        {#if serverSetting.enhancerLimiterEnabled}
            <SliderRow
                label="Ceiling"
                hint="Maximum output level."
                min={-12}
                max={-1}
                step={0.5}
                suffix="dB"
                value={serverSetting.enhancerLimiterCeiling}
                onValueChange={(v) => setNum("enhancerLimiterCeiling", v)}
            />
        {/if}
    {/if}
</div>
