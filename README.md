# Vocalis AI

**AI-powered realtime voice changer mod** — low-latency, real-time voice conversion for streaming, gaming and content creation.

## Table of Contents

- [Overview](#overview)
- [Supported operated systems](#supported-operated-systems)
- [System requirements](#system-requirements)
  - [For CPU-only voice conversion](#for-cpu-only-voice-conversion)
  - [For GPU voice conversion](#for-gpu-voice-conversion)
- [Known issues](#known-issues)
  - [General](#general)
  - [DirectML (dml) version](#directml-dml-version)
  - [Nvidia version](#nvidia-version)
  - [All versions](#all-versions)
- [How to use](#how-to-use)
  - [Running locally on Windows](#running-locally-on-windows)
    - [Before you start](#before-you-start)
    - [Check your hardware](#check-your-hardware)
    - [For AMD/Intel/CPU users](#for-amdintelcpu-users)
    - [For Nvidia users](#for-nvidia-users)
    - [Running the voice changer](#running-the-voice-changer)
  - [Running locally on macOS](#running-locally-on-macos)
    - [For Apple Silicon (Apple M1, etc.) users](#for-apple-silicon-apple-m1-etc-users)
    - [For Intel users](#for-intel-users)
    - [Removing Apple quarantine attribute](#removing-apple-quarantine-attribute)
    - [Running the voice changer](#running-the-voice-changer-1)
  - [Running on Colab/Kaggle](#running-on-colabkaggle)
- [Troubleshooting](#troubleshooting)
  - [Exceptions.PretrainDownloadException: 'Failed to download weight.'](#exceptionspretraindownloadexception-failed-to-download-weight)
  - [Audio devices are not displayed](#audio-devices-are-not-displayed)
  - [No sound after start](#no-sound-after-start)
  - [Hearing non-converted voice](#hearing-non-converted-voice)
  - [Hearing audio crackles](#hearing-audio-crackles)
  - [Audio is stuttery](#audio-is-stuttery)
- [Contribution](#contribution)
- [Working with the source](#working-with-the-source)
  - [Prerequisites](#prerequisites)
  - [Setting up the environment](#setting-up-the-environment)
  - [Running the server](#running-the-server)
  - [Building a package](#building-a-package)

## Overview

Vocalis AI is an AI-powered realtime voice changer based on [w-okada voice changer](https://github.com/w-okada/voice-changer) and its [deiteris fork](https://github.com/deiteris/voice-changer) that performs real-time voice conversion
using various voice conversion algorithms.

> [!IMPORTANT]
> This version works only with Retrieval-based Voice Conversion (RVC).

Vocalis AI aims to improve the overall performance for any backend, and at the same time introducing new features and improving
user experience.

The following videos demonstrate how the voice changer works and performs with AMD graphics cards (including integrated GPU!):

[Amd iGPU.webm](https://github.com/deiteris/voice-changer/assets/6103913/67354d4e-51aa-425c-bd23-d33ad2baf824)

[Amd Dgpu Rx6600m.webm](https://github.com/deiteris/voice-changer/assets/6103913/b932296c-36e4-4150-9306-e80b5c7e4afb)

And this one demonstrates how the voice changer works and performs with Nvidia GeForce GTX 1650 laptop:

[Nvidia Dgpu Gtx 1650.webm](https://github.com/deiteris/voice-changer/assets/6103913/3985e6f3-c22d-4899-ad93-057c599b8b53)

## Supported operated systems

* Windows 10 or later.
* Linux.
* macOS 12 Monterey or later. With Apple Silicon or Intel CPU.

## System requirements

> [!IMPORTANT]
> Minimum requirement means that you will be able to run **ONLY** the voice changer. Voice conversion and gaming at the same time will not provide satisfying experience with minimum requirements in most cases.

RAM: at least 6GB.

Disk space: at least 6GB of free disk space. For fast model loading, SSD is recommended.

### For CPU-only voice conversion

Minimum requirement: Intel Core i5-4690K or AMD FX-6300.

Recommended requirement: Intel Core i5-10400F or AMD Ryzen 5 1600X.

### For GPU voice conversion

Minimum VRAM required: 2GB (in FP32 mode), ~1GB (in FP16 mode, if supported).

Minimum requirement:

* An integrated graphics card: AMD Radeon Vega 7 (with AMD Ryzen 5 5600G) or later.
* A dedicated graphics card: Nvidia GeForce GTX 16 Series or RTX 20 Series or later, or AMD Radeon RX 400 series or later, or Intel Arc A300 series or later.

> [!NOTE]
> Nvidia GTX 900/1000 series and older GPUs are supported only by the DirectML version.

> [!WARNING]
> The voice changer does not perform well with integrated Intel GPUs. This is a known issue that may be addressed in the future. You may proceed at your own risk and report issues or successful usage.

Recommended requirement:

A dedicated graphics card Nvidia GeForce RTX 20 Series or later, or AMD Radeon RX 6000 series or later, or Intel Arc A500 series or later.

## Known issues

### General

* Mozilla Firefox ESR may not display audio devices.

### DirectML (dml) version

* When changing **Chunk**, **Extra** or **Crossfade size** settings, you must switch device to CPU then back to your GPU.
  Otherwise, performance issues can be observed.

* Only `rmvpe_onnx`, `fcpe_onnx`, `crepe_tiny_onnx` and `crepe_full_onnx` are available in the list of **F0 Det.**.

* When using a laptop with integrated GPU and dedicated GPU, severely degraded performance (up to 50% reduction) can be observed when running the voice changer on built-in display.

* Slightly degraded performance (up to 25% reduction) can be observed with multi-GPU setups.

* AMD Radeon RX 7000 series may be unable to achieve low latency (below 256ms).

### Nvidia version

* When starting voice conversion for the first time, it may take up to 5-7 seconds to start outputting the converted voice.

### All versions

* Only "perf" metric is reported in server audio mode with `rest` protocol.

## How to use

### Running locally on Windows

#### Before you start

1. [If not installed] Download and install [7-Zip](https://www.7-zip.org/) or [WinRAR](https://www.win-rar.com/download.html).

1. [If not installed] Download and install [VAC Lite by Muzychenko](https://software.muzychenko.net/freeware/vac470lite.zip).

1. Navigate to the [releases section](https://github.com/CyrixJD115/vocalis-ai/releases).

#### Check your hardware

1. Open **Task Manager** > **Performance**.

1. Click **CPU**, check and note the processor model on the right. An example: AMD Ryzen 7 5800H with Radeon Graphics.

1. Check and note graphics card models under **GPU**. An example:

   * GPU 0: AMD Radeon RX 6600M.

   * GPU 1: AMD Radeon(TM) Graphics.

#### For AMD/Intel/CPU users

> [!TIP]
> For AMD users, the recommended driver version is `24.6.1` or later.

1. Download the `voice-changer-windows-amd64-dml.zip` ZIP file.

1. Right-click the ZIP file. In the opened action menu select **7-Zip** > **Extract to "voice-changer-windows-amd64-dml\\"**.

#### For Nvidia users

1. Make sure your Nvidia driver version is `570.26` or later (required by the CUDA 12.8 build). [Click here](https://www.nvidia.com/en-gb/drivers/drivers-faq) to learn how to check your driver version.

   > [!NOTE]
   > The Nvidia build covers GTX 16 / RTX 20 series and later, including RTX 50 (Blackwell). Owners of GTX 900/1000 series GPUs should use the DirectML (dml) build instead.

1. Download the `voice-changer-windows-amd64-cuda.zip.001` and `voice-changer-windows-amd64-cuda.zip.002` ZIP files and place them in the same folder.

1. Right-click the `voice-changer-windows-amd64-cuda.zip.001` ZIP file. In the opened action menu select **7-Zip** > **Extract to "voice-changer-windows-amd64-cuda\\"**. This will unpack **both** files, no need to unpack them separately.

The following examples demonstrate the unpacking process:

* 7-Zip.
  ![unzip_cuda](https://github.com/deiteris/voice-changer/assets/6103913/f33ebb39-b527-462e-bd0c-6007d26aba35)
* WinRAR.
  ![unzip_cuda_winrar](https://github.com/deiteris/voice-changer/assets/6103913/1f8d63db-01b6-427f-9ee9-c674a61d0ecf)

#### Running the voice changer

1. Open the extracted folder (`voice-changer-windows-amd64-dml` or `voice-changer-windows-amd64-cuda`) > `MMVCServerSIO`.

1. Run `MMVCServerSIO.exe`.

When running the voice changer for the first time, it will start downloading necessary files. Do not close the window until the download finishes.

Once the download is finished, the voice changer will open the user interface using your default web browser.

### Running locally on macOS

> [!IMPORTANT]
> macOS support is experimental.

#### For Apple Silicon (Apple M1, etc.) users

1. Download the `voice-changer-macos-arm64-cpu.tar.gz` file.

1. Double-click the file. The voice changer will unpack and the `MMVCServerSIO` folder will appear.

#### For Intel users

> [!NOTE]
> The voice changer would work best if your Intel-based machine has AMD graphics. If your machine has only Intel integrated graphics, only CPU will be utilized.

1. Download the `voice-changer-macos-amd64-cpu.tar.gz` file.

1. Double-click the file. The voice changer will unpack and the `MMVCServerSIO` folder will appear.

#### Removing Apple quarantine attribute

> [!WARNING]
> Currently, this step is mandatory. Otherwise, the voice changer will fail to start with an error related to **Python.framework** being damaged. This may be improved in the future.

1. Open Terminal.

1. Run the following command:

   ```
   xattr -dr com.apple.quarantine <Path to extracted MMVCServerSIO folder>
   ```

   For example, if you extracted the voice changer to your desktop, the command may look as follows:

   ```
   xattr -dr com.apple.quarantine ~/Desktop/MMVCServerSIO
   ```

#### Running the voice changer

1. Open the extracted `MMVCServerSIO` folder.

1. Double-click `MMVCServerSIO` to run the voice changer.

### Running on Colab/Kaggle

Refer to corresponding [Colab](https://github.com/CyrixJD115/vocalis-ai/blob/HEAD/Colab_RealtimeVoiceChanger.ipynb) or [Kaggle](https://github.com/CyrixJD115/vocalis-ai/blob/HEAD/Kaggle_RealtimeVoiceChanger.ipynb) notebooks in this repository and follow their instructions.

## Troubleshooting

> [!TIP]
> When any issue with the voice changer occurs, check the command line window (the one that opens during the start) for errors.

### Exceptions.PretrainDownloadException: 'Failed to download weight.'

Either the remote files have changed or your files were corrupted. The error will show which files are affected above the error:

```
[WeightDownloader] 'pretrain/content_vec_500.onnx failed to pass hash verification check. Got 1931e237626b80d65ae44cbacd4a5197, expected ab288ca5b540a4a15909a40edf875d1e'
[WeightDownloader] 'pretrain/rmvpe.onnx failed to pass hash verification check. Got 65030149d579a65f15aa7e85769c32f1, expected b6979bf69503f8ec48c135000028a7b0'
```

Find and delete the mentioned files from the voice changer folder and restart the voice changer. Deleted files will be re-downloaded.

### Audio devices are not displayed

1. Make sure that you have given the permission to access the microphone.

1. If you are using Mozilla Firefox ESR, there may be an issue with audio devices. Use other web browser (preferably Chrome or Chromium-based).

### No sound after start

1. Make sure you have selected correct input and output audio devices.

1. Make sure your input device is not muted. Check the microphone volume in the system settings or hardware switch on your headset (usually a button, if present).

### Hearing non-converted voice

In the voice changer, make sure **passthru** is not on (indicated by blinking red color). Click it to switch it off (indicated by solid green color).

![unpassthru](https://github.com/user-attachments/assets/014fd740-d8cb-48f6-8b5c-d53258a34b95)

### Hearing audio crackles

1. Make sure you are using **VAC by Muzychenko** (indicated by the **Line 1** audio device name).

1. In Windows **Sound Control Panel**, make sure that the sample rate of your microphone matches the sample rate of the virtual cable.

   The following example shows the configuration of the virtual cable and the microphone:

   ![image](https://github.com/user-attachments/assets/bd19dcbe-87a8-4e0a-9d3d-baf8015c546c)

   ![image](https://github.com/user-attachments/assets/0e7ae533-3ba5-4308-895e-54254c2a67e0)

1. If nothing helped, in **Task Manager** > **Details**, find "audiodg.exe" process and do the folowing:

   1. Right-click "audiodg.exe" > **Set priority** > **High**.
  
   1. Right-click "audiodg.exe" > **Set affinity**. Uncheck every option, then only select CPU 2.

### Audio is stuttery

1. If you changed chunk when voice conversion was on, click **Stop** then **Start** again.

1. Make sure the **perf** time is smaller than **Chunk**. Increase **Chunk** or reduce **Extra** and **Crossfade size**.

## Contribution

At the moment, the fork does not accept any code contributions. However, feel free to report any issues
you encounter during usage.

## Working with the source

### Prerequisites

1. [If not installed] Download and install [Python 3.10](https://www.python.org/downloads/release/python-3108/). Any version from 3.10 to 3.12 works; 3.10 is required for the `rocm` backend and recommended overall.

1. [If not installed] Download and install git.

1. Open a command line.

1. Verify your Python version by running the following command:

   ```
   python --version
   Python 3.10.8
   ```

1. Clone the repository.

1. Navigate to the `server` folder.

### Quick start with start.py (recommended)

The launcher creates a virtual environment (`.venv`), installs the dependencies for the selected backend — using [uv](https://docs.astral.sh/uv/) when available for a much faster setup — and starts the server:

```
python start.py
```

The compute backend is auto-detected (Nvidia GPU -> `cuda`, other Windows GPUs -> `dml`, macOS -> `cpu`, AMD GPU on Linux -> `rocm`). Useful flags:

| Flag | Description |
|------|-------------|
| `--backend cuda\|dml\|rocm\|cpu` | Force a specific backend instead of auto-detecting. |
| `--host 0.0.0.0` | Allow connections from other devices on your network (self-signed HTTPS is enabled automatically). |
| `--port 18888` | Change the listening port. |
| `--no-browser` | Do not open the UI in the browser automatically. |
| `--skip-deps` | Skip the dependency check (fast restart). |
| `--reinstall` | Delete `.venv` and reinstall from scratch. |
| `--no-start` | Only set up the environment, do not start the server. |
| `-- <main.py args>` | Forward flags to the server, e.g. `-- --log-level info`. |

### Setting up the environment manually

If you prefer to manage the environment yourself, use one of the following methods.

#### With uv

The project ships a `pyproject.toml` with one extra per backend (`cuda`, `dml`, `rocm`, `cpu` — install exactly one):

```
uv sync --extra cuda
uv run python main.py
```

> [!WARNING]
> Prefer `python start.py` for day-to-day use. A plain `uv run` re-syncs the environment to the base dependencies before executing and can replace backend-specific packages (for example, swapping CUDA torch for the CPU build). If you use `uv run`, pass `--no-sync` (e.g. `uv run --no-sync python start.py`) or select the extra explicitly (`uv run --extra cuda python main.py`).

> [!NOTE]
> The `rocm` extra does not include `onnxruntime-rocm`: AMD ships it as a direct wheel URL which uv's lockfile cannot resolve across Python versions. Use `start.py` or the requirements file below, which handle it correctly.

Alternatively, install straight from the requirements files (the single source of truth, and the only path that covers every backend):

```
uv venv
uv pip install -r requirements-common.txt -r requirements-cuda.txt
uv run main.py
```

#### With plain venv + pip

1. [If not set up] Set up virtual environment with the following command:

   ```
   python -m venv venv
   ```

1. Activate virtual environment using one of the following commands:

   * For Windows:

     ```
     .\venv\Scripts\activate.ps1
     ```

   * For Linux/macOS:

     ```
     source ./venv/bin/activate
     ```

1. Install the requirements using one of the following commands:

   * For AMD/Intel/CPU (Windows only):

     ```
     pip install -r requirements-common.txt -r requirements-dml.txt
     ```

   * For Nvidia (any OS):

     ```
     pip install -r requirements-common.txt -r requirements-cuda.txt
     ```

   * For AMD ROCm (Linux only):

     ```
     pip install -r requirements-common.txt -r requirements-rocm.txt
     ```

   * For CPU (Linux/macOS only):

     ```
     pip install -r requirements-common.txt -r requirements-cpu.txt
     ```

### Running the server

Run the server by executing `main.py`.

```
python ./main.py
```

This will run the server with default settings. Note that it will not open the web browser by default, copy the address from command line.

The server behavior can be configured with environment variables (or a `.env` file next to `main.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Bind address. Set to `0.0.0.0` to allow connections from other devices on your network. |
| `PORT` | `18888` | Listening port. |
| `SAMPLE_MODE` | `production` | Source of sample models for the **DL Sample** dialog. Set to empty (`''`) to disable. |
| `MODEL_DIR` | `model_dir` | Directory where model slots are stored. |

For example, to make the voice changer accessible on the local network:

```
HOST=0.0.0.0 python ./main.py --https true
```

> [!WARNING]
> When exposing the server to a network, keep `--https true` so that browsers allow microphone access on remote devices.

### Model management API

The server exposes a small REST API for managing RVC models programmatically (the web UI uses its own endpoints; these are the script-friendly ones):

| Method & path | Description |
|---------------|-------------|
| `GET /api/models` | List installed models and the currently selected slot. |
| `POST /api/models` | Upload and add a model. Accepts a `.zip` archive or loose files: one `.pth`/`.onnx`/`.safetensors` model (required), an optional `.index` feature file, and an optional icon image. |
| `DELETE /api/models/{slot}` | Remove a model (deselects it first if active). |

`POST /api/models` parameters (multipart form):

| Field | Description |
|-------|-------------|
| `file` | One or more files. A `.zip` is unpacked server-side and classified automatically. |
| `slot` | Target slot number. Omit or pass `-1` to use the first free slot. |
| `name` | Optional display name (defaults to the model file name). |
| `activate` | `true` to select the model immediately (it is warmed up in the background, so conversion starts without delay). |

Examples:

```bash
# Add a model from a zip into the first free slot and start using it
curl -X POST http://127.0.0.1:18888/api/models \
    -F "file=@MyModelRVC.zip" -F "name=MyModel" -F "activate=true"

# List models
curl http://127.0.0.1:18888/api/models

# Remove the model in slot 4
curl -X DELETE http://127.0.0.1:18888/api/models/4
```

Other useful endpoints: `POST /update_settings` (form fields `key`/`val`, e.g. `key=modelSlotIndex&val=4`, `key=tran&val=12`) and `POST /test` (msgpack-encoded `[timestamp, int16 PCM]` body — returns converted audio; used for offline conversion).

### Web UI development

The web UI lives in `client/demo` and is built with Svelte 5, Vite and Tailwind CSS v4. It reuses the shared TypeScript client (`client/lib`, aliased as `@vc-lib/*`); the audio-worklet processor is bundled with esbuild at build time, so the lib's webpack toolchain is not needed.

The launcher can drive the whole stack by itself:

```
python start.py                  # backend on :18888, serves the pre-built UI from client/demo/dist
python start.py --dev-ui         # all-in-one: backend + Svelte/Vite dev server on :5173 with hot reload,
                                 # browser opens the dev server; API/Socket.IO are proxied to the backend
                                 # (--ui-port to change the Vite port, requires Node.js)
python start.py --build-ui       # (re)build client/demo/dist before starting (needs Node.js)
```

If `client/demo/dist` is missing and Node.js is installed, `start.py` builds the UI automatically; with `--dev-ui` the Vite server starts instead and installs the UI dependencies on first run. Both modes tear the dev server down together with the backend on Ctrl+C.

For manual UI work:

```
cd client/demo
npm install
npm run dev        # dev server on :5173, API/Socket.IO proxied to http://127.0.0.1:18888 (override with VC_SERVER_URL)
npm run build      # production build into client/demo/dist (the directory served by the python server)
npm run check      # svelte-check typechecking
```

To work on the UI without the python backend, use the mock server (canned `/info`, `/version`, `/edition`, `/update_settings` responses plus the built assets):

```
npm run mock       # serve dist/ with mock data on :8899
npm run shots      # headless-chromium screenshot suite against the mock server (scripts/screenshot.mjs)
```

### Building a package

1. [If not installed] Install `pyinstaller` with the following command:

   ```
   pip install --upgrade pip wheel setuptools pyinstaller
   ```

1. Run the following command to build an executable:

   ```
   pyinstaller --clean -y --dist ./dist --workpath /tmp MMVCServerSIO.spec
   ```

   This will output the resulting executable in the `dist` folder.
