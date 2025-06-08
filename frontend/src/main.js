const { app, BrowserWindow, ipcMain } = require('electron');
const activeWin = require('active-win');
const path = require('path');

console.log('Electron app starting...'); 

let win;

function createWindow () {
  console.log('Creating browser window...'); 

  win = new BrowserWindow({
    width: 800,
    height: 600,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // optional
    }
  });

  win.loadFile(path.join(__dirname, 'index.html'));
  console.log('Window bounds:', win.getBounds());
}


// Active Window Tracking


let intervalId;

ipcMain.handle('start-tracking', async () => {
  if (intervalId) return;

  intervalId = setInterval(async () => {
    try {
      const result = await activeWin();
      console.log("Detected active window:", result);

      if (win && win.webContents && !win.webContents.isDestroyed()) {
        win.webContents.send('active-window-data', result);
      }
    } catch (err) {
      console.error("Error in tracking:", err);
    }
  }, 5000);
});

ipcMain.on('stop-tracking', () => {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
});


app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    } 
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
