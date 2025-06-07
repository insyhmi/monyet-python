const { app, BrowserWindow } = require('electron');
const path = require('path');

console.log('Electron app starting...'); 

function createWindow () {
  console.log('Creating browser window...'); 

  const win = new BrowserWindow({
    width: 800,
    height: 600,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js') // optional
    }
  });

  win.loadFile(path.join(__dirname, 'index.html'));
  console.log('Window bounds:', win.getBounds());
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
