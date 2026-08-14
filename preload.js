const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Config
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),

  // Stats & Applications
  getStats: () => ipcRenderer.invoke('get-stats'),
  getApplications: () => ipcRenderer.invoke('get-applications'),
  updateApplicationStatus: (payload) => ipcRenderer.invoke('update-application-status', payload),
  deleteApplication: (id) => ipcRenderer.invoke('delete-application', id),
  
  // Status Tracking & Email Scanner
  checkStatusUpdates: () => ipcRenderer.invoke('check-status-updates'),

  // Notifications
  getNotifications: () => ipcRenderer.invoke('get-notifications'),
  clearNotifications: () => ipcRenderer.invoke('clear-notifications'),
  onNewNotification: (callback) => {
    ipcRenderer.on('new-notification', (_, data) => callback(data));
  },

  // AI Command Agent
  executeAiPrompt: (prompt) => ipcRenderer.invoke('execute-ai-prompt', prompt),

  // Logs & Login
  getLogs: () => ipcRenderer.invoke('get-applications'),
  openLoginBrowser: () => ipcRenderer.invoke('open-login-browser'),

  // Bot Control
  startBot: (options) => ipcRenderer.invoke('start-bot', options),
  stopBot: () => ipcRenderer.invoke('stop-bot'),
  getBotStatus: () => ipcRenderer.invoke('get-bot-status'),

  // SMTP Test
  testSmtp: () => ipcRenderer.invoke('test-smtp'),

  // External Links
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  selectResumeFile: () => ipcRenderer.invoke('select-resume-file'),

  // Window Controls
  minimize: () => ipcRenderer.invoke('minimize-window'),
  maximize: () => ipcRenderer.invoke('maximize-window'),
  close: () => ipcRenderer.invoke('close-window'),

  // Event Listeners
  onBotOutput: (callback) => {
    ipcRenderer.on('bot-output', (_, data) => callback(data));
  },
  onBotStatusChange: (callback) => {
    ipcRenderer.on('bot-status-change', (_, data) => callback(data));
  },
  onConfigUpdated: (callback) => {
    ipcRenderer.on('config-updated', (_, data) => callback(data));
  },

  // Cleanup
  removeAllBotListeners: () => {
    ipcRenderer.removeAllListeners('bot-output');
    ipcRenderer.removeAllListeners('bot-status-change');
    ipcRenderer.removeAllListeners('new-notification');
    ipcRenderer.removeAllListeners('config-updated');
  }
});
