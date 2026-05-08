# Send to reMarkable — Calibre Plugin

A Calibre **Device Driver** plugin that makes a USB-tethered reMarkable tablet appear natively in Calibre's device panel — just like a Kindle or Kobo. Books are uploaded via the tablet's built-in USB web interface; no cloud account or third-party tools required.

## Requirements

- Calibre 6+
- reMarkable tablet (rM1, rM2, or Paper Pro) with **USB web interface enabled**  
  (Settings → Storage → USB web interface)
- USB cable connecting the tablet to your computer

## Installation

1. Download the latest `remarkable.zip` from Releases, or build it yourself (see below).
2. In Calibre: **Preferences → Plugins → Load plugin from file** → select `remarkable.zip`.
3. Restart Calibre.

## Usage

1. Connect your reMarkable via USB and enable the USB web interface on the tablet.
2. Within a few seconds, **reMarkable** appears in Calibre's device panel.
3. Select one or more books in the library → **Send to device**.
4. Calibre automatically converts books to EPUB or PDF if needed, then uploads them.

## Supported formats

The plugin tells Calibre it accepts **EPUB** and **PDF**. Calibre converts anything else (AZW3, MOBI, etc.) before uploading — no manual conversion step required.

## Configuration

Go to **Preferences → Plugins → reMarkable → Customize**:

| Setting | Default | Description |
|---------|---------|-------------|
| Connection type | USB web interface | How files are delivered to the tablet (see below). |
| Tablet host | `10.11.99.1` | IP address of the tablet over USB. Override for SSH tunnels or custom network setups. |
| Connection timeout | 2 s | How long to wait when probing the device. Increase on slow connections. |
| SSH password | _(empty)_ | Required when using the SSH backend (see below). |

### Connection types

**USB web interface** (default): Uses the tablet's built-in HTTP upload endpoint. Requires **USB web interface** to be enabled on the tablet (Settings → Storage → USB web interface). No password needed.

**SSH (direct file copy)**: Copies files directly into the tablet's document store over SSH and restarts the viewer. Requires **developer mode** enabled on the tablet. Find the SSH password under **Settings → Help → Copyrights and licenses** (scroll to the GPL Notice section). Requires `paramiko` to be available in Calibre's Python environment.

> **Note:** After switching connection type, reconnect the device (eject and re-plug) for the change to take effect.

## Building from Source

```bash
scripts/build.sh
```

Produces `remarkable.zip` in the repo root. Install it via Calibre's plugin loader or:

```bash
calibre-customize -a remarkable.zip
```

## Running Tests

```bash
python -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest tests/
```

## Roadmap

- v3: reMarkable Cloud API backend (no USB cable required)
- v3: List and delete device books through Calibre
- v3+: Pull annotated PDFs back into Calibre
