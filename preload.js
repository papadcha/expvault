const { contextBridge, ipcRenderer } = require('electron');

// Εκθέτει ελεγχόμενες λειτουργίες στο frontend
contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close:    () => ipcRenderer.send('window-close'),
  platform: process.platform,
});
