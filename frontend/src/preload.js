const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  startTracking: (task) => ipcRenderer.invoke('start-tracking', task),
  stopTracking: () => ipcRenderer.send('stop-tracking'),
  sendTask: (taskValue) => ipcRenderer.send('task-value', taskValue),
  onWindowData: (callback) => ipcRenderer.on('active-window-data', (_, data) => callback(data)),
  saveSetupData: (data) => ipcRenderer.invoke('save-setup-data', data),
  getSetupData: () => ipcRenderer.invoke('get-setup-data'),
  loadMainWindow: () => ipcRenderer.send('load-main-window'),
  sendNotification: (title, body) => ipcRenderer.send('notify-test', { title, body }),
  onBackendResult: (callback) => ipcRenderer.on('backend-result', (_, result) => callback(result)),

});