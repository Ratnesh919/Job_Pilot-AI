const { app, BrowserWindow, ipcMain, shell, Notification } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, spawnSync } = require('child_process');

let mainWindow = null;
let activeBotProcess = null;
let botStartTime = null;
let botLogs = [];

const ROOT_DIR = __dirname;
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const DATA_DIR = path.join(ROOT_DIR, 'data');
const CONFIG_PATH = path.join(ROOT_DIR, 'config.json');
const DB_PATH = path.join(DATA_DIR, 'applications_db.json');
const NOTIFICATIONS_PATH = path.join(DATA_DIR, 'notifications.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// ─── Configuration Management ───────────────────────────────────────
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    }
  } catch (e) {
    console.error('Error loading config:', e);
  }
  return {
    candidate: {
      name: "Job Candidate",
      email: "",
      phone: "",
      location: "Remote",
      portfolio: "",
      linkedin: "",
      experience_years: "0-1"
    },
    api_keys: { openrouter: "", nvidia: "", gemini: "" },
    email: { sender: "", app_password: "" },
    browser: { chrome_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: true },
    target_roles: ["Software Engineer", "Python Developer", "Frontend Developer"],
    experience_level: "fresher",
    primary_location: "Remote",
    preferred_locations: ["Remote", "New York", "Bengaluru"],
    include_remote: true,
    bot_settings: { max_per_run: 10, delay_ms: 2000, retry_count: 3, enable_desktop_notifications: true }
  };
}

function saveConfig(newConfig) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(newConfig, null, 2), 'utf-8');
    return true;
  } catch (e) {
    console.error('Error saving config:', e);
    return false;
  }
}

// ─── Applications Database ──────────────────────────────────────────
function getApplicationsDB() {
  try {
    if (fs.existsSync(DB_PATH)) {
      return JSON.parse(fs.readFileSync(DB_PATH, 'utf-8'));
    }
  } catch (e) {
    console.error('Error reading applications db:', e);
  }
  return [];
}

function saveApplicationsDB(apps) {
  try {
    fs.writeFileSync(DB_PATH, JSON.stringify(apps, null, 2), 'utf-8');
    return true;
  } catch (e) {
    console.error('Error saving applications db:', e);
    return false;
  }
}

function updateApplicationStatus(id, newStatus, note = '') {
  const apps = getApplicationsDB();
  const app = apps.find(a => a.id === id);
  if (app) {
    const oldStatus = app.status;
    app.status = newStatus;
    const timestamp = new Date().toLocaleString();
    if (!app.history) app.history = [];
    app.history.push({
      status: newStatus,
      date: timestamp,
      note: note || `Status updated from ${oldStatus} to ${newStatus}`
    });
    saveApplicationsDB(apps);
    sendDesktopNotification(`Status Updated: ${app.company}`, `${app.role} is now marked as "${newStatus}".`);
    return { success: true, app };
  }
  return { success: false, message: 'Application not found' };
}

// ─── Notifications ──────────────────────────────────────────────────
function getNotifications() {
  try {
    if (fs.existsSync(NOTIFICATIONS_PATH)) {
      return JSON.parse(fs.readFileSync(NOTIFICATIONS_PATH, 'utf-8'));
    }
  } catch (e) {
    console.error('Error reading notifications:', e);
  }
  return [];
}

function saveNotifications(notifications) {
  try {
    fs.writeFileSync(NOTIFICATIONS_PATH, JSON.stringify(notifications, null, 2), 'utf-8');
  } catch (e) {
    console.error('Error saving notifications:', e);
  }
}

function addNotification(title, message, type = 'info') {
  const notifs = getNotifications();
  const newNotif = {
    id: `notif_${Date.now()}`,
    title,
    message,
    type,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    date: new Date().toISOString()
  };
  notifs.unshift(newNotif);
  if (notifs.length > 50) notifs.pop();
  saveNotifications(notifs);

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('new-notification', newNotif);
  }
}

