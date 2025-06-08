const { app, BrowserWindow, ipcMain } = require('electron');
const activeWin = require('active-win');
const path = require('path');

// 👇 Fix fetch for Node.js using dynamic import
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

let win;

function createWindow() {
  console.log('Creating browser window...');

  win = new BrowserWindow({
    width: 800,
    height: 600,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // optional
    },
  });

  win.loadFile(path.join(__dirname, 'index.html'));
  console.log('Window bounds:', win.getBounds());
}

// 🧠 Active Window Tracking
let intervalId;

ipcMain.handle('start-tracking', async () => {
  if (intervalId) return;

  intervalId = setInterval(async () => {
    try {
      const result = await activeWin();
      console.log("Detected active window:", result);

      // 🚀 Send active window title to FastAPI backend
      const response = await fetch('http://localhost:8000/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_task: "writing code", // <-- Replace or update with user input if needed
          current_window: result.title || result.owner?.name || "Unknown"
        }),
      });

      const responseData = await response.json();
      console.log("Backend response:", responseData);

      // Send window data to renderer (frontend)
      if (win && win.webContents && !win.webContents.isDestroyed()) {
        win.webContents.send('active-window-data', result);
      }
    } catch (err) {
      console.error("Error in tracking:", err);
    }
  }, 10000); // Interval in miliseconds
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
