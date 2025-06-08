const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  startTracking: (task) => ipcRenderer.invoke('start-tracking', task),
  stopTracking: () => ipcRenderer.send('stop-tracking'),
  onWindowData: (callback) => ipcRenderer.on('active-window-data', (_, data) => callback(data)),
});