function sendDesktopNotification(title, body) {
  const cfg = loadConfig();
  if (cfg.bot_settings && cfg.bot_settings.enable_desktop_notifications === false) {
    return;
  }
  if (Notification.isSupported()) {
    new Notification({ title, body, silent: false }).show();
  }
}

// ─── Metrics & Stats ────────────────────────────────────────────────
function getStats() {
  const apps = getApplicationsDB();
  const total = apps.length;
  const applied = apps.filter(a => a.status === 'Applied').length;
  const underReview = apps.filter(a => a.status === 'Under Review').length;
  const interviews = apps.filter(a => a.status === 'Interview Scheduled' || (a.status && a.status.includes('Interview'))).length;
  const tests = apps.filter(a => a.status === 'Assessment / Test').length;
  const offers = apps.filter(a => a.status === 'Selected / Offered').length;
  const rejected = apps.filter(a => a.status === 'Rejected').length;

  const successRate = total > 0 ? Math.round(((total - rejected) / total) * 100) : 0;

  return {
    totalApplications: total,
    applied,
    underReview,
    interviews,
    tests,
    offers,
    rejected,
    successRate: `${successRate}%`
  };
}

// ─── Window Creation ────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1380,
    height: 880,
    minWidth: 1080,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0b0f17',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile('index.html');

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (activeBotProcess) {
      try { process.kill(-activeBotProcess.pid); } catch (e) { activeBotProcess.kill(); }
      activeBotProcess = null;
    }
  });
}

// ─── Bot Execution ──────────────────────────────────────────────────
function startBot(options = {}) {
  if (activeBotProcess) {
    return { success: false, message: 'Bot is already active!' };
  }

  const script = path.join(BACKEND_DIR, 'auto_job_agent.py');
  botStartTime = Date.now();
  botLogs = [];

  const proc = spawn('python', ['-u', script], {
    cwd: BACKEND_DIR,
    env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
  });

  activeBotProcess = proc;

  proc.stdout.on('data', (data) => {
    const text = data.toString('utf-8');
    botLogs.push({ type: 'stdout', text, time: new Date().toISOString() });
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-output', { type: 'stdout', text });
      mainWindow.webContents.send('bot-status-change', getBotStatus());
    }
  });

  proc.stderr.on('data', (data) => {
    const text = data.toString('utf-8');
    botLogs.push({ type: 'stderr', text, time: new Date().toISOString() });
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-output', { type: 'stderr', text });
    }
  });

  proc.on('close', (code) => {
    activeBotProcess = null;
    sendDesktopNotification('JobPilot-AI Cycle Complete', 'Bot finished applying for jobs.');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-status-change', getBotStatus());
    }
  });

  proc.on('error', (err) => {
    activeBotProcess = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-output', { type: 'stderr', text: `Failed to spawn bot: ${err.message}` });
      mainWindow.webContents.send('bot-status-change', getBotStatus());
    }
  });

  return { success: true, message: 'JobPilot-AI started successfully.' };
}

function startBotCustom(portalChoice = 'all', keyword = 'Software Engineer', headless = true) {
  if (activeBotProcess) return;
  const script = path.join(BACKEND_DIR, 'portal_auto_applier.py');
  botStartTime = Date.now();

  const proc = spawn('python', ['-u', script, keyword], {
    cwd: BACKEND_DIR,
    env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
  });

  activeBotProcess = proc;
  proc.stdout.on('data', (data) => {
    const text = data.toString('utf-8');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-output', { type: 'stdout', text });
      mainWindow.webContents.send('bot-status-change', getBotStatus());
    }
  });
  proc.on('close', () => {
    activeBotProcess = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-status-change', getBotStatus());
    }
  });
}

function stopBot() {
  if (activeBotProcess) {
    try { activeBotProcess.kill('SIGTERM'); } catch (e) { activeBotProcess.kill(); }
    activeBotProcess = null;
    return { success: true, message: 'JobPilot-AI stopped.' };
  }
  return { success: false, message: 'Bot is not running.' };
}

