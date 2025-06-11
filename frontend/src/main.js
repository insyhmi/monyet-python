const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const activeWin = require('active-win');
const path = require('path');
const Store = require('electron-store').default;

// 👇 Fix fetch for Node.js using dynamic import
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

let win;
let setupData = null;
let intervalId;
let user_task = "";
let wasProcrastinating = false;

// New store
const store = new Store();

function createWindow() {
  console.log('Creating browser window...');

  win = new BrowserWindow({
    width: 800,
    height: 600,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // optional
      contextIsolation: true,
      nodeIntegration: false,
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

      // Send active window title to FastAPI backend
      const response = await fetch('http://localhost:8000/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({

          current_task: task, 
          current_window: activity.title || activity.owner?.name || "Unknown"
        }),
      });


        const responseData = await response.json();
        console.log("Backend response:", responseData);

        if (win && win.webContents && !win.webContents.isDestroyed()) {
            win.webContents.send('active-window-data', activity);
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
  }, 10000); // Interval in miliseconds
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

// Save data in memory from setup window
ipcMain.handle('save-setup-data', async (event, data) => {
  store.set('setupData', data);
  const storedData = store.get('setupData'); // confirm it's really saved
  console.log('DEBUG main.js confirms setupData is now:', storedData);
  return true;
});

// Get setup data from main page
ipcMain.handle('get-setup-data', async () => {
  const data = store.get('setupData');
  console.log('Retrieved setup data in main.js:', data);
  return data;
}); 

// Load main page (index.html) after setup
ipcMain.on('load-main-window', () => {
  if (win) {
    win.loadFile(path.join(__dirname, 'index.html'));
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

