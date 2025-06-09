const { app, BrowserWindow, ipcMain } = require('electron');
const activeWin = require('active-win');
const path = require('path');

// 👇 Fix fetch for Node.js using dynamic import
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

let win;
let setupData;
let intervalId;

function createWindow() {
  console.log('Creating browser window...');

  win = new BrowserWindow({
    width: 800,
    height: 600,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // optional
      contextIsolation: true
    },
  });

  win.loadFile(path.join(__dirname, 'setup.html'));
  console.log('Window bounds:', win.getBounds());
}

// Active Window Tracking

ipcMain.handle('start-tracking', async (event, task) => {
  if (intervalId) return;

  intervalId = setInterval(async () => {
    try {
      console.log("Current goal is", task);
      const activity = await activeWin();
      console.log("Detected active window:", activity);

      // 🚀 Send active window title to FastAPI backend
      const response = await fetch('http://localhost:8000/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_task: task,
          current_window: activity.title || activity.owner?.name || "Unknown"
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        console.error("FastAPI returned an error:", text);
        return;
      }

      const responseData = await response.json();
      console.log("Backend response:", responseData);

      // Send window data to renderer (frontend)
      if (win && win.webContents && !win.webContents.isDestroyed()) {
        win.webContents.send('active-window-data', { activeWindow: activity, analysis: responseData });
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

// Save data in memory from setup window

ipcMain.handle('save-setup-data', async (event, data) => {
  setupData = data;
  console.log('Setup data saved:', setupData);
  return true;
});

// Get setup data from main page
ipcMain.handle('get-setup-data', async () => {
  console.log("DEBUG Getting setup data....")
  return setupData;
}); 


// Load main page (index.html) after setup
ipcMain.on('load-main-window', () => {
  if (win) {
    win.loadFile(path.join(__dirname, 'index.html'));
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
