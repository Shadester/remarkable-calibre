# reMarkable — Calibre Plugin

A Calibre **Device Driver** plugin that makes a reMarkable tablet appear natively in Calibre's device panel — just like a Kindle or Kobo. Upload books, browse your library on the device, download files, and delete books, all without a cloud account or third-party tools.

## Features

| Feature | SSH | USB web |
|---|---|---|
| Browse device library | ✓ | ✓ |
| Upload EPUB / PDF | ✓ | ✓ |
| Download book | ✓ | — |
| Delete book | ✓ | — |
| Real disk space info | ✓ | — |
| Firmware version | ✓ | — |

## Requirements

- Calibre 6+
- reMarkable tablet (rM1, rM2, or Paper Pro)
- USB cable

**For SSH (recommended):** Developer mode must be enabled on the tablet.  
**For USB web:** USB web interface must be enabled (Settings → Storage → USB web interface).

## Installation

1. Download the latest `remarkable.zip` from [Releases](../../releases).
2. In Calibre: **Preferences → Plugins → Load plugin from file** → select `remarkable.zip`.
3. Restart Calibre.
4. Configure the plugin (see below), then connect your tablet via USB.

## Configuration

Go to **Preferences → Plugins → reMarkable → Customize**:

| Setting | Default | Description |
|---|---|---|
| Connection type | SSH | How to communicate with the tablet. |
| Tablet host | `10.11.99.1` | IP address of the tablet over USB. |
| Connection timeout | 2 s | How long to wait when probing. |
| SSH password | _(empty)_ | Required for SSH — see below. |

### SSH (recommended)

SSH gives full access: browse, upload, download, and delete.

1. On the tablet, go to **Settings → Security** and enable **Developer mode**.
2. Find your SSH password under **Settings → Help → Copyrights and licenses** (scroll to the GPL Notice section).
3. Enter the password in the plugin's **SSH password** field.

The plugin connects as `root@10.11.99.1` — the standard reMarkable USB address.

### USB web interface (upload only)

The USB web interface only supports browsing the library and uploading files. Downloading and deleting books require SSH.

1. On the tablet, go to **Settings → Storage** and enable **USB web interface**.
2. Select **USB web interface (upload only)** in the plugin's connection type.
3. No password needed.

## Usage

1. Connect your reMarkable via USB cable.
2. Within a few seconds, **reMarkable** appears in Calibre's device panel.
3. The device panel lists all books currently on the tablet.
4. Select books in the library and click **Send to device** to upload. Calibre automatically converts other formats (AZW3, MOBI, etc.) to EPUB or PDF before uploading.
5. Right-click a book in the device panel to **Delete from device**.
6. Double-click a book in the device panel to **View** (download and open locally).

## Building from Source

```bash
scripts/build.sh
```

Produces `remarkable.zip` in the repo root. Install via Calibre's plugin loader or:

```bash
calibre-customize -a remarkable.zip
```

## Running Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install pytest
pytest tests/
```
