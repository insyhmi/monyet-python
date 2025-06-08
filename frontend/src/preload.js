const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  startTracking: () => ipcRenderer.invoke('start-tracking'),
  stopTracking: () => ipcRenderer.send('stop-tracking'),
  onWindowData: (callback) => ipcRenderer.on('active-window-data', (_, data) => callback(data)),
});