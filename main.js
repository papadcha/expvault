const { app, BrowserWindow, dialog, ipcMain, globalShortcut } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const os = require('os');

const FLASK_PORT = 5000;
let mainWindow = null;
let flaskProcess = null;

// ── Εύρεση Python executable ──────────────────────────────────────────────────
function getPythonPath() {
  // Σε packaged app: χρησιμοποίησε bundled python αν υπάρχει
  const resourcesPath = process.resourcesPath || path.join(__dirname);
  const bundledPython = path.join(resourcesPath, 'backend', 'venv',
    os.platform() === 'win32' ? 'Scripts/python.exe' : 'bin/python'
  );

  const fs = require('fs');
  if (fs.existsSync(bundledPython)) return bundledPython;

  // Fallback: system python
  if (os.platform() === 'win32') return 'python';
  return 'python3';
}

// ── Εύρεση backend path ───────────────────────────────────────────────────────
function getBackendPath() {
  // app.isPackaged είναι true και με system electron — δεν είναι αξιόπιστο
  // Χρησιμοποίησε ELECTRON_DEV env variable ή έλεγξε αν υπάρχει το αρχείο
  const devPath = path.join(__dirname, 'backend');
  const fs = require('fs');
  if (fs.existsSync(path.join(devPath, 'app.py'))) {
    return devPath;  // Development: βρήκε το backend δίπλα στο main.js
  }
  return path.join(process.resourcesPath, 'backend');  // Packaged
}

// ── Εκκίνηση Flask ────────────────────────────────────────────────────────────
function startFlask() {
  const python = getPythonPath();
  const backendDir = getBackendPath();
  const appScript = path.join(backendDir, 'app.py');

  console.log(`[Flask] Starting: ${python} ${appScript}`);
  console.log(`[Flask] Working dir: ${backendDir}`);

  flaskProcess = spawn(python, [appScript], {
    cwd: backendDir,
    env: {
      ...process.env,
      FLASK_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  flaskProcess.stdout.on('data', d => console.log('[Flask]', d.toString().trim()));
  flaskProcess.stderr.on('data', d => console.log('[Flask ERR]', d.toString().trim()));

  flaskProcess.on('exit', (code) => {
    console.log(`[Flask] Exited with code ${code}`);
    if (mainWindow && code !== 0) {
      dialog.showErrorBox(
        'Σφάλμα Backend',
        `Το Flask τερματίστηκε απροσδόκητα (κωδικός ${code}).\nΕπανεκκινήστε την εφαρμογή.`
      );
    }
  });
}

// ── Αναμονή μέχρι το Flask να είναι έτοιμο ──────────────────────────────────
function waitForFlask(retries = 30, delay = 500) {
  return new Promise((resolve, reject) => {
    const check = (n) => {
      http.get(`http://localhost:${FLASK_PORT}/api/apothemates`, (res) => {
        if (res.statusCode === 200) resolve();
        else if (n > 0) setTimeout(() => check(n - 1), delay);
        else reject(new Error('Flask δεν ξεκίνησε εγκαίρως'));
      }).on('error', () => {
        if (n > 0) setTimeout(() => check(n - 1), delay);
        else reject(new Error('Flask δεν ξεκίνησε εγκαίρως'));
      });
    };
    check(retries);
  });
}

// ── Δημιουργία παραθύρου ─────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    frame: false,           // Χωρίς OS chrome — custom titlebar μέσα στο HTML
    titleBarStyle: 'hidden',
    backgroundColor: '#0f2040',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    show: false,            // Δεν εμφανίζεται μέχρι να φορτωθεί
  });

  mainWindow.loadURL(`http://localhost:${FLASK_PORT}`);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    // mainWindow.webContents.openDevTools(); // Uncomment για debugging
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Splash / loading screen ───────────────────────────────────────────────────
function createSplash() {
  const splash = new BrowserWindow({
    width: 420,
    height: 260,
    frame: false,
    alwaysOnTop: true,
    backgroundColor: '#0f2040',
    webPreferences: { contextIsolation: true }
  });

  splash.loadURL(`data:text/html,
    <html>
    <head><meta charset="UTF-8">
    <style>
      body { margin:0; background:#0f2040; display:flex; flex-direction:column;
             align-items:center; justify-content:center; height:100vh;
             font-family: 'Segoe UI', sans-serif; color:white; }
      .icon { font-size:52px; margin-bottom:16px; }
      h1 { font-size:16px; font-weight:600; letter-spacing:2px;
           color:#e8a020; text-transform:uppercase; margin:0 0 8px; }
      p  { font-size:12px; color:rgba(255,255,255,0.5); margin:0 0 28px; }
      .bar-wrap { width:220px; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; }
      .bar { height:4px; background:#e8a020; border-radius:2px;
             animation: load 2s ease-in-out infinite; }
      @keyframes load { 0%{width:0} 60%{width:80%} 100%{width:100%} }
    </style></head>
    <body>
      <div class="icon">💣</div>
      <h1>Βιβλίο Εκρηκτικών Υλών</h1>
      <p>Εκκίνηση υπηρεσιών...</p>
      <div class="bar-wrap"><div class="bar"></div></div>
    </body></html>
  `);

  return splash;
}

// ── IPC: Window controls ──────────────────────────────────────────────────────
ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window-close', () => mainWindow?.close());

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  const splash = createSplash();

  // Ctrl+Q / Cmd+Q για έξοδο
  globalShortcut.register('CommandOrControl+Q', () => app.quit());

  try {
    startFlask();
    await waitForFlask();
    createWindow();
    splash.close();
  } catch (err) {
    splash.close();
    dialog.showErrorBox(
      'Σφάλμα Εκκίνησης',
      `Δεν ήταν δυνατή η εκκίνηση του backend:\n${err.message}\n\n` +
      `Βεβαιωθείτε ότι η Python είναι εγκατεστημένη και τα dependencies είναι διαθέσιμα.`
    );
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (flaskProcess) {
    console.log('[Flask] Terminating...');
    flaskProcess.kill('SIGTERM');
    // Windows fallback
    if (os.platform() === 'win32') {
      spawn('taskkill', ['/pid', flaskProcess.pid, '/f', '/t']);
    }
  }
  app.quit();
});

app.on('activate', () => {
  // macOS: ξαναάνοιγμα παραθύρου αν κλείστηκε
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
