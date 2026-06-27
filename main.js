const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

let mainWindow = null;
let pythonProcess = null;
let pendingRequests = {};
let reqCounter = 0;
let bridgeReady = false;
let queuedMessages = [];

function getPythonPath() {
  const backendDir = path.join(__dirname, 'backend');
  const venvPython = path.join(backendDir, 'venv',
    os.platform() === 'win32' ? 'Scripts/python.exe' : 'bin/python3'
  );
  if (fs.existsSync(venvPython)) return venvPython;
  return os.platform() === 'win32' ? 'python' : 'python3';
}

function getBridgeExe() {
  // Σε packaged mode υπάρχει bridge.exe compiled με PyInstaller
  const exeName = os.platform() === 'win32' ? 'bridge.exe' : 'bridge';
  const exePath = path.join(process.resourcesPath, 'bridge', exeName);
  if (fs.existsSync(exePath)) return exePath;
  return null;
}

function startBridge() {
  const bridgeExe = getBridgeExe();
  const userDataDir = app.getPath('userData');
  fs.mkdirSync(userDataDir, { recursive: true });

  const fontsDir = app.isPackaged
    ? path.join(process.resourcesPath, 'assets', 'fonts')
    : path.join(__dirname, 'assets', 'fonts');

  const bridgeEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    EXPVAULT_DATA_DIR: userDataDir,
    EXPVAULT_FONTS_DIR: fontsDir,
  };

  let cmd, args, cwd;
  if (bridgeExe) {
    // Production: PyInstaller compiled exe
    cmd = bridgeExe;
    args = [];
    cwd = path.dirname(bridgeExe);
    console.log(`[Bridge] Starting packaged: ${bridgeExe}`);
  } else {
    // Development: run bridge.py with Python
    const backendDir = path.join(__dirname, 'backend');
    cmd = getPythonPath();
    args = [path.join(backendDir, 'bridge.py')];
    cwd = backendDir;
    // Σε dev mode χρησιμοποιούμε τον backend φάκελο για τα δεδομένα
    bridgeEnv.EXPVAULT_DATA_DIR = backendDir;
    console.log(`[Bridge] Starting dev: ${cmd} ${args[0]}`);
  }

  pythonProcess = spawn(cmd, args, {
    cwd,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: bridgeEnv,
  });

  let buffer = '';
  pythonProcess.stdout.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.ready) {
          console.log('[Bridge] Ready');
          bridgeReady = true;
          for (const m of queuedMessages) pythonProcess.stdin.write(m + '\n');
          queuedMessages = [];
          return;
        }
        const pending = pendingRequests[msg.id];
        if (pending) {
          delete pendingRequests[msg.id];
          if (msg.error) pending.reject(new Error(msg.error));
          else pending.resolve(msg.result);
        }
      } catch (e) {
        console.error('[Bridge] JSON parse error:', line);
      }
    }
  });

  pythonProcess.stderr.on('data', d => console.error('[Bridge ERR]', d.toString().trim()));
  pythonProcess.on('exit', (code) => {
    console.log(`[Bridge] Exited with code ${code}`);
    if (mainWindow && code !== 0)
      dialog.showErrorBox('Σφάλμα', `Το Python process τερματίστηκε (κωδικός ${code}).`);
  });
}

function callPython(cmd, payload = {}) {
  return new Promise((resolve, reject) => {
    const id = ++reqCounter;
    pendingRequests[id] = { resolve, reject };
    const msg = JSON.stringify({ id, cmd, payload });
    if (bridgeReady) pythonProcess.stdin.write(msg + '\n');
    else queuedMessages.push(msg);
    setTimeout(() => {
      if (pendingRequests[id]) {
        delete pendingRequests[id];
        reject(new Error(`Timeout: ${cmd}`));
      }
    }, 120000);
  });
}

