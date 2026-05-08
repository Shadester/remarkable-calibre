# CLAUDE.md

## Project

Calibre Device Driver plugin for the reMarkable tablet. Runs inside Calibre's plugin sandbox (Python 3, Qt available). The plugin file Calibre loads is `remarkable.zip`.

## Build & test

```bash
bash scripts/build.sh          # produces remarkable.zip
pipx run pytest tests/         # run tests (no venv needed)
```

Install into Calibre: **Preferences → Plugins → Load plugin from file → remarkable.zip**, then restart Calibre.

## Releasing

```bash
bash scripts/build.sh
gh release create vX.Y.Z remarkable.zip --repo Shadester/remarkable-calibre --title "vX.Y.Z" --notes "Release notes here"
```

## Structure

```
__init__.py          # plugin entry point, re-exports RemarkableDevice
device.py            # DevicePlugin subclass — Calibre interface layer
config.py            # JSONConfig prefs + Qt ConfigWidget
backends/
  base.py            # Backend ABC: check_connection(), upload(), + optional methods
  ssh.py             # SSHBackend  — full CRUD via subprocess ssh/scp
  usb_web.py         # USBWebBackend — browse + upload via HTTP
tests/
  conftest.py        # stubs calibre.* imports so tests run outside Calibre
  test_ssh.py
  test_usb_web.py
  test_device.py
```

## Architecture

`device.py` is a thin Calibre adapter. All real logic lives in backends. `_backend()` instantiates the right backend from prefs on every call — backends are stateless and short-lived.

The `Backend` ABC defines `check_connection()` and `upload()`. Additional capabilities (`list_books`, `download`, `delete`, `get_storage_info`, `get_firmware_version`) are optional — `device.py` gates on `hasattr(backend, method)` so USB web and SSH can differ without subclassing.

## SSH mechanism

Uses system `ssh`/`scp` binaries via `subprocess`. Password is delivered through a temporary `SSH_ASKPASS` script plus `SSH_ASKPASS_REQUIRE=force` (OpenSSH 8.4+, included in macOS Monterey+). All subprocess calls use `stdin=subprocess.DEVNULL` so SSH never blocks waiting on Calibre's inherited stdin. Paramiko was explicitly avoided — it is not reliably available inside Calibre's bundled Python.

## reMarkable file layout

Books live in `/home/root/.local/share/remarkable/xochitl/` as UUID-named file sets:

- `<uuid>.epub` or `<uuid>.pdf` — the book content
- `<uuid>.metadata` — JSON with `visibleName`, `type`, `deleted`, etc.
- `<uuid>.content` — JSON with `fileType`, `pageCount`, etc.

xochitl does not hot-reload; `systemctl --no-block restart xochitl` is run after any write operation. `list_books` iterates `*.metadata` files directly (not `grep -r` which would scan large binary book files and time out).

## USB web API

The reMarkable USB web interface (port 80 at `10.11.99.1`) exposes:

- `GET /documents/` — JSON array of root-level items; recurse into `CollectionType` entries
- `GET /documents/<guid>` — items inside a folder
- `POST /upload` — multipart upload
- `GET /pdf/<guid>` — PDF render (not used — returns converted PDF, not original file)

JSON fields use `ID`, `Type` (`DocumentType` / `CollectionType`), and `VissibleName` (intentional double-s typo from the original reMarkable API).
