<script lang="ts">
    import Dialog from "./Dialog.svelte";
    import Icon from "../../lib/icons/Icon.svelte";
    import { serverState } from "../../lib/state/serverState.svelte";
    import { guiState } from "../../lib/state/guiState.svelte";
    import { toast } from "../../lib/toast.svelte";
    import { registerMessages, getMessage } from "../../lib/i18n";
    import { basename, checkExtention, downloadFile, fileSelector, trimfileName } from "../../lib/utils";
    import { MODEL_ICON_BLANK_URL } from "../../lib/const";
    import { VoiceChangerType, type RVCModelSlot } from "@vc-lib/const";
    import type { ModelFileKind, ModelUploadSetting } from "../../lib/state/uploadTypes";
    import { ModelFileKind as ModelFileKindEnum } from "../../lib/state/uploadTypes";

    registerMessages("ModelSlotManager", {
        change_icon: { ja: "アイコン変更", en: "change icon" },
        rename: { ja: "リネーム", en: "rename" },
        download: { ja: "ダウンロード", en: "download" },
        terms_of_use: { ja: "利用規約", en: "terms of use" },
        sample: { ja: "サンプル", en: "DL sample" },
        upload: { ja: "アップロード", en: "upload" },
        edit: { ja: "編集", en: "edit" },
        header_message: { ja: "サンプルをダウンロード", en: "Download Sample for" },
        alert_model_file: { ja: "モデルファイルを選択してください。", en: "file is not selected." },
        alert_extention: { ja: "ファイルの拡張子が不正です。", en: "extension of file should be the following." },
        speaker_id: { ja: "話者登録", en: "Speaker ID" },
    });

    type Screen = "Main" | "SampleDownloader" | "FileUploader" | "Editor";

    let screen: Screen = $state("Main");
    let targetIndex = $state(0);

    let slots = $derived(serverState.serverSetting.modelSlots || []);

    const close = () => (guiState.showModelSlotManagerDialog = false);
    const backToSlotManager = () => (screen = "Main");
    const openScreen = (s: Screen, index: number) => {
        targetIndex = index;
        screen = s;
        if (s == "FileUploader") {
            resetUploadSetting(index);
        }
    };

    //////////////////////////////////////
    // Main screen
    //////////////////////////////////////
    const iconAction = async (index: number) => {
        const slot = slots[index];
        if (!slot || !slot.name || slot.name.length == 0) {
            return;
        }
        const file = await fileSelector("");
        if (!checkExtention(file.name, ["png", "jpg", "jpeg", "gif"])) {
            toast.error(`Thumbnail extension should be ".png", ".jpg", ".jpeg" or ".gif".`);
            return;
        }
        await serverState.uploadAssets(index, "iconFile", file);
    };

    const nameValueAction = async (index: number) => {
        const slot = slots[index];
        if (!slot || !slot.name || slot.name.length == 0) {
            return;
        }
        const text = await guiState.requestTextInput();
        if (text.length > 0) {
            await serverState.updateModelInfo(index, "name", text);
        }
    };

    const fileValueAction = (url: string) => {
        if (url.length == 0) {
            return;
        }
        downloadFile("./" + url, basename(url));
    };

    //////////////////////////////////////
    // Sample downloader screen
    //////////////////////////////////////
    let sampleLang = $state("All");

    let sampleModels = $derived(serverState.serverSetting.sampleModels || []);
    let sampleLangs = $derived(["All", ...new Set(sampleModels.map((x) => x.lang))]);
    let filteredSamples = $derived(sampleLang == "All" ? sampleModels : sampleModels.filter((x) => x.lang == sampleLang));

    const downloadSample = async (sampleId: string) => {
        guiState.showWaitingDialog = true;
        try {
            await serverState.uploadModel({
                voiceChangerType: VoiceChangerType.RVC,
                slot: targetIndex,
                isSampleMode: true,
                sampleId,
                files: [],
                params: { useIndex: true },
            });
        } catch (e) {
            toast.error(String(e));
        } finally {
            guiState.showWaitingDialog = false;
            backToSlotManager();
        }
    };

    //////////////////////////////////////
    // File uploader screen
    //////////////////////////////////////
    let uploadSetting = $state<ModelUploadSetting | undefined>(undefined);
    let uploadVoiceChangerType = $state<string>("RVC");

    const resetUploadSetting = (slot: number, type: string = uploadVoiceChangerType) => {
        uploadVoiceChangerType = type;
        uploadSetting = {
            voiceChangerType: type as VoiceChangerType,
            slot,
            isSampleMode: false,
            sampleId: null,
            files: [],
            params: {},
        };
    };

    const onUploadTypeChanged = (e: Event) => {
        resetUploadSetting(targetIndex, (e.currentTarget as HTMLSelectElement).value);
    };

    const fileKindExtensions: Record<ModelFileKind, string[]> = {
        rvcModel: ["pth", "onnx", "safetensors"],
        rvcIndex: ["index", "bin"],
    };

    const selectUploadFile = async (kind: ModelFileKind) => {
        if (!uploadSetting) {
            return;
        }
        const file = await fileSelector("");
        const exts = fileKindExtensions[kind];
        if (!checkExtention(file.name, exts)) {
            toast.error(`${getMessage("ModelSlotManager", "alert_extention")} ${exts.join(", ")}`);
            return;
        }
        uploadSetting.files = [...uploadSetting.files.filter((x) => x.kind != kind), { kind, file, dir: "" }];
        uploadSetting = { ...uploadSetting };
    };

    const uploadModelFiles = async () => {
        if (!uploadSetting || serverState.uploadProgress != 0) {
            return;
        }
        const hasModel = uploadSetting.files.some((x) => x.kind == ModelFileKindEnum.rvcModel);
        if (!hasModel) {
            toast.error(getMessage("ModelSlotManager", "alert_model_file"));
            return;
        }
        guiState.showWaitingDialog = true;
        try {
            await serverState.uploadModel(uploadSetting);
        } catch (e) {
            toast.error(String(e));
        } finally {
            guiState.showWaitingDialog = false;
            backToSlotManager();
        }
    };

    //////////////////////////////////////
    // Editor screen
    //////////////////////////////////////
    let editorTargetId = $state<string>("0");
    let editorTargetName = $state("");

    let editorSlot = $derived(slots[targetIndex] as RVCModelSlot | undefined);
    $effect(() => {
        if (editorSlot) {
            editorTargetName = editorSlot.speakers?.[Number(editorTargetId)] ?? "";
        }
    });

    const setSpeaker = async () => {
        if (!editorSlot) {
            return;
        }
        const inputElem = document.getElementById("edit-model-slot-speakers-name-input") as HTMLInputElement | null;
        if (!inputElem) {
            return;
        }
        const speakers = { ...editorSlot.speakers, [Number(editorTargetId)]: inputElem.value };
        await serverState.updateModelInfo(targetIndex, "speakers", JSON.stringify(speakers));
    };

    const deleteSpeaker = async () => {
        if (!editorSlot) {
            return;
        }
        const speakers = { ...editorSlot.speakers };
        delete speakers[Number(editorTargetId)];
        await serverState.updateModelInfo(targetIndex, "speakers", JSON.stringify(speakers));
    };
