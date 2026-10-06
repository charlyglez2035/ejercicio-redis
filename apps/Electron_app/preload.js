const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('libraryApi', {
  fetchXml: (endpoint) => ipcRenderer.invoke('fetch-xml', endpoint)
});