function getBotStatus() {
  const apps = getApplicationsDB();
  return {
    running: activeBotProcess !== null,
    startTime: botStartTime,
    appliedCount: apps.length
  };
}

async function runEmailStatusCheck() {
  return new Promise((resolve) => {
    const script = path.join(BACKEND_DIR, 'email_status_tracker.py');
    const proc = spawn('python', ['-u', script], {
      cwd: BACKEND_DIR,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    });

    let stdoutData = '';
    proc.stdout.on('data', (d) => { stdoutData += d.toString('utf-8'); });
    proc.on('close', () => {
      try {
        const res = JSON.parse(stdoutData.trim());
        if (res.updates && res.updates.length > 0) {
          sendDesktopNotification('Interview Updates Detected 🎉', `Found ${res.updates.length} recruiter updates in Gmail!`);
        }
        resolve(res);
      } catch (e) {
        resolve({ success: false, message: 'Scan finished', updates: [] });
      }
    });
    proc.on('error', (err) => {
      resolve({ success: false, message: err.message, updates: [] });
    });
  });
}

async function testSmtp() {
  return new Promise((resolve) => {
    const script = path.join(BACKEND_DIR, 'email_sender.py');
    const proc = spawn('python', ['-u', script, '--test'], {
      cwd: BACKEND_DIR,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    });

    let output = '';
    proc.stdout.on('data', (d) => { output += d.toString('utf-8'); });
    proc.on('close', () => {
      resolve(output.includes('SMTP_OK'));
    });
    proc.on('error', () => {
      resolve(false);
    });
  });
}

