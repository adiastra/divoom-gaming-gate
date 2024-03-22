// renderer.js
const { ipcRenderer } = require('electron');

const form = document.querySelector('form');

form.addEventListener('submit', (event) => {
  event.preventDefault();

  const characterName = form.querySelector('#character-name').value;
  const characterHealth = form.querySelector('#character-health').value;

  ipcRenderer.send('submit-form', { characterName, characterHealth });
});

ipcRenderer.on('image-data', (event, { imageData }) => {
  // Send imageData to Divoom TimeGate device
  console.log(imageData);
});
