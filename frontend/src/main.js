const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  startTracking: (task) => ipcRenderer.invoke('start-tracking', task),
  getScore: (activityLog) => ipcRenderer.invoke('get-score', activityLog),
  stopTracking: () => ipcRenderer.send('stop-tracking'),
  sendTask: (taskValue) => ipcRenderer.send('task-value', taskValue),  
  saveSetupData: (data) => ipcRenderer.invoke('save-setup-data', data),
  getSetupData: () => ipcRenderer.invoke('get-setup-data'),
  loadMainWindow: () => ipcRenderer.send('load-main-window'),
  sendNotification: (title, body) => ipcRenderer.send('notify-test', { title, body }),

  onWindowData: (callback) => ipcRenderer.on('active-window-data', (_, data) => callback(data)),
  onBackendResult: (callback) => ipcRenderer.on('backend-result', (_, result) => callback(result)),
  gemini_changeApiInterval : (time) =>ipcRenderer.send('gemini_changeApiInterval', time)

});
