# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ExpVault (Βιβλίο Εκρηκτικών Υλών) — an Electron desktop app for a quarry's legally-mandated
explosives purchase/consumption ledger. Produces the official 2-page landscape PDF (purchases &
returns / consumptions) and auto-imports supplier invoice PDFs (EpsilonNet format). See
`README.md` for the full domain model (tables, movement types, PDF parser format) and
`ΟΔΗΓΟΣ_ΧΡΗΣΗΣ.md` for the user-facing workflow guide — don't duplicate that here.

## Commands

```bash
npm start              # electron .  (dev mode — spawns backend/bridge.py directly via system python)
npm run smoke-test:bridge   # node scripts/smoke-test-bridge.mjs — exercises a built bridge.exe
npm run dist:win       # electron-builder --win (NSIS installer)
npm run dist:linux     # electron-builder --linux (AppImage)
npm run dist:mac       # electron-builder --mac (dmg)
.\build.ps1            # full Windows release build, see "Build pipeline" below
```

There is no lint script and no JS unit test framework. The two verification mechanisms are:
- `scripts/smoke-test-bridge.mjs` — spawns a freshly-built `bridge.exe` against a throwaway fresh
  DB and exercises the commands that have historically broken silently in PyInstaller packaging
  (Greek text round-trip via stdin, every export format). Run it any time `backend/bridge.spec`'s
  PyInstaller excludes change, or after touching `backend/exports.py`.
- The `run-expvault` Claude Code skill (`.claude/skills/run-expvault/driver.mjs`) — drives the real
  Electron app via `playwright-core`'s `_electron`, either `dev` (repo + `backend/expvault.db`) or
  `installed` (the packaged exe at `C:\Program Files\ExpVault`, using the **real** user database at
  `%APPDATA%\expvault\expvault.db`). Use it for any UI-behavior verification instead of guessing
  from source. In `installed` mode, any add/update you do is against real data — clean it up in the
  same session (matching `add_*` calls with `delete_*`).

## Architecture

Three tiers, talking over two different IPC boundaries:

```
index.html + js/*.js (renderer, ES modules)
        │  window.api.call(cmd, payload)   [contextBridge, see preload.js]
        ▼
main.js (Electron main process)
        │  newline-delimited JSON over stdin/stdout
        ▼
backend/bridge.py  →  backend/database.py (sqlite3)  →  expvault.db
```

- **Renderer → main**: `preload.js` exposes a narrow `window.api` surface via `contextBridge`
  (context isolation is on, `nodeIntegration` is off). `js/utils.js`'s `py(cmd, payload)` wraps
  `window.api.call`, which is `ipcRenderer.invoke('python', cmd, payload)`.
- **Main → Python bridge**: `main.js` spawns either `python backend/bridge.py` (dev) or the
  PyInstaller-compiled `resources/bridge/bridge.exe` (packaged, detected via `getBridgeExe()`).
  Requests are `{id, cmd, payload}\n` JSON lines; the bridge replies `{id, result}` or
  `{id, error}\n`. `main.js` keeps a `pendingRequests` map keyed by an incrementing `id` and a
  120s per-request timeout. Messages sent before the bridge's `{ready: true}` handshake are queued
  (`queuedMessages`) and flushed on ready. `backend/bridge.py` dispatches on `cmd` with a flat
  `if cmd == 'x': ...` chain — add new commands there and in the matching `py('x', …)` call site.
- **Data dir resolution**: `bridge.py` always overrides `database.DB_NAME` to an **absolute** path
  built from `EXPVAULT_DATA_DIR` (never relies on CWD). Dev mode: `main.js` sets this to
  `backend/` next to `bridge.py`, so the dev DB is `backend/expvault.db`. Packaged: it's
  `app.getPath('userData')`, i.e. `%APPDATA%\expvault\expvault.db` on Windows.
