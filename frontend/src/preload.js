const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  startTracking: (task) => ipcRenderer.invoke('start-tracking', task),
  stopTracking: () => ipcRenderer.send('stop-tracking'),
  onWindowData: (callback) => ipcRenderer.on('active-window-data', (_, data) => callback(data)),
  saveSetupData: (data) => ipcRenderer.invoke('save-setup-data', data),
  getSetupData: () => ipcRenderer.invoke('get-setup-data'),
  loadMainWindow: () => ipcRenderer.send('load-main-window'),
});