# CuteMix — MOTU PCIe-424 with 24i OSC Console

**CuteMix** is a high-performance, studio-grade Qt Python mixing console designed to control a **MOTU PCIe-424** card with an attached **24i** AudioWire audio interface over **Open Sound Control (OSC)** on Windows desktop.

Reverse-engineered from the official MOTU CueMix FX TouchOSC mapping ([`cuemix-control-map.md`](https://github.com/devfrp/Linux-motu-pci-424/blob/main/docs/cuemix-control-map.md)), CuteMix communicates bidirectionally with the MOTU DSP mixer running on Windows.

---

## Key Features

* **Tailored for MOTU PCIe-424 + 24i:**
  * **24 Input Channel Strips:** Pre-configured for the 24 analog line inputs of the 24i AudioWire interface.
  * **Analog Conditioning Section:** Input Trim potentiometers ($0\text{ to }+24\text{ dB}$), $-20\text{ dB}$ Pad toggle, Polarity/Phase invert ($\varnothing$), Stereo pair linking (`ST`), and input mute.
  * **Matrix Mix Bus Sends:** Long-throw faders with calibrated decibel scale ticks ($-\infty\text{ to }+6\text{ dB}$, with $0\text{ dB}$ Unity at $0.78$ travel), bipolar Pan pots with center detent (`L100` .. `C` .. `R100`), Mute (`M`), Solo (`S`), and Gang groups (`G`).
  * **Hardware-Style LED Ladder Meters:** 20+ segment LED bar with green/amber/red zones, smooth peak-hold decay, and latching red Clip indicators (click to reset).
  * **Pinned Master Bus Strip:** Mix Bus selector (Mix 1 to 4/8), Master Fader (anodized red cap), dual L/R peak meters, Master Mute, Studio Talkback & Listenback, and Atten/Dim pot.
  * **Global Solo Active Alert:** Flashes amber when any solo is active across the console; one click clears all solos desk-wide.
* **Multiple Workspace Views:**
  1. **Mix Console:** Full scrollable 24-channel fader desk with bank quick-select buttons (`ALL 24`, `CH 01-08`, `CH 09-16`, `CH 17-24`).
  2. **Inputs Preamp Rack:** Dedicated analog conditioning rack displaying all 24 inputs' trims, pads, phases, and mutes side-by-side.
  3. **Matrix Overview:** High-altitude matrix grid showing send levels and mutes for all 24 inputs across all mix buses simultaneously.
  4. **OSC Monitor & Diagnostics:** Real-time packet inspector showing incoming/outgoing OSC messages, address filtering, traffic statistics, and a manual OSC command injector for testing.
* **Stereo Linking & Gang Groups:**
  * Even/odd channel pairs (e.g. Ch 1 & 2) link faders, mutes, and automatically spread pan hard Left and Right.
  * Channels in the Gang Group (`G`) move together preserving relative level offsets.
* **Snapshots & 30-Level Undo/Redo:**
  * Save and recall complete console scenes as JSON files (`Ctrl+S` / `Ctrl+O`).
  * Includes bundled presets: `default_unity.json` and `tracking_template.json`.
  * Comprehensive Undo (`Ctrl+Z`) and Redo (`Ctrl+Y`) stack.
* **Dual OSC Dialects & Zero-Dependency Engine:**
  * **TouchOSC (CueMix FX Native):** Uses `/bin/fvEB+{B}/fvInCS+{ch}/cdf`, `/in/fvInCS+{ch}/in/trm`, etc. which MOTU CueMix FX understands natively.
  * **Hierarchical Direct:** Uses `/mix/{B}/input/{ch}/volume`, `/input/{ch}/trim`, etc.
  * **Dual Broadcast:** Broadcasts both formats simultaneously.
  * Includes a built-in, pure-Python OSC 1.0 packet encoder and decoder (works out of the box with zero external C libraries).
* **Bonjour / Zeroconf Auto-Discovery:**
  * Automatically advertises as `CuteMix 424 (TouchOSC)` so MOTU CueMix FX discovers it in `Control Surfaces > TouchOSC`.

---

---

## Windows Desktop Setup & Installation

You have two ways to run CuteMix on Windows:

### Option A: Standalone Executable (No Python Required)
1. Download the latest **`CuteMix-Windows-x64.zip`** from [GitHub Releases](https://github.com/samplaman/cutemix/releases).
2. Extract the ZIP anywhere on your system.
3. Run **`CuteMix.exe`**.

*Note: You can also build the standalone `.exe` locally on any Windows machine with Python installed by double-clicking `build_windows.bat`.*

### Option B: Run from Source / Python Environment
1. Make sure **Python 3.9+** is installed on your Windows machine (download from [python.org](https://www.python.org/)).
   *(Check the box **"Add Python to PATH"** during Python setup).*
2. Open the `cutemix` folder and double-click:
   ```cmd
   setup_windows.bat
   ```
   This automatically creates a Python virtual environment and installs `PySide6` and `zeroconf`.
3. Launch via `run.bat` or `python app.py`.

---

### Step 2: Configure MOTU CueMix FX for OSC

1. Launch **CueMix FX** from your Windows Start Menu or System Tray.
2. In the CueMix FX top menu, go to **Control Surfaces > Configure OSC Devices...**
3. Configure the OSC connection:
   * **If using Auto-Discovery (Bonjour):**
     * CuteMix will automatically appear in the list as **`CuteMix 424 (TouchOSC)`**. Click **Add**.
   * **If configuring manually:**
     * **Device Name:** `CuteMix`
     * **IP Address / Host:** `127.0.0.1` *(or your PC's local LAN IP)*
     * **Send Port (CueMix FX Out):** `9000` *(matches CuteMix Listen Port)*
     * **Receive Port (CueMix FX In):** `8000` *(matches CuteMix Target Port)*
4. Go to **Control Surfaces > TouchOSC** and make sure the connection is **checked (enabled)**.

### Step 3: Launch CuteMix

Double-click:
```cmd
run.bat
```
CuteMix will start, bind to UDP port `9000`, and begin communicating with CueMix FX on port `8000`.

---

## OSC Control Mapping Reference

The OSC mapping implemented in CuteMix is based on the official MOTU CueMix FX TouchOSC layout:

| Parameter | CuteMix TouchOSC Address (Native) | Direct Matrix Address | Range / Type |
|---|---|---|---|
| **Channel Send Fader** | `/bin/fvEB+{B}/fvInCS+{ch}/cdf` | `/mix/{B}/input/{ch}/volume` | `float` $0.0 \dots 1.0$ ($0.78 = 0\text{ dB}$) |
| **Channel Send Pan** | `/bin/fvEB+{B}/fvInCS+{ch}/pan` | `/mix/{B}/input/{ch}/pan` | `float` $0.0 \dots 1.0$ ($0.5 = \text{Center}$) |
| **Channel Send Mute** | `/bin/fvEB+{B}/fvInCS+{ch}/mute` | `/mix/{B}/input/{ch}/mute` | `float` $0.0$ or $1.0$ |
| **Channel Send Solo (PFL)**| `/bin/fvEB+{B}/fvInCS+{ch}/solo` | `/mix/{B}/input/{ch}/solo` | `float` $0.0$ or $1.0$ |
| **Input Trim / Gain** | `/in/fvInCS+{ch}/in/trm` | `/input/{ch}/trim` | `float` $0.0 \dots 1.0$ ($0 \dots +24\text{ dB}$) |
| **Input Pad (-20 dB)** | `/in/fvInCS+{ch}/in/pad` | `/input/{ch}/pad` | `float` $0.0$ or $1.0$ |
| **Input Polarity (Phase)** | `/in/fvInCS+{ch}/in/psi` | `/input/{ch}/phase` | `float` $0.0$ or $1.0$ |
| **Input Stereo Link** | `/in/fvInCS+{ch}/in/st` | `/input/{ch}/stereo` | `float` $0.0$ or $1.0$ |
| **Input Mute** | `/in/fvInCS+{ch}/in/mute` | `/input/{ch}/mute` | `float` $0.0$ or $1.0$ |
| **Bus Master Fader** | `/bus/fvEB+{B}/mix/blS` | `/mix/{B}/master/volume` | `float` $0.0 \dots 1.0$ |
| **Bus Master Mute** | `/bus/fvEB+{B}/mix/mute` | `/mix/{B}/master/mute` | `float` $0.0$ or $1.0$ |
| **Meters Stream Toggle** | `/metersToggle` | `/metersToggle` | `float` $1.0 = \text{On}, 0.0 = \text{Off}$ |
| **Meters Data Packet** | `/metersLED` | `/meters` | Multi-channel float array |
| **Talkback Switch** | `/talkback` | `/talk` | `float` $0.0$ or $1.0$ |
| **Listenback Switch** | `/listenback` | `/listen` | `float` $0.0$ or $1.0$ |
| **Atten / Dim Volume** | `/atten` | `/atten` | `float` $0.0 \dots 1.0$ |

*Note: `{B}` is the 0-based mix bus index (`0` for Mix 1, `1` for Mix 2, etc.), and `{ch}` is the 0-based input channel strip index (`0` to `23` for 24i).*

---

## Command Line Arguments

CuteMix can be run with optional command line flags:

```bash
python app.py [OPTIONS]
```

* `--demo`: Launch with synthetic audio meter generator (ideal for testing without a connected PCIe-424 card).
* `--host <IP>`: Override target CueMix FX host IP (e.g. `--host 192.168.1.100`).
* `--target-port <PORT>`: Override send port (default: `8000`).
* `--listen-port <PORT>`: Override listen port (default: `9000`).
* `--dialect <touchosc|direct|both>`: Select OSC address format (default: `touchosc`).

Example:
```bash
python app.py --demo
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Z` | Undo last mixer action |
| `Ctrl+Y` | Redo |
| `Ctrl+S` | Save mixer snapshot to JSON |
| `Ctrl+O` | Load mixer snapshot from JSON |
| `Ctrl+R` | Reset sends on current mix bus to Unity defaults |
| `Ctrl+N` | Reset all console buses to Unity defaults |
| `Ctrl+,` | Open Preferences & OSC Settings dialog |
| `Esc` | Clear all solos console-wide |
| `Alt+1` | Switch to Mix Console |
| `Alt+2` | Switch to Inputs Preamp Rack |
| `Alt+3` | Switch to Matrix Overview |
| `Alt+4` | Switch to OSC Monitor & Diagnostics |
| `Double-Click Fader` | Snap directly to Unity ($0.0\text{ dB}$) |
| `Double-Click Pan` | Snap directly to Center (`C`) |
| `Double-Click Trim` | Snap directly to $0\text{ dB}$ |
| `Shift / Ctrl + Drag` | Fine adjustment mode on faders and knobs |
