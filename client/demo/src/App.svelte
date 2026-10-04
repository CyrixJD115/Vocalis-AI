<script lang="ts">
    import { onMount } from "svelte";
    import Header from "./components/Header.svelte";
    import ModelSlotArea from "./components/ModelSlotArea.svelte";
    import CharacterPanel from "./components/CharacterPanel.svelte";
    import ConfigPanel from "./components/ConfigPanel.svelte";
    import ToastHost from "./components/ToastHost.svelte";
    import WaitingDialog from "./components/dialogs/WaitingDialog.svelte";
    import StartingNoticeDialog from "./components/dialogs/StartingNoticeDialog.svelte";
    import TextInputDialog from "./components/dialogs/TextInputDialog.svelte";
    import PassThroughDialog from "./components/dialogs/PassThroughDialog.svelte";
    import ServerInfoDialog from "./components/dialogs/ServerInfoDialog.svelte";
    import ClientInfoDialog from "./components/dialogs/ClientInfoDialog.svelte";
    import AdvancedSettingDialog from "./components/dialogs/AdvancedSettingDialog.svelte";
    import MergeLabDialog from "./components/dialogs/MergeLabDialog.svelte";
    import ModelSlotManagerDialog from "./components/dialogs/ModelSlotManagerDialog.svelte";
    import VirtualAudioDialog from "./components/dialogs/VirtualAudioDialog.svelte";
    import { appState } from "./lib/state/appState.svelte";
    import { serverState } from "./lib/state/serverState.svelte";
    import { guiState } from "./lib/state/guiState.svelte";
    import { toast } from "./lib/toast.svelte";

    let slotControl = $derived(appState.appGuiSetting.front.modelSlotControl);
    let headerOptions = $derived(slotControl.find((x) => x.name == "headerArea")?.options || {});
    let configOptions = $derived(slotControl.find((x) => x.name == "configArea")?.options || {});
    let detectors = $derived(
        configOptions.detectors || ["crepe_full_onnx", "crepe_tiny_onnx", "crepe_full", "crepe_tiny", "rmvpe", "rmvpe_onnx", "fcpe", "fcpe_onnx"],
    );

    onMount(async () => {
        guiState.initialize();
        appState.loadAppGuiSetting();
        appState.loadServerMeta();
        try {
            await serverState.reloadServerInfo();
        } catch (e) {
            console.error(e);
            toast.error("Cannot reach the voice changer server. Is the server running?");
        }
    });
</script>

<div class="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-4 p-4 md:p-6">
    <Header mainTitle={headerOptions.mainTitle || "Realtime Voice Changer Client"} subTitle={headerOptions.subTitle || ""} />

    <ModelSlotArea />

    <div class="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <CharacterPanel />
        <ConfigPanel {detectors} />
    </div>

    <footer class="pb-2 text-center text-[11px] text-slate-600">
        Realtime Voice Changer · Svelte UI
    </footer>
</div>

<ToastHost />
<WaitingDialog />
<StartingNoticeDialog />
<TextInputDialog />
<PassThroughDialog />
<ServerInfoDialog />
<ClientInfoDialog />
<AdvancedSettingDialog />
<MergeLabDialog />
<ModelSlotManagerDialog />
<VirtualAudioDialog />
