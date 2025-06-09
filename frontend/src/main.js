const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const activeWin = require('active-win');
const path = require('path');

// 👇 Fix fetch for Node.js using dynamic import
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

let win;
let user_task = "";
let wasProcrastinating = false;

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

          current_task: user_task, 
          current_window: result.title || result.owner?.name || "Unknown"
        }),
      });

        const responseData = await response.json();
        console.log("Backend response:", responseData);

        if (win && win.webContents && !win.webContents.isDestroyed()) {
        win.webContents.send('active-window-data', result);
        win.webContents.send('backend-result', responseData);
        }

        // Check if the user is now procrastinating, and wasn't before
        if (responseData.isProcrastinating && !wasProcrastinating) {
            new Notification({
                title: 'Focus Alert 🚨',
                body: `You're currently off-task: ${responseData.current_window}`,
            }).show();

            wasProcrastinating = true;
        } else if (!responseData.isProcrastinating) {
            // Reset flag when user is back on task
            wasProcrastinating = false;
        }
    } catch (err) {
      console.error("Error in tracking:", err);
    }
  }, 5000); // Interval in miliseconds
});

ipcMain.on('notify-test', (event, { title, body }) => {
    notify(title, body);
});

ipcMain.on('stop-tracking', () => {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
});

function notify(title, body){
    new Notification({
        title : title,
        body : body,
    }).show();
}

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
