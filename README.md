# Send to reMarkable — Calibre Plugin

A Calibre plugin that sends books from your library to a USB-tethered reMarkable tablet via its built-in USB web interface.

## Requirements

- Calibre 6+
- reMarkable tablet with **USB web interface enabled** (Settings → Storage → USB web interface)
- USB cable connecting the tablet to your computer

## Installation

1. Download the latest `remarkable.zip` from Releases, or build it yourself (see below).
2. In Calibre: **Preferences → Plugins → Load plugin from file** → select `remarkable.zip`.
3. Restart Calibre.

A **Send to reMarkable** action appears in the toolbar and under the **Books** menu.

## Usage

1. Select one or more books in Calibre's library view.
2. Click **Send to reMarkable** (or use the menu: **Books → Send to reMarkable**).
3. The plugin will upload the best available format (EPUB preferred, then PDF) for each book.
4. A summary shows which books were sent, which failed, and which were skipped (no supported format found).

## Configuration

Go to **Preferences → Plugins → Send to reMarkable → Customize**:

| Setting | Default | Description |
|---------|---------|-------------|
| Host | `10.11.99.1` | IP of the tablet's USB web interface. |
| Format priority | `EPUB, PDF` | Order of preference when multiple formats exist. |
| On no supported format | Skip | What to do when a book has no EPUB or PDF. |
| Connection timeout | 2 s | How long to wait when checking connectivity. |

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
pytest tests/
```

## Roadmap

- v2: reMarkable Cloud API backend (no USB cable required)
- v2: Custom column "On reMarkable" to track sent books
- v2+: Pull annotated PDFs back into Calibre