- **Page routing**: no client-side router — `index.html` has one `.page` div per screen, toggled by
  `.active` class; `onPageLoad(page)` (bottom of `index.html`'s inline `<script type="module">`)
  is the dispatch table that triggers each page's initial data load.

### Gotcha: inline `onclick=""` handlers need manual global exposure

Every JS module here uses `export function …`, but HTML `onclick="foo()"` attributes need `foo` on
`window`. There's a single `Object.assign(window, { … })` block near the bottom of `index.html`
that every such function must be added to (alongside the matching `import`). **This is a real,
recurring bug source**: a function exported and used in an `onclick` but missing from that
`Object.assign` fails silently (`ReferenceError` inside the inline handler, no visible error to the
user — the button just does nothing). When adding a new modal/button with an inline handler, check
both the import list and the `Object.assign` block.

### Gotcha: the shared confirm-modal must be re-armed on every open

`#confirm-modal` / `#confirm-ok-btn` is one shared DOM element used by multiple flows. The generic
`showConfirm(msg, onOk)` / `closeConfirm()` pair (`js/utils.js`) re-binds `confirm-ok-btn.onclick`
fresh on every `showConfirm()` call, and `closeConfirm()` always nulls it out afterward as cleanup.
`js/delete-confirm.js`'s `confirmDelete(type, id)` **must do the same** — bind `onclick` inside
`confirmDelete()` itself, not once at module load — otherwise the delete button works exactly once
per app session and silently does nothing on every subsequent use (`closeConfirm()` already nulled
its handler after the first use, and nothing ever re-binds it). Same pattern applies to any other
modal built around this shared confirm dialog.

## Build pipeline (`build.ps1`)

1. `pip install pyinstaller reportlab openpyxl python-docx`
2. `pyinstaller backend/bridge.spec --clean --noconfirm` → `backend/dist/bridge/bridge.exe`
3. `node scripts/smoke-test-bridge.mjs` against the freshly built exe — aborts the build on failure
4. Copies `backend/dist/bridge` → `dist/bridge` (matches `package.json`'s `extraResources.from`)
5. `npm install` then `npm run dist:win` (electron-builder, NSIS target)

`package.json`'s `build.files` bundles the **entire** `node_modules` into the app (not just prod
deps) — this is why the installer is ~140MB+ and why NSIS packaging/signing is the slowest step of
a build (multiple minutes). `extraResources` copies `dist/bridge` and `assets/fonts` into
`resources/`; `win.extraResources` additionally bundles `assets/rclone/rclone.exe` so Windows users
don't need rclone installed separately for cloud backup.

### Custom NSIS script: `build/installer.nsh`

electron-builder auto-loads `build/installer.nsh` (default location, no `package.json` config
needed) and inserts its `customInstall`/`customUnInstall` macros into the generated installer. This
repo uses it to register the bundled Iosevka font as a real system font — Word/Excel exports need
it installed system-wide to render correctly (unlike the PDF export, which embeds the font file
directly via `backend/exports.py`'s `find_font()`/reportlab, so it needs no OS-level install).

Two non-obvious NSIS constraints, both cost real debugging time to discover:
- `WriteRegStr`/`DeleteRegValue`'s root-key argument must be a **literal** `HKLM`/`HKCU` token — a
  variable holding that string compiles fine for `WriteRegStr` but fails for `DeleteRegValue` with
  a cryptic `Usage: DeleteRegValue root_key subkey entry_name` error. The macros branch on
  `$installMode` ("all" vs "CurrentUser", set by electron-builder's `multiUser.nsh`) and duplicate
  the literal-rootkey calls per branch rather than storing the root key in a variable.
- The `HKLM` (system `C:\Windows\Fonts`) font registry value only needs the bare filename; the
  `HKCU` (per-user `%LOCALAPPDATA%\Microsoft\Windows\Fonts`, since it's outside the default search
  path) value needs the **full path**, or Windows won't resolve the font.
- On a machine that already has a per-machine (`C:\Program Files\...`) install, electron-builder's
  multi-user installer defaults to `$installMode == "all"` on reinstall/update regardless of the
  `perMachine: false` config in `package.json` — that config only governs the choice for a
  genuinely fresh install.

## Auto-update

Two independent, parallel mechanisms — don't assume fixing one covers the other:

- **`electron-updater`** (`main.js`'s `setupAutoUpdater()`): real auto-update via the GitHub
  Releases API (`package.json`'s `build.publish`), `autoDownload: true`,
  `autoInstallOnAppQuit: true`. It always pushes whatever release GitHub reports as "latest",
  full stop — it has no concept of "known bad version".
- **`version-check.js`** (`allowed-versions.json` + the in-app version-history modal,
  `js/version-notice.js`): a rollback-notice layer for "this version has a known issue, here's the
  last safe one" that `electron-updater` can't express. If a release turns out to be broken,
  editing `allowed-versions.json` alone is **not enough** — `electron-updater` will keep installing
  it for anyone not yet updated. You must also mark the GitHub release itself as a pre-release (see
  `RELEASE-CHECKLIST.md` for the full rollback procedure).

`js/version-notice.js`'s `parseVersionsMd()` parses `VERSIONS.md` for the in-app history modal —
each entry's header must match `vX.Y.Z — YYYY-MM-DD` followed by a line of 5+ dashes, exactly the
format already used in the file.

## Release checklist

Full step-by-step in `RELEASE-CHECKLIST.md`. Key trap: `build.ps1` produces installer filenames
with **spaces** (`ExpVault Setup X.Y.Z.exe`), but `latest.yml` (electron-updater's manifest) and
prior GitHub release assets use **hyphens** (`ExpVault-Setup-X.Y.Z.exe`) — rename before uploading
release assets, and verify the actual filename on GitHub before locking in any download URL in
`allowed-versions.json` or `README.md`.