function setupIPC() {
  ipcMain.handle('python', async (event, cmd, payload) => {
    try {
      return { ok: true, result: await callPython(cmd, payload) };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('open-file-dialog', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
      filters: [{ name: 'PDF', extensions: ['pdf'] }],
      properties: ['openFile']
    });
    return canceled ? null : filePaths[0];
  });

  ipcMain.handle('save-file-dialog', async (event, { defaultName, ext }) => {
    const filters = ext === 'pdf'
      ? [{ name: 'PDF Files', extensions: ['pdf'] }]
      : ext === 'docx'
      ? [{ name: 'Word Files', extensions: ['docx'] }]
      : [{ name: 'Excel Files', extensions: ['xlsx'] }];
    const downloadsPath = app.getPath('downloads');
    const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
      defaultPath: require('path').join(downloadsPath, defaultName),
      filters
    });
    return canceled ? null : filePath;
  });

  ipcMain.handle('open-dir-dialog', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory', 'createDirectory']
    });
    return canceled ? null : filePaths[0];
  });

  ipcMain.handle('open-rclone-terminal', async () => {
    function trySpawn(cmd, args, opts = {}) {
      return new Promise((resolve) => {
        try {
          const child = spawn(cmd, args, { detached: true, stdio: 'ignore', ...opts });
          child.on('error', () => resolve(false));
          child.unref();
          setTimeout(() => resolve(true), 200);
        } catch { resolve(false); }
      });
    }
    if (os.platform() === 'win32') {
      // Δοκιμή Windows Terminal πρώτα, μετά PowerShell, μετά cmd
      const attempts = [
        ['wt.exe', ['powershell', '-NoExit', '-Command', 'rclone config']],
        ['powershell.exe', ['-NoExit', '-Command', 'rclone config']],
        ['cmd.exe', ['/K', 'rclone config']],
      ];
      for (const [cmd, args] of attempts) {
        if (await trySpawn(cmd, args, { shell: false })) return { ok: true };
      }
      return { ok: false, error: 'Δεν βρέθηκε terminal — εκτελέστε χειροκίνητα: rclone config' };
    }
    const attempts = [
      ['alacritty', ['-e', 'rclone', 'config']],
      ['konsole',   ['-e', 'rclone', 'config']],
      ['kitty',     ['rclone', 'config']],
      ['gnome-terminal', ['--', 'rclone', 'config']],
      ['xfce4-terminal', ['-e', 'rclone config']],
      ['xterm',     ['-e', 'rclone config']],
    ];
    for (const [cmd, args] of attempts) {
      if (await trySpawn(cmd, args)) return { ok: true };
    }
    return { ok: false, error: 'Δεν βρέθηκε terminal — εκτελέστε χειροκίνητα: rclone config' };
  });

  ipcMain.on('window-minimize', () => mainWindow?.minimize());
  ipcMain.on('window-maximize', () => {
    mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize();
  });
  ipcMain.on('window-close', () => mainWindow?.close());
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    minWidth: 1024, minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0f2040',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());

  let _closeInProgress = false;
  mainWindow.on('close', async (e) => {
    if (_closeInProgress) return;

    let hasPaths = false;
    try {
      const cfg = await callPython('get_backup_config');
      hasPaths = Array.isArray(cfg?.paths) && cfg.paths.some(p => p);
    } catch {}

    if (!hasPaths) return;

    e.preventDefault();
    _closeInProgress = true;

    mainWindow.webContents.send('backup-progress', 'start');
    try {
      await callPython('run_backup');
      mainWindow.webContents.send('backup-progress', 'done');
    } catch (err) {
      console.error('[Backup] Error on close:', err.message);
      mainWindow.webContents.send('backup-progress', 'error');
    }
    await new Promise(r => setTimeout(r, 900));
    mainWindow.close();
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.commandLine.appendSwitch('lang', 'el');

app.whenReady().then(() => {
  setupIPC();
  startBridge();
  createWindow();
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.stdin.end();
    pythonProcess.kill('SIGTERM');
  }
  setTimeout(() => app.quit(), 300);
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
