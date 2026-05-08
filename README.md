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
| Host | `10.11.99.1` | IP of the tablet's USB web interface. Override if you're using an SSH tunnel or custom network setup. |
| Connection timeout | 2 s | How long to wait when probing the device. Increase on slow USB connections. |

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
