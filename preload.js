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
  onUpdateStatus:     (cb) => ipcRenderer.on('update-status', (_, info) => cb(info)),
  openExternal:       (url) => ipcRenderer.invoke('open-external', url),
  installUpdate:      ()   => ipcRenderer.send('update-install'),
  getAppVersion:      ()              => ipcRenderer.invoke('get-app-version'),
  getVersionHistory:  ()              => ipcRenderer.invoke('get-version-history'),
  getAllowedVersions: ()              => ipcRenderer.invoke('get-allowed-versions'),
  reportVersionIssue: (lastGood, desc) => ipcRenderer.invoke('report-version-issue', lastGood, desc),
  onVersionNotice:    (cb) => ipcRenderer.once('version-notice', (_, info) => cb(info)),
});
