const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  call:     (cmd, payload = {}) => ipcRenderer.invoke('python', cmd, payload),
  openFile: ()                  => ipcRenderer.invoke('open-file-dialog'),
  saveFile: (opts)              => ipcRenderer.invoke('save-file-dialog', opts),
  openDir: ()                   => ipcRenderer.invoke('open-dir-dialog'),
  openJson: ()                  => ipcRenderer.invoke('open-json-dialog'),
  saveJson: (opts)              => ipcRenderer.invoke('save-json-dialog', opts),
  minimize: ()                  => ipcRenderer.send('window-minimize'),
  maximize: ()                  => ipcRenderer.send('window-maximize'),
  close:    ()                  => ipcRenderer.send('window-close'),
  platform: process.platform,
  onBackupProgress:    (cb) => ipcRenderer.on('backup-progress', (_, status) => cb(status)),
  openRcloneTerminal: ()   => ipcRenderer.invoke('open-rclone-terminal'),
});
