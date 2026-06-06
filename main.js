const { app, BrowserWindow, dialog, ipcMain, globalShortcut } = require('electron');
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
  const backendDir = getBackendPath();
  const venvPython = path.join(backendDir, 'venv',
    os.platform() === 'win32' ? 'Scripts/python.exe' : 'bin/python3'
  );
  if (fs.existsSync(venvPython)) return venvPython;
  return os.platform() === 'win32' ? 'python' : 'python3';
}

function getBackendPath() {
  const devPath = path.join(__dirname, 'backend');
  if (fs.existsSync(path.join(devPath, 'bridge.py'))) return devPath;
  return path.join(process.resourcesPath, 'backend');
}

function startBridge() {
  const python = getPythonPath();
  const backendDir = getBackendPath();
  const bridgeScript = path.join(backendDir, 'bridge.py');
  console.log(`[Bridge] Starting: ${python} ${bridgeScript}`);

  pythonProcess = spawn(python, [bridgeScript], {
    cwd: backendDir,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
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
      ? [{ name: 'PDF', extensions: ['pdf'] }]
      : [{ name: 'Excel', extensions: ['xlsx'] }];
    const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
      defaultPath: defaultName, filters, properties: ['createDirectory']
    });
    return canceled ? null : filePath;
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
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.webContents.openDevTools();
  });
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(() => {
  globalShortcut.register('CommandOrControl+Q', () => app.quit());
  setupIPC();
  startBridge();
  createWindow();
});

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    pythonProcess.stdin.end();
    pythonProcess.kill('SIGTERM');
  }
  setTimeout(() => app.quit(), 300);
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