// ─── IPC Handlers ───────────────────────────────────────────────────
function setupIPC() {
  ipcMain.handle('get-config', () => loadConfig());
  ipcMain.handle('save-config', (_, config) => {
    const ok = saveConfig(config);
    if (ok && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('config-updated', config);
    }
    return ok;
  });

  ipcMain.handle('get-stats', () => getStats());
  ipcMain.handle('get-applications', () => getApplicationsDB());
  ipcMain.handle('update-application-status', (_, { id, newStatus, note }) => updateApplicationStatus(id, newStatus, note));
  ipcMain.handle('delete-application', (_, id) => {
    const apps = getApplicationsDB();
    const filtered = apps.filter(a => a.id !== id);
    saveApplicationsDB(filtered);
    return { success: true };
  });

  ipcMain.handle('check-status-updates', async () => await runEmailStatusCheck());
  ipcMain.handle('get-notifications', () => getNotifications());
  ipcMain.handle('clear-notifications', () => {
    saveNotifications([]);
    return { success: true };
  });

  ipcMain.handle('start-bot', (_, options) => startBot(options));
  ipcMain.handle('stop-bot', () => stopBot());
  ipcMain.handle('get-bot-status', () => getBotStatus());
  ipcMain.handle('test-smtp', async () => await testSmtp());

  ipcMain.handle('open-login-browser', async () => {
    const profileDir = path.join(DATA_DIR, 'chrome_profile');
    const pythonCode = `
import asyncio, os
from playwright.async_api import async_playwright

async def main():
    os.makedirs(r'${profileDir.replace(/\\/g, '\\\\')}', exist_ok=True)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=r'${profileDir.replace(/\\/g, '\\\\')}',
            headless=False,
            args=['--no-first-run']
        )
        p1 = context.pages[0] if context.pages else await context.new_page()
        await p1.goto('https://www.linkedin.com/login')
        p2 = await context.new_page()
        await p2.goto('https://www.naukri.com/nlogin/login')
        print('[BROWSER] Login browser opened. You can log into LinkedIn & Naukri once.', flush=True)
        try:
            await p1.wait_for_timeout(300000)
        except:
            pass
        await context.close()

asyncio.run(main())
`;
    spawn('python', ['-u', '-c', pythonCode], {
      cwd: BACKEND_DIR,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    });
    return { success: true, message: 'Opening login browser...' };
  });

  ipcMain.handle('open-external', (_, url) => { shell.openExternal(url); });
  
  ipcMain.handle('select-resume-file', async () => {
    const { dialog } = require('electron');
    const result = await dialog.showOpenDialog(mainWindow, {
      title: 'Select Resume PDF File',
      filters: [{ name: 'PDF Resume', extensions: ['pdf'] }],
      properties: ['openFile']
    });

    if (!result.canceled && result.filePaths.length > 0) {
      const selectedPath = result.filePaths[0];
      const targetPath = path.join(ROOT_DIR, 'Resume.pdf');
      try {
        fs.copyFileSync(selectedPath, targetPath);
      } catch (e) {
        console.error('Error copying resume:', e);
      }

      // Automatically run AI Resume Extractor
      let extractedData = null;
      try {
        const script = path.join(BACKEND_DIR, 'resume_extractor.py');
        const proc = spawnSync('python', ['-u', script, targetPath], {
          cwd: BACKEND_DIR,
          env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
        });
        if (proc.stdout) {
          const res = JSON.parse(proc.stdout.toString('utf-8').trim());
          if (res.success && res.extracted) {
            extractedData = res.extracted;
          }
        }
      } catch (e) {
        console.error('Error in AI resume extraction:', e);
      }

      const updatedConfig = loadConfig();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('config-updated', updatedConfig);
        if (extractedData) {
          mainWindow.webContents.send('resume-extracted', { extracted: extractedData, fileName: path.basename(selectedPath) });
        }
      }
      return {
        success: true,
        filePath: targetPath,
        fileName: path.basename(selectedPath),
        extracted: extractedData
      };
    }
    return { success: false, canceled: true };
  });
  ipcMain.handle('minimize-window', () => { if (mainWindow) mainWindow.minimize(); });
  ipcMain.handle('maximize-window', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) mainWindow.unmaximize();
      else mainWindow.maximize();
    }
  });
  ipcMain.handle('close-window', () => { if (mainWindow) mainWindow.close(); });

  ipcMain.handle('execute-ai-prompt', async (_, promptText) => {
    return new Promise((resolve) => {
      const script = path.join(BACKEND_DIR, 'ai_command_agent.py');
      const proc = spawn('python', ['-u', script, promptText], {
        cwd: BACKEND_DIR,
        env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
      });

      let stdoutData = '';
      let stderrData = '';

      proc.stdout.on('data', (d) => { stdoutData += d.toString('utf-8'); });
      proc.stderr.on('data', (d) => { stderrData += d.toString('utf-8'); });

      proc.on('close', () => {
        try {
          const res = JSON.parse(stdoutData.trim());
          const plan = res.plan || {};
          
          if (plan.action === 'apply_portal') {
            const kw = plan.parameters?.keyword || 'Software Engineer';
            startBotCustom(plan.parameters?.portal || 'all', kw, plan.parameters?.headless !== false);
          } else if (plan.action === 'update_settings' || res.execution?.config_updated) {
            const freshConfig = loadConfig();
            if (mainWindow && !mainWindow.isDestroyed()) {
              mainWindow.webContents.send('config-updated', freshConfig);
            }
          }

          addNotification('AI Agent Action', plan.message_to_user || 'Executed AI command', 'info');
          resolve(res);
        } catch (e) {
          resolve({
            success: false,
            error: stderrData || 'Failed to execute AI prompt',
            plan: { message_to_user: 'Processed request. ' + (stdoutData || stderrData || e.message) }
          });
        }
      });

      proc.on('error', (err) => {
        resolve({ success: false, error: err.message });
      });
    });
  });
}

// ─── App Lifecycle ──────────────────────────────────────────────────
app.whenReady().then(() => {
  setupIPC();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
