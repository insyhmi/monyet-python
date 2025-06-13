const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const activeWin = require('active-win');
const path = require('path');
const audioPlayer = require ('play-sound')();
const Store = require('electron-store').default;


// 👇 Fix fetch for Node.js using dynamic import
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

let win;
let setupData = null;
let intervalId;
let user_task = "";
let wasProcrastinating = false;
let gemini_apiCallInterval = 20000 //ms 
let trackingActive = false;
let stopTracking = false;
let cameraWorker = null;

// New store
const store = new Store();
const activityLogs = [];

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

async function geminiTrackFunction() {
    try {
        console.log("Current goal is", currentTask); // Store this globally or in closure
        const activity = await activeWin();
        console.log("Detected active window:", activity);

        const response = await fetch('http://localhost:8000/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_task: currentTask,
                current_window: activity.title || activity.owner?.name || "Unknown"
            }),
        });

        const responseData = await response.json();
        console.log("Backend response:", responseData);

        if (win && win.webContents && !win.webContents.isDestroyed()) {
            win.webContents.send('active-window-data', activity);
            win.webContents.send('backend-result', responseData);
        }
        activityLogs.push({
            procrastinating: responseData.isProcrastinating,  // boolean
            site: responseData.current_window
        });
        if (responseData.isProcrastinating && !wasProcrastinating) {
            new Notification({
                title: 'Focus Alert 🚨',
                body: `You're currently off-task: ${responseData.current_window}`,
            }).show();
            wasProcrastinating = true;
        } else if (!responseData.isProcrastinating) {
            wasProcrastinating = false;
        }

    } catch (err) {
        console.error("Error in tracking:", err);
    }
}

// Camera Tracking Controller
const cameraTracker = {
  /**
   * Starts the camera tracking
   * @returns {Promise<{status: string, success: boolean}>}
   */
  async start() {
    try {
      const response = await fetch('http://localhost:8000/start-tracking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error starting camera tracking:', error);
      return { status: 'error', success: false, message: error.message };
    }
  },

  /**
   * Stops the camera tracking
   * @returns {Promise<{status: string, success: boolean}>}
   */
  async stop() {
    try {
      const response = await fetch('http://localhost:8000/stop-tracking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error stopping camera tracking:', error);
      return { status: 'error', success: false, message: error.message };
    }
  },

  /**
   * Gets the current tracking status
   * @returns {Promise<{is_active: boolean, last_detection: object}>}
   */
  async getStatus() {
    try {
      const response = await fetch('http://localhost:8000/status');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting camera status:', error);
      return { is_active: false, last_detection: null };
    }
  }
};
// Start tracking: await cameraTracker.start()
// Stop tracking: await cameraTracker.stop()
// Check status: await cameraTracker.getStatus()

// Start tracking when focus session begins
async function onFocusStart() {
  const result = await cameraTracker.start();
  if (result.success) {
    console.log('Camera tracking started');
  }
}

// Stop tracking when break starts
async function onBreakStart() {
  const result = await cameraTracker.stop();
  if (result.success) {
    console.log('Camera tracking stopped');
  }
}

// Check status periodically
async function checkCameraStatus() {
  const status = await cameraTracker.getStatus();
  console.log('Camera status:', status);
  if (status.last_detection.banned_items_detected){
    new Notification({
        title: '📱 Phone alert!',
        body: 'Please stay focus during this time!',
    }).show();
    win.webContents.send('play-alert-sound', true);
  }
  else if (!status.last_detection.user_present){
    new Notification({
        title: '🚶‍➡️ User is missing!',
        body: 'Come back! Your work is still in progress!',
    }).show();
    win.webContents.send('play-alert-sound', true);
  }
}

async function trackingLoop() {
  while (!stopTracking) {
    await new Promise(res => setTimeout(res, gemini_apiCallInterval)); // Wait first
    if (stopTracking){
        break;
    }
    await geminiTrackFunction(); // Then send data
    checkCameraStatus();
  }
};


ipcMain.on('gemini_changeApiInterval', async (event,time) =>{
    console.log("Changing Gemini API interval to", time);
    gemini_apiCallInterval = time;
});

// Active Window Tracking
ipcMain.handle('start-tracking', async (event, task) => {
  if (trackingActive) return;
  currentTask = task;
  trackingActive = true;
  stopTracking = false;
  onFocusStart();
  trackingLoop();
});

ipcMain.on('notify-test', (event, { title, body }) => {
    notify(title, body);
});

ipcMain.handle('stop-tracking', async () => {
  stopTracking = true;
  trackingActive = false;
  onBreakStart();
  console.log("Tracking stopped");
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
