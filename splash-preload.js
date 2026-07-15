const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splashApi', {
  onAdeiaInfo: (cb) => ipcRenderer.on('adeia-info', (_, data) => cb(data)),
  close: () => ipcRenderer.send('splash-close'),
});
