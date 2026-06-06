const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  call:     (cmd, payload = {}) => ipcRenderer.invoke('python', cmd, payload),
  openFile: ()                  => ipcRenderer.invoke('open-file-dialog'),
  saveFile: (opts)              => ipcRenderer.invoke('save-file-dialog', opts),
  minimize: ()                  => ipcRenderer.send('window-minimize'),
  maximize: ()                  => ipcRenderer.send('window-maximize'),
  close:    ()                  => ipcRenderer.send('window-close'),
  platform: process.platform,
});