</script>

<Dialog title="Model Slot Configuration" open={guiState.showModelSlotManagerDialog} width="max-w-4xl" onClose={close}>
    {#if screen == "Main"}
        <div class="flex flex-col gap-3">
            {#each slots as slot, index (slot.slotIndex)}
                {@const rvc = slot.voiceChangerType == "RVC" ? (slot as RVCModelSlot) : null}
                <div class="flex items-center gap-4 rounded-xl border border-white/[0.07] bg-black/20 p-3">
                    <button class="group relative h-16 w-16 shrink-0 overflow-hidden rounded-lg" onclick={() => iconAction(index)} title={getMessage("ModelSlotManager", "change_icon")}>
                        {#if slot.iconFile}
                            <img src={serverState.serverSetting.voiceChangerParams.model_dir + "/" + slot.slotIndex + "/" + basename(slot.iconFile)} alt={slot.name} class="h-full w-full object-cover opacity-80" />
                        {:else}
                            <img src={MODEL_ICON_BLANK_URL} alt={slot.name} class="h-full w-full object-cover opacity-80" />
                        {/if}
                    </button>
                    <div class="min-w-0 flex-1 text-sm">
                        <div class="flex items-baseline gap-2">
                            <span class="shrink-0 font-mono text-xs text-slate-500">[{slot.slotIndex}]</span>
                            {#if slot.name.length > 0}
                                <button class="truncate text-slate-100 underline decoration-dotted decoration-slate-600 underline-offset-4 hover:text-white" onclick={() => nameValueAction(index)} title={getMessage("ModelSlotManager", "rename")}>
                                    {slot.name}
                                </button>
                                {#if slot.termsOfUseUrl}
                                    <a class="shrink-0 text-xs text-accent-300" href={slot.termsOfUseUrl} target="_blank" rel="noopener noreferrer">[{getMessage("ModelSlotManager", "terms_of_use")}]</a>
                                {/if}
                            {:else}
                                <span class="text-slate-600">blank</span>
                            {/if}
                        </div>
                        {#if rvc}
                            <div class="mt-0.5 flex flex-col text-xs text-slate-400">
                                <button class="w-fit text-left hover:text-accent-300" disabled={!rvc.modelFile} onclick={() => fileValueAction(rvc.modelFile)}>
                                    model: {trimfileName(rvc.modelFile, 40)}
                                </button>
                                <button class="w-fit text-left hover:text-accent-300" disabled={!rvc.indexFile} onclick={() => fileValueAction(rvc.indexFile)}>
                                    index: {trimfileName(rvc.indexFile, 40)}
                                </button>
                                <span class="truncate text-slate-500">
                                    info: {rvc.f0 ? "f0" : "nof0"}, {rvc.samplingRate}, {rvc.embChannels}, {rvc.modelType}, {rvc.defaultTune}, {rvc.defaultFormantShift}, {rvc.defaultIndexRatio}, {rvc.defaultProtect}
                                </span>
                            </div>
                        {/if}
                    </div>
                    <div class="flex shrink-0 flex-col gap-1.5">
                        <button class="btn" onclick={() => openScreen("FileUploader", index)}>
                            <Icon name="upload" size={13} />
                            {getMessage("ModelSlotManager", "upload")}
                        </button>
                        <button class="btn" onclick={() => openScreen("SampleDownloader", index)}>
                            <Icon name="download" size={13} />
                            {getMessage("ModelSlotManager", "sample")}
                        </button>
                        <button class="btn" onclick={() => openScreen("Editor", index)}>
                            <Icon name="pencil" size={13} />
                            {getMessage("ModelSlotManager", "edit")}
                        </button>
                    </div>
                </div>
            {/each}
            <div class="flex justify-center pt-1">
                <button class="btn px-8" onclick={close}>close</button>
            </div>
        </div>
    {:else if screen == "SampleDownloader"}
        <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2">
                <div class="text-sm text-slate-300">
                    {getMessage("ModelSlotManager", "header_message")}
                    <span class="font-mono text-accent-300">Slot[{targetIndex}]</span>
                </div>
                <button class="btn" onclick={backToSlotManager}>&lt;&lt;back</button>
            </div>
            <div class="flex items-center gap-2">
                <span class="control-label">lang</span>
                <select class="field w-40" bind:value={sampleLang}>
                    {#each sampleLangs as lang (lang)}
                        <option value={lang}>{lang}</option>
                    {/each}
                </select>
            </div>
            <div class="flex max-h-[50vh] flex-col gap-3 overflow-y-auto pr-1">
                {#each filteredSamples as sample (sample.id)}
                    <div class="flex items-center gap-4 rounded-xl border border-white/[0.07] bg-black/20 p-3">
                        <img src={sample.icon} alt={sample.name} class="h-16 w-16 shrink-0 rounded-lg object-cover opacity-80" />
                        <div class="min-w-0 flex-1 text-sm">
                            <div class="truncate text-slate-100">{sample.name}</div>
                            <div class="text-xs text-slate-400">VC Type: {sample.voiceChangerType}</div>
                            <div class="truncate text-xs text-slate-500">
                                {#if sample.voiceChangerType == "RVC"}
                                    type:{sample.modelType}, f0:{sample.f0 ? "f0" : "nof0"}, sr:{sample.sampleRate}
                                {/if}
                            </div>
                            {#if sample.termsOfUseUrl}
                                <a class="text-xs text-accent-300" href={sample.termsOfUseUrl} target="_blank" rel="noopener noreferrer">[{getMessage("ModelSlotManager", "terms_of_use")}]</a>
                            {/if}
                        </div>
                        <button class="btn btn-accent shrink-0" onclick={() => downloadSample(sample.id)}>
                            <Icon name="download" size={13} />
                            {getMessage("ModelSlotManager", "download")}
                        </button>
                    </div>
                {/each}
            </div>
        </div>
    {:else if screen == "FileUploader"}
        <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2">
                <div class="text-sm text-slate-300">
                    Upload Files for
                    <span class="font-mono text-accent-300">Slot[{targetIndex}]</span>
                </div>
                <button class="btn" onclick={backToSlotManager}>&lt;&lt;back</button>
            </div>
            <div class="flex items-center gap-3">
                <span class="control-label">VoiceChangerType</span>
                <select class="field w-40" value={uploadVoiceChangerType} onchange={onUploadTypeChanged}>
                    {#each Object.values(VoiceChangerType) as t (t)}
                        <option value={t}>{t}</option>
                    {/each}
                </select>
            </div>
            {#if uploadVoiceChangerType == "RVC"}
                {#each [["Model", "rvcModel"], ["Index", "rvcIndex"]] as [label, kind] (kind)}
                    <div class="flex items-center gap-3">
                        <span class="control-label w-16 shrink-0 text-right">{label}</span>
                        <span class="min-w-0 flex-1 truncate text-sm text-slate-300">
                            {uploadSetting?.files.find((x) => x.kind == kind)?.file ? trimfileName(uploadSetting.files.find((x) => x.kind == kind)!.file.name, 30) : "-"}
                        </span>
                        <button class="btn" onclick={() => selectUploadFile(kind as ModelFileKind)}>select file</button>
                    </div>
                {/each}
            {/if}
            <div class="flex flex-col items-center gap-2 pt-2">
                <button class="btn btn-accent px-10" disabled={serverState.uploadProgress != 0} onclick={uploadModelFiles}>
                    {serverState.uploadProgress == 0 ? "upload" : `uploading(${serverState.uploadProgress.toFixed(1)}%)`}
                </button>
                {#if serverState.uploadProgress != 0}
                    <div class="h-1.5 w-64 overflow-hidden rounded-full bg-white/10">
                        <div class="h-full rounded-full bg-accent-400 transition-all" style={`width: ${serverState.uploadProgress}%`}></div>
                    </div>
                {/if}
            </div>
        </div>
    {:else if screen == "Editor"}
        <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2">
                <div class="text-sm text-slate-300">
                    Edit
                    <span class="font-mono text-accent-300">Slot[{targetIndex}]</span>
                </div>
                <button class="btn" onclick={backToSlotManager}>&lt;&lt;back</button>
            </div>
            {#if editorSlot}
                <div class="flex items-center gap-3">
                    <span class="control-label">{getMessage("ModelSlotManager", "speaker_id")}</span>
                    <span class="control-label">ID:</span>
                    <select class="field w-24" bind:value={editorTargetId}>
                        {#each Array(127) as _, id (id)}
                            <option value={String(id)}>{id}</option>
                        {/each}
                    </select>
                    <span class="control-label">Name:</span>
                    <input id="edit-model-slot-speakers-name-input" class="field flex-1" type="text" bind:value={editorTargetName} />
                    <button class="btn btn-accent" onclick={setSpeaker}>set</button>
                    <button class="btn" onclick={deleteSpeaker}>del</button>
                </div>
                <div class="text-xs text-slate-500">
                    Current speakers: {Object.entries(editorSlot.speakers || {}).map(([k, v]) => `${k}:${v}`).join(", ") || "none"}
                </div>
            {:else}
                <div class="py-6 text-center text-sm text-slate-500">Slot not found.</div>
            {/if}
        </div>
    {/if}
</Dialog>
