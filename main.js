// main.js
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');
const base64Img = require('base64-img');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    }
  });

  mainWindow.loadFile('index.html');

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

ipcMain.on('submit-form', (event, data) => {
  // Create image using ImageMagick
  exec('convert -size 128x128 xc:white RPGCharacter.png', (error, stdout, stderr) => {
    if (error) {
      console.error(`exec error: ${error}`);
      return;
    }

    // Add character name and health bar to the image
    exec(`convert RPGCharacter.png -gravity North -pointsize 16 -annotate +0+5 "${data.characterName}" RPGCharacter.png`);
    exec(`convert RPGCharacter.png -fill red -draw "rectangle 10,100 118,110" RPGCharacter.png`);
    exec(`convert RPGCharacter.png -fill green -draw "rectangle 10,100 90,110" RPGCharacter.png`);
    
    // Convert the image to base64
    base64Img.base64('RPGCharacter.png', (err, dataUrl) => {
      if (err) {
        console.error(`Error converting image to base64: ${err}`);
        return;
      }

      // Send the base64-encoded image data back to the front-end
      mainWindow.webContents.send('image-data', { imageData: dataUrl });
    });
  });
});
