/**
 * script.js — AI Conveyor Color Segregation System
 * ===================================================
 * Architecture:
 *  1. CONFIG         — Tunable constants (timings, scoring, max log entries)
 *  2. STATE          — Single source-of-truth game state object
 *  3. DOM            — Cached element references
 *  4. AUTH MODULE    — Login / logout
 *  5. UI MODULE      — Header, score display, score delta notification
 *  6. BELT MODULE    — Conveyor animation, item spawning, movement tracking
 *  7. GAME MODULE    — Game loop, scoring, feedback
 *  8. LOG MODULE     — Moves feed
 *  9. HISTORY MODULE — Score history table + backend API calls
 * 10. CONTROLS       — Button wiring
 * 11. KEYBOARD       — Global key shortcuts
 * 12. INIT           — Boot sequence
 */

'use strict';

/* ═══════════════════════════════════════════════════════════════
   1. CONFIG
   ─────────────────────────────────────────────────────────────
   Change these to tune game feel.
   All time values are in milliseconds unless noted.
═══════════════════════════════════════════════════════════════ */
const CONFIG = {
  /** Duration for item to travel belt from left edge to right edge (ms) */
  ITEM_TRAVEL_MS: 4500,

  /** Pause between items after a round ends (ms) */
  INTER_ITEM_DELAY_MS: 900,

  /** Positive score per correct answer */
  SCORE_CORRECT: 5,

  /** Negative score per wrong / missed answer */
  SCORE_WRONG: -10,

  /** Max entries to keep in the moves log */
  MAX_LOG_ENTRIES: 20,

  /** Colors in the pool */
  COLORS: ['red', 'blue', 'green'],

  /** Backend API base URL — change to deployed URL in production */
  API_BASE: '',   // empty = same origin (served by FastAPI)

  /**
   * MOCK_AUTH: false = use real FastAPI+MongoDB backend (recommended).
   * Set to true only for pure offline JS testing without a backend.
   */
  MOCK_AUTH: false,

  /** Mock credentials (only used when MOCK_AUTH = true)
   *  Built-in admin accounts — always available even before any registration.
   *  Format: { username: plaintext_password }
   *  ┌────────────┬────────────┐
   *  │  Username  │  Password  │
   *  ├────────────┼────────────┤
   *  │  admin     │  admin123  │
   *  │  demo      │  demo      │
   *  └────────────┴────────────┘
   */
  MOCK_USERS: { admin: 'admin123', demo: 'demo' },
};

/* ═══════════════════════════════════════════════════════════════
   2. STATE
   ─────────────────────────────────────────────────────────────
   All mutable runtime state lives here. Never mutate directly
   from UI handlers — go through the module functions.
═══════════════════════════════════════════════════════════════ */
const STATE = {
  /** JWT Bearer token returned by /api/login — kept in memory only */
  jwtToken: null,

  /** Current logged-in username */
  username: '',

  /** Current game status: 'idle' | 'running' | 'paused' | 'stopped' */
  status: 'idle',

  /** Current score for this session */
  score: 0,

  /** Total rounds played this session */
  totalRounds: 0,

  /** Total correct answers this session */
  correctRounds: 0,

  /** Color of item currently on belt */
  currentColor: null,

  /** Color the user selected this round */
  selectedColor: null,

  /** Whether a round is currently in-flight (item on belt) */
  roundActive: false,

  /** requestAnimationFrame id for pause/resume tracking */
  animFrameId: null,

  /** setTimeout id for inter-item delay */
  nextItemTimer: null,

  /** Timestamp when item started moving (for pause math) */
  itemStartTime: null,

  /** How many ms have already elapsed (for resume after pause) */
  itemElapsedMs: 0,

  /** Reference to the CSS animation "start" mark for current item */
  itemAnimStarted: false,
};

/* ═══════════════════════════════════════════════════════════════
   3. DOM
   ─────────────────────────────────────────────────────────────
   Cache all element references once at startup.
═══════════════════════════════════════════════════════════════ */
const DOM = {};

function cacheDOM() {
  // Login
  DOM.loginOverlay   = document.getElementById('login-overlay');
  DOM.loginUsername  = document.getElementById('login-username');
  DOM.loginPassword  = document.getElementById('login-password');
  DOM.loginBtn       = document.getElementById('login-btn');
  DOM.loginError     = document.getElementById('login-error');

  // Auth tabs
  DOM.tabLogin       = document.getElementById('tab-login');
  DOM.tabRegister    = document.getElementById('tab-register');
  DOM.panelLogin     = document.getElementById('panel-login');
  DOM.panelRegister  = document.getElementById('panel-register');

  // Register fields
  DOM.regUsername    = document.getElementById('reg-username');
  DOM.regEmail       = document.getElementById('reg-email');
  DOM.regPassword    = document.getElementById('reg-password');
  DOM.regConfirm     = document.getElementById('reg-confirm');
  DOM.registerBtn    = document.getElementById('register-btn');
  DOM.registerMsg    = document.getElementById('register-msg');

  // Switch links
  DOM.goRegister     = document.getElementById('go-register');
  DOM.goLogin        = document.getElementById('go-login');

  // App shell
  DOM.app            = document.getElementById('app');

  // Header — user menu
  DOM.userMenuBtn       = document.getElementById('user-menu-btn');
  DOM.userDropdown      = document.getElementById('user-dropdown');
  DOM.userAvatar        = document.getElementById('user-avatar');
  DOM.usernameDisplay   = document.getElementById('username-display');
  DOM.dropdownAvatar    = document.getElementById('dropdown-avatar');
  DOM.dropdownUsername  = document.getElementById('dropdown-username');
  DOM.dropdownRole      = document.getElementById('dropdown-role');
  DOM.ddLogout          = document.getElementById('dd-logout');
  DOM.ddProfile         = document.getElementById('dd-profile');
  DOM.ddScores          = document.getElementById('dd-scores');

  // Header score
  DOM.scoreValue     = document.getElementById('score-value');

  // Needed for outside-click detection
  DOM.userDisplay    = document.getElementById('user-display');

  // Belt
  DOM.beltTrack      = document.getElementById('belt-track');
  DOM.beltLines      = document.getElementById('belt-lines');
  DOM.conveyorItem   = document.getElementById('conveyor-item');
  DOM.feedbackOverlay= document.getElementById('feedback-overlay');
  DOM.statusDots     = [
    document.getElementById('sd1'),
    document.getElementById('sd2'),
    document.getElementById('sd3'),
  ];

  // Color buttons
  DOM.colorButtons   = document.querySelectorAll('.color-btn');

  // Controls
  DOM.btnStart       = document.getElementById('btn-start');
  DOM.btnPause       = document.getElementById('btn-pause');
  DOM.btnStop        = document.getElementById('btn-stop');
  DOM.btnReset       = document.getElementById('btn-reset');

  // Log
  DOM.movesLog       = document.getElementById('moves-log');

  // Sidebar
  DOM.sidebarScore   = document.getElementById('sidebar-score');
  DOM.accuracyPct    = document.getElementById('accuracy-pct');
  DOM.accuracyFill   = document.getElementById('accuracy-bar-fill');
  DOM.accuracyBar    = document.getElementById('accuracy-bar-bg');
  DOM.historyTbody   = document.getElementById('history-tbody');

  // Delta notification
  DOM.scoreDelta     = document.getElementById('score-delta');
}

/* ═══════════════════════════════════════════════════════════════
   4. AUTH MODULE
   ─────────────────────────────────────────────────────────────
   Handles:
   - Tab switching between Login and Register panels
   - Login (mock JS-side OR real backend POST /api/login)
   - Register (POST /api/register — persisted to SQLite users table)
   - Session entry into the app shell
═══════════════════════════════════════════════════════════════ */
const Auth = (() => {

  /* ── Tab switching ─────────────────────────────────────────── */
  function switchTab(tab) {
    const isLogin = tab === 'login';
    DOM.tabLogin.classList.toggle('active', isLogin);
    DOM.tabRegister.classList.toggle('active', !isLogin);
    DOM.tabLogin.setAttribute('aria-selected', isLogin ? 'true' : 'false');
    DOM.tabRegister.setAttribute('aria-selected', !isLogin ? 'true' : 'false');
    DOM.panelLogin.classList.toggle('hidden', !isLogin);
    DOM.panelRegister.classList.toggle('hidden', isLogin);
    clearMessages();
    // Focus first input in active panel
    setTimeout(() => {
      const firstInput = isLogin ? DOM.loginUsername : DOM.regUsername;
      firstInput.focus();
    }, 60);
  }

  function clearMessages() {
    [DOM.loginError, DOM.registerMsg].forEach(el => {
      el.className = 'auth-msg hidden';
      el.textContent = '';
    });
  }

  function showLoginError(msg) {
    DOM.loginError.textContent = msg;
    DOM.loginError.className = 'auth-msg error';
    void DOM.loginError.offsetWidth; // restart shake
    DOM.loginError.className = 'auth-msg error';
  }

  function showRegisterMsg(msg, isError = true) {
    DOM.registerMsg.textContent = msg;
    DOM.registerMsg.className = `auth-msg ${isError ? 'error' : 'success'}`;
    void DOM.registerMsg.offsetWidth;
    DOM.registerMsg.className = `auth-msg ${isError ? 'error' : 'success'}`;
  }

  /* ── Login flow ───────────────────────────────────────────── */
  async function handleLogin() {
    clearMessages();
    const username = DOM.loginUsername.value.trim();
    const password = DOM.loginPassword.value;

    if (!username || !password) {
      showLoginError('Please enter your username and password.');
      return;
    }

    DOM.loginBtn.textContent = 'AUTHENTICATING…';
    DOM.loginBtn.disabled = true;

    let result;
    if (CONFIG.MOCK_AUTH) {
      // JS-side mock: checks built-in table first, then localStorage registered users
      result = mockLogin(username, password);
    } else {
      result = await apiLogin(username, password);
    }

    DOM.loginBtn.textContent = 'LOGIN';
    DOM.loginBtn.disabled = false;

    if (result.ok) {
      enterApp(result.username || username, result.role || 'user');
    } else {
      showLoginError(result.message);
      DOM.loginPassword.value = '';
      DOM.loginPassword.focus();
    }
  }

  /**
   * Mock login: checks CONFIG.MOCK_USERS (built-in admin accounts)
   * then falls through to localStorage registered users.
   */
  function mockLogin(username, password) {
    const lc = username.toLowerCase();

    // Check built-in admin accounts first
    if (CONFIG.MOCK_USERS[lc] === password) {
      return { ok: true, username: lc };
    }

    // Check locally registered users (stored by Register flow)
    const registered = getRegisteredUsers();
    const found = registered.find(u => u.username.toLowerCase() === lc);
    if (found && found.password === password) {
      return { ok: true, username: found.username };
    }

    return { ok: false, message: 'Invalid username or password.' };
  }

  async function apiLogin(username, password) {
    try {
      const res  = await fetch(`${CONFIG.API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        // Store JWT token in memory (not localStorage — security best practice)
        STATE.jwtToken = data.token;
        return { ok: true, username: data.username, role: data.role || 'user' };
      }
      const msg = data.detail?.message || data.message || 'Login failed.';
      return { ok: false, message: msg };
    } catch {
      return { ok: false, message: 'Cannot reach server. Is the backend running?\nRun: uvicorn app:app --reload --port 8000' };
    }
  }

  /* ── Register flow ────────────────────────────────────────── */
  async function handleRegister() {
    clearMessages();
    const username = DOM.regUsername.value.trim();
    const email    = DOM.regEmail.value.trim();
    const password = DOM.regPassword.value;
    const confirm  = DOM.regConfirm.value;

    // Validation
    if (!username) { showRegisterMsg('Username is required.'); return; }
    if (username.length < 3) { showRegisterMsg('Username must be at least 3 characters.'); return; }
    if (/\s/.test(username)) { showRegisterMsg('Username cannot contain spaces.'); return; }
    if (!password) { showRegisterMsg('Password is required.'); return; }
    if (password.length < 4) { showRegisterMsg('Password must be at least 4 characters.'); return; }
    if (password !== confirm) { showRegisterMsg('Passwords do not match.'); return; }

    DOM.registerBtn.textContent = 'CREATING…';
    DOM.registerBtn.disabled = true;

    let result;
    if (CONFIG.MOCK_AUTH) {
      result = mockRegister(username, password, email);
    } else {
      result = await apiRegister(username, password, email);
    }

    DOM.registerBtn.textContent = 'CREATE ACCOUNT';
    DOM.registerBtn.disabled = false;

    if (result.ok) {
      showRegisterMsg('✓ Account created! Switching to login…', false);
      // Pre-fill login and switch tab after brief delay
      setTimeout(() => {
        DOM.loginUsername.value = username;
        DOM.loginPassword.value = '';
        switchTab('login');
        DOM.loginPassword.focus();
      }, 1400);
    } else {
      showRegisterMsg(result.message);
    }
  }

  /**
   * Mock register: persists to localStorage so it survives page refresh
   * and is compatible with mockLogin checks above.
   */
  function mockRegister(username, password, email) {
    const lc = username.toLowerCase();

    // Prevent overwriting built-in admin accounts
    if (CONFIG.MOCK_USERS[lc]) {
      return { ok: false, message: 'That username is already taken.' };
    }

    const users = getRegisteredUsers();
    if (users.find(u => u.username.toLowerCase() === lc)) {
      return { ok: false, message: 'Username already exists. Please choose another.' };
    }

    users.push({ username, password, email, created: new Date().toISOString() });
    try {
      localStorage.setItem('conv_registered_users', JSON.stringify(users));
    } catch {
      // localStorage unavailable (private browsing etc.) — session-only
    }
    return { ok: true };
  }

  /** Read registered users from localStorage (with fallback to empty array) */
  function getRegisteredUsers() {
    try {
      return JSON.parse(localStorage.getItem('conv_registered_users') || '[]');
    } catch {
      return [];
    }
  }

  async function apiRegister(username, password, email) {
    try {
      const res  = await fetch(`${CONFIG.API_BASE}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email }),
      });
      const data = await res.json();
      if (res.ok && data.success) return { ok: true };
      const msg = data.detail?.message || data.message || 'Registration failed.';
      return { ok: false, message: msg };
    } catch {
      return { ok: false, message: 'Cannot reach server. Is the backend running?\nRun: uvicorn app:app --reload --port 8000' };
    }
  }

  /* ── Enter the app after successful auth ──────────────────── */
  function enterApp(username, role = 'user') {
    STATE.username = username;
    UI.setUser(username, role);
    DOM.loginOverlay.style.transition = 'opacity 0.45s ease';
    DOM.loginOverlay.style.opacity = '0';
    setTimeout(() => {
      DOM.loginOverlay.classList.add('hidden');
      DOM.app.classList.remove('hidden');
      History.load();
      Belt.buildRibs();
    }, 450);
  }

  /* ── Wire all auth events ─────────────────────────────────── */
  function wireEvents() {
    // Tab clicks
    DOM.tabLogin.addEventListener('click',    () => switchTab('login'));
    DOM.tabRegister.addEventListener('click', () => switchTab('register'));

    // Switch link buttons inside panels
    DOM.goRegister.addEventListener('click', () => switchTab('register'));
    DOM.goLogin.addEventListener('click',    () => switchTab('login'));

    // Login submit
    DOM.loginBtn.addEventListener('click', handleLogin);
    [DOM.loginUsername, DOM.loginPassword].forEach(el =>
      el.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); })
    );

    // Register submit
    DOM.registerBtn.addEventListener('click', handleRegister);
    [DOM.regUsername, DOM.regEmail, DOM.regPassword, DOM.regConfirm].forEach(el =>
      el.addEventListener('keydown', e => { if (e.key === 'Enter') handleRegister(); })
    );
  }

  return { wireEvents };
})();

/* ═══════════════════════════════════════════════════════════════
   5. UI MODULE
   ─────────────────────────────────────────────────────────────
   Score display, user info, dropdown menu, notifications
═══════════════════════════════════════════════════════════════ */
const UI = (() => {

  /* ── User info + dropdown ──────────────────────────────────── */
  function setUser(username, role = 'user') {
    const initial = username.charAt(0).toUpperCase();
    const roleLabel = role === 'admin' ? 'Administrator' : 'User';

    // Trigger button
    DOM.userAvatar.textContent     = initial;
    DOM.usernameDisplay.textContent= username;

    // Dropdown info
    DOM.dropdownAvatar.textContent   = initial;
    DOM.dropdownUsername.textContent = username;
    DOM.dropdownRole.textContent     = roleLabel;
  }

  /* ── Dropdown open / close ─────────────────────────────────── */
  let _dropdownOpen = false;

  function openDropdown() {
    _dropdownOpen = true;
    DOM.userDropdown.classList.remove('hidden');
    DOM.userMenuBtn.setAttribute('aria-expanded', 'true');
    // Focus first item for keyboard nav
    DOM.ddProfile.focus();
  }

  function closeDropdown() {
    _dropdownOpen = false;
    DOM.userDropdown.classList.add('hidden');
    DOM.userMenuBtn.setAttribute('aria-expanded', 'false');
  }

  function toggleDropdown() {
    _dropdownOpen ? closeDropdown() : openDropdown();
  }

  function wireDropdown() {
    // Toggle on button click
    DOM.userMenuBtn.addEventListener('click', e => {
      e.stopPropagation();
      toggleDropdown();
    });

    // Close when clicking anywhere outside
    document.addEventListener('click', e => {
      if (_dropdownOpen && !DOM.userDisplay.contains(e.target)) {
        closeDropdown();
      }
    });

    // Keyboard: Escape closes; arrow keys navigate items
    document.addEventListener('keydown', e => {
      if (!_dropdownOpen) return;
      const items = [...DOM.userDropdown.querySelectorAll('.dropdown-item')];
      const idx   = items.indexOf(document.activeElement);

      if (e.key === 'Escape')      { closeDropdown(); DOM.userMenuBtn.focus(); }
      if (e.key === 'ArrowDown')   { e.preventDefault(); items[(idx + 1) % items.length].focus(); }
      if (e.key === 'ArrowUp')     { e.preventDefault(); items[(idx - 1 + items.length) % items.length].focus(); }
      if (e.key === 'Tab')         { closeDropdown(); }
    });

    // Dropdown menu item actions
    DOM.ddProfile.addEventListener('click', () => {
      closeDropdown();
      showProfileToast();
    });

    DOM.ddScores.addEventListener('click', () => {
      closeDropdown();
      // Scroll to history panel
      document.getElementById('history-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    DOM.ddLogout.addEventListener('click', () => {
      closeDropdown();
      Logout.perform();
    });
  }

  /* ── Profile toast (brief info popup) ────────────────────────  */
  function showProfileToast() {
    const existing = document.getElementById('profile-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'profile-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.innerHTML = `
      <div class="toast-avatar">${STATE.username.charAt(0).toUpperCase()}</div>
      <div class="toast-body">
        <div class="toast-name">${STATE.username}</div>
        <div class="toast-sub">Session active · Score: ${STATE.score}</div>
      </div>
      <button class="toast-close" aria-label="Close">✕</button>
    `;
    document.body.appendChild(toast);
    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());

    // Auto-dismiss after 4 s
    setTimeout(() => toast && toast.remove(), 4000);
  }

  /* ── Score display ─────────────────────────────────────────── */
  function updateScore(value) {
    DOM.scoreValue.textContent = value;
    DOM.scoreValue.className = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
    DOM.sidebarScore.textContent = value;
    DOM.sidebarScore.className = `big-score ${value > 0 ? 'positive' : value < 0 ? 'negative' : ''}`;
  }

  function showDelta(delta) {
    const el = DOM.scoreDelta;
    el.className = '';
    el.textContent = delta > 0 ? `+${delta}` : `${delta}`;
    void el.offsetWidth;
    el.classList.add('show', delta > 0 ? 'up' : 'down');
  }

  function updateAccuracy() {
    const { totalRounds, correctRounds } = STATE;
    if (totalRounds === 0) {
      DOM.accuracyPct.textContent = '—';
      DOM.accuracyFill.style.width = '0%';
      DOM.accuracyBar.setAttribute('aria-valuenow', 0);
      return;
    }
    const pct = Math.round((correctRounds / totalRounds) * 100);
    DOM.accuracyPct.textContent = `${pct}%`;
    DOM.accuracyFill.style.width = `${pct}%`;
    DOM.accuracyBar.setAttribute('aria-valuenow', pct);
    DOM.accuracyFill.style.background =
      pct >= 70 ? 'linear-gradient(90deg, #4C8BFF, #36D68C)'
    : pct >= 40 ? 'linear-gradient(90deg, #FFD060, #FF9C40)'
    :             'linear-gradient(90deg, #FF4C6A, #FF8040)';
  }

  function setStatusDots(mode) {
    DOM.statusDots.forEach(d => d.className = 'status-dot');
    if (mode === 'running') {
      DOM.statusDots.forEach(d => d.classList.add('active'));
    } else if (mode === 'paused') {
      DOM.statusDots.forEach(d => d.classList.add('paused'));
    }
  }

  function setControlStates(status) {
    const idle    = status === 'idle' || status === 'stopped';
    const running = status === 'running';
    const paused  = status === 'paused';
    DOM.btnStart.disabled = running || paused;
    DOM.btnPause.disabled = idle;
    DOM.btnStop.disabled  = idle;
    DOM.btnPause.innerHTML = paused
      ? '<span class="icon" aria-hidden="true">▶</span> RESUME'
      : '<span class="icon" aria-hidden="true">⏸</span> PAUSE';
    DOM.btnPause.setAttribute('aria-label', paused ? 'Resume simulation' : 'Pause simulation');
  }

  return { setUser, wireDropdown, updateScore, showDelta, updateAccuracy, setStatusDots, setControlStates };
})();

/* ═══════════════════════════════════════════════════════════════
   6. BELT MODULE
   ─────────────────────────────────────────────────────────────
   Manages conveyor item animation (CSS transform approach for
   hardware acceleration). Uses a requestAnimationFrame loop to
   track elapsed time so pause/resume works correctly.
═══════════════════════════════════════════════════════════════ */
const Belt = (() => {

  /** Build decorative belt ribs (called once after login) */
  function buildRibs() {
    const belt = DOM.beltLines;
    belt.innerHTML = '';
    const beltW = DOM.beltTrack.offsetWidth || 800;
    const count = Math.ceil(beltW / 40) + 2;
    for (let i = 0; i < count; i++) {
      const line = document.createElement('div');
      line.className = 'belt-line';
      line.style.left = `${i * 40}px`;
      line.style.animationDelay = `${(i * 0.04).toFixed(2)}s`;
      belt.appendChild(line);
    }
  }

  /** Pick a random color from CONFIG.COLORS */
  function randomColor() {
    return CONFIG.COLORS[Math.floor(Math.random() * CONFIG.COLORS.length)];
  }

  /**
   * Spawn a new item on the belt.
   * Uses requestAnimationFrame + elapsed-time math to support pause/resume.
   */
  function spawnItem() {
    if (STATE.status !== 'running') return;

    const color = randomColor();
    STATE.currentColor  = color;
    STATE.selectedColor = null;
    STATE.roundActive   = true;
    STATE.itemElapsedMs = 0;

    // Reset color buttons
    DOM.colorButtons.forEach(btn => {
      btn.classList.remove('selected');
      btn.setAttribute('aria-pressed', 'false');
    });

    // Set item appearance
    const item = DOM.conveyorItem;
    item.className = `item-${color}`;
    item.textContent = color.toUpperCase();
    item.setAttribute('aria-label', `${color} item moving on belt`);

    // Position item just off left edge
    item.style.transition = 'none';
    item.style.left = '-80px';

    // Start raf loop
    STATE.itemStartTime = performance.now();
    scheduleFrame();
  }

  /** rAF loop to update item position and detect reaching end */
  function scheduleFrame() {
    if (STATE.animFrameId) cancelAnimationFrame(STATE.animFrameId);
    STATE.animFrameId = requestAnimationFrame(tick);
  }

  function tick(now) {
    if (STATE.status !== 'running' || !STATE.roundActive) return;

    // Elapsed ms for this item (accumulates across pause/resume)
    const elapsed = STATE.itemElapsedMs + (now - STATE.itemStartTime);
    const progress = Math.min(elapsed / CONFIG.ITEM_TRAVEL_MS, 1);

    // Belt width including start/end offsets
    const beltW = DOM.beltTrack.offsetWidth;
    const startX = -80;
    const endX   = beltW + 20;
    const currentX = startX + (endX - startX) * progress;

    DOM.conveyorItem.style.left = `${currentX}px`;

    if (progress < 1) {
      STATE.animFrameId = requestAnimationFrame(tick);
    } else {
      // Item reached end — evaluate round
      Game.evaluateRound();
    }
  }

  /** Pause belt movement — freezes elapsed counter */
  function pauseItem() {
    if (STATE.animFrameId) {
      cancelAnimationFrame(STATE.animFrameId);
      STATE.animFrameId = null;
    }
    // Accumulate elapsed time so we resume from correct spot
    STATE.itemElapsedMs += performance.now() - STATE.itemStartTime;
  }

  /** Resume belt movement after pause */
  function resumeItem() {
    if (!STATE.roundActive) return;
    STATE.itemStartTime = performance.now();
    scheduleFrame();
  }

  /** Clear the item and reset round state */
  function clearItem() {
    if (STATE.animFrameId) {
      cancelAnimationFrame(STATE.animFrameId);
      STATE.animFrameId = null;
    }
    if (STATE.nextItemTimer) {
      clearTimeout(STATE.nextItemTimer);
      STATE.nextItemTimer = null;
    }
    STATE.roundActive   = false;
    STATE.currentColor  = null;
    STATE.selectedColor = null;
    STATE.itemElapsedMs = 0;

    DOM.conveyorItem.style.left = '-200px';
    DOM.conveyorItem.className  = '';
    DOM.conveyorItem.textContent= '';
    DOM.conveyorItem.setAttribute('aria-label', 'No item on belt');

    DOM.colorButtons.forEach(btn => {
      btn.classList.remove('selected');
      btn.setAttribute('aria-pressed', 'false');
    });
  }

  /** Flash feedback overlay briefly */
  function showFeedback(correct) {
    const overlay = DOM.feedbackOverlay;
    overlay.className = '';
    void overlay.offsetWidth; // reflow
    overlay.textContent = correct ? '✓' : '✗';
    overlay.style.color = correct ? 'rgba(54,214,140,0.9)' : 'rgba(255,76,106,0.9)';
    overlay.classList.add('show');
    overlay.setAttribute('aria-hidden', 'true');
  }

  return { buildRibs, spawnItem, pauseItem, resumeItem, clearItem, showFeedback };
})();

/* ═══════════════════════════════════════════════════════════════
   7. GAME MODULE
   ─────────────────────────────────────────────────────────────
   Core loop: start / pause / stop / reset + scoring
═══════════════════════════════════════════════════════════════ */
const Game = (() => {

  function start() {
    if (STATE.status === 'running' || STATE.status === 'paused') return;
    STATE.status = 'running';
    UI.setStatusDots('running');
    UI.setControlStates('running');
    Belt.spawnItem();
  }

  function pause() {
    if (STATE.status === 'running') {
      STATE.status = 'paused';
      Belt.pauseItem();
      // Pause inter-item timer if active
      if (STATE.nextItemTimer) {
        clearTimeout(STATE.nextItemTimer);
        STATE.nextItemTimer = null;
        STATE._pausedForInterItem = true;
      }
      UI.setStatusDots('paused');
      UI.setControlStates('paused');
    } else if (STATE.status === 'paused') {
      STATE.status = 'running';
      UI.setStatusDots('running');
      UI.setControlStates('running');
      if (STATE._pausedForInterItem) {
        // Was between items — just spawn next
        STATE._pausedForInterItem = false;
        Belt.spawnItem();
      } else {
        Belt.resumeItem();
      }
    }
  }

  function stop() {
    if (STATE.status === 'idle' || STATE.status === 'stopped') return;
    STATE.status = 'stopped';
    Belt.clearItem();
    UI.setStatusDots('stopped');
    UI.setControlStates('stopped');
    // Clear any pending inter-item timer
    if (STATE.nextItemTimer) {
      clearTimeout(STATE.nextItemTimer);
      STATE.nextItemTimer = null;
    }
    STATE._pausedForInterItem = false;
  }

  async function reset() {
    stop();
    // POST score to backend
    await History.saveScore(STATE.username, STATE.score);

    // Reset in-memory score
    STATE.score        = 0;
    STATE.totalRounds  = 0;
    STATE.correctRounds= 0;

    UI.updateScore(0);
    UI.updateAccuracy();
    UI.setControlStates('stopped');
    UI.setStatusDots('idle');
    STATE.status = 'idle';
  }

  /** Called when item reaches end of belt */
  function evaluateRound() {
    STATE.roundActive = false;
    const correct = STATE.selectedColor === STATE.currentColor;

    // Score update
    const delta = correct ? CONFIG.SCORE_CORRECT : CONFIG.SCORE_WRONG;
    STATE.score += delta;
    STATE.totalRounds++;
    if (correct) STATE.correctRounds++;

    UI.updateScore(STATE.score);
    UI.showDelta(delta);
    UI.updateAccuracy();
    Belt.showFeedback(correct);

    // Log the move
    Log.addEntry(STATE.currentColor, STATE.selectedColor, correct);

    // Schedule next item (unless stopped/paused)
    STATE.nextItemTimer = setTimeout(() => {
      STATE.nextItemTimer = null;
      if (STATE.status === 'running') Belt.spawnItem();
    }, CONFIG.INTER_ITEM_DELAY_MS);
  }

  /** Called when a color button is clicked */
  function selectColor(color) {
    if (!STATE.roundActive) return;
    STATE.selectedColor = color;

    // Highlight selection
    DOM.colorButtons.forEach(btn => {
      const isSelected = btn.dataset.color === color;
      btn.classList.toggle('selected', isSelected);
      btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });
  }

  return { start, pause, stop, reset, evaluateRound, selectColor };
})();

/* ═══════════════════════════════════════════════════════════════
   8. LOG MODULE
   ─────────────────────────────────────────────────────────────
   Prepends move entries to the live feed, capping at MAX_LOG_ENTRIES
═══════════════════════════════════════════════════════════════ */
const Log = (() => {

  const COLOR_HEX = { red: '#FF4C6A', blue: '#4C8BFF', green: '#36D68C' };

  function timestamp() {
    const now = new Date();
    return now.toTimeString().slice(0, 8); // HH:MM:SS
  }

  function addEntry(actual, selected, correct) {
    const container = DOM.movesLog;

    // Build entry element
    const entry = document.createElement('div');
    entry.className = `move-entry ${correct ? 'correct' : 'wrong'}`;
    entry.setAttribute('role', 'listitem');

    const dot = document.createElement('div');
    dot.className = 'move-color-dot';
    dot.style.background = COLOR_HEX[actual] || '#aaa';

    const text = document.createElement('span');
    text.className = 'move-text';
    // "Move → [red] | Selected: [blue]"
    const selectedLabel = selected || 'none';
    text.textContent = `Move → [${actual}] | Selected: [${selectedLabel}]`;

    const time = document.createElement('span');
    time.className = 'move-time';
    time.textContent = timestamp();

    entry.appendChild(dot);
    entry.appendChild(text);
    entry.appendChild(time);

    // Prepend (most recent at top)
    container.insertBefore(entry, container.firstChild);

    // Trim to MAX_LOG_ENTRIES
    while (container.children.length > CONFIG.MAX_LOG_ENTRIES) {
      container.removeChild(container.lastChild);
    }
  }

  return { addEntry };
})();

/* ═══════════════════════════════════════════════════════════════
   9. HISTORY MODULE
   ─────────────────────────────────────────────────────────────
   Fetches and displays score history from backend.
   saveScore() POSTs to /api/scores; load() GETs from /api/scores.
═══════════════════════════════════════════════════════════════ */
const History = (() => {

  async function saveScore(user, score) {
    const ts  = new Date().toISOString();
    const row = { user, score, timestamp: ts };   // for local display

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (STATE.jwtToken) headers['Authorization'] = `Bearer ${STATE.jwtToken}`;

      // Backend ScoreReq schema: { score, user?, timestamp? }
      const res = await fetch(`${CONFIG.API_BASE}/api/scores`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ score, user, timestamp: ts }),
      });

      if (res.ok) {
        prependRow(row, true);
      } else if (res.status === 401) {
        console.warn('[Auth] Token rejected when saving score — session may have expired.');
        prependRow(row, true);   // still show locally
      } else {
        const err = await res.json().catch(() => ({}));
        console.warn('[Score] Save failed:', err?.detail || res.status);
        prependRow(row, true);
      }
    } catch (e) {
      console.warn('[History] Backend unreachable — showing score locally:', e.message);
      prependRow(row, true);
    }
  }

  async function load() {
    try {
      const res  = await fetch(`${CONFIG.API_BASE}/api/scores`);
      const data = await res.json();
      renderAll(data);
    } catch (e) {
      renderAll([]);
    }
  }

  function renderAll(rows) {
    const tbody = DOM.historyTbody;
    tbody.innerHTML = '';
    if (!rows || rows.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 3;
      td.innerHTML = '<div class="empty-history">No scores yet</div>';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    rows.forEach(row => prependRow(row, false));
  }

  function prependRow(row, isNew) {
    const tbody = DOM.historyTbody;

    // Remove empty state if present
    const empty = tbody.querySelector('.empty-history');
    if (empty) empty.closest('tr').remove();

    const tr = document.createElement('tr');
    if (isNew) tr.classList.add('new-entry');

    const scoreNum = Number(row.score);
    const pillClass = scoreNum > 0 ? 'pos' : scoreNum < 0 ? 'neg' : 'zero';

    // Format timestamp nicely
    let timeStr = '—';
    try {
      const d = new Date(row.timestamp);
      timeStr = `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (_) {}

    tr.innerHTML = `
      <td><span class="history-user">${escHtml(row.user)}</span></td>
      <td><span class="score-pill ${pillClass}">${scoreNum > 0 ? '+' : ''}${scoreNum}</span></td>
      <td><span class="history-time">${timeStr}</span></td>
    `;

    tbody.insertBefore(tr, tbody.firstChild);
  }

  /** Simple HTML entity escaping */
  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  return { saveScore, load };
})();

/* ═══════════════════════════════════════════════════════════════
   LOGOUT MODULE
   ─────────────────────────────────────────────────────────────
   Stops the game, clears all state, and returns to the login screen.
═══════════════════════════════════════════════════════════════ */
const Logout = (() => {

  function perform() {
    // 1. Stop any running simulation
    if (STATE.status === 'running' || STATE.status === 'paused') {
      Game.stop();
    }

    // 2. Show a brief logout animation on the app shell
    DOM.app.style.transition = 'opacity 0.35s ease';
    DOM.app.style.opacity = '0';

    setTimeout(() => {
      // 3. Reset all state
      STATE.jwtToken      = null;
      STATE.username      = '';
      STATE.score         = 0;
      STATE.totalRounds   = 0;
      STATE.correctRounds = 0;
      STATE.status        = 'idle';

      // 4. Reset UI
      UI.updateScore(0);
      UI.updateAccuracy();
      UI.setControlStates('idle');
      UI.setStatusDots('idle');

      // 5. Clear moves log
      DOM.movesLog.innerHTML = '';

      // 6. Clear score history table
      DOM.historyTbody.innerHTML = '';

      // 7. Clear login form fields
      DOM.loginUsername.value = '';
      DOM.loginPassword.value = '';
      DOM.regUsername.value   = '';
      DOM.regEmail.value      = '';
      DOM.regPassword.value   = '';
      DOM.regConfirm.value    = '';

      // 8. Hide app, show login overlay
      DOM.app.classList.add('hidden');
      DOM.app.style.opacity   = '';
      DOM.app.style.transition= '';

      DOM.loginOverlay.style.opacity   = '0';
      DOM.loginOverlay.style.transition= 'opacity 0.4s ease';
      DOM.loginOverlay.classList.remove('hidden');

      // Switch login tab back to login panel
      DOM.tabLogin.classList.add('active');
      DOM.tabRegister.classList.remove('active');
      DOM.panelLogin.classList.remove('hidden');
      DOM.panelRegister.classList.add('hidden');

      // Clear any auth messages
      [DOM.loginError, DOM.registerMsg].forEach(el => {
        el.className = 'auth-msg hidden';
        el.textContent = '';
      });

      requestAnimationFrame(() => {
        DOM.loginOverlay.style.opacity = '1';
        setTimeout(() => {
          DOM.loginOverlay.style.transition = '';
          DOM.loginUsername.focus();
        }, 410);
      });

    }, 350);
  }

  return { perform };
})();

/* ═══════════════════════════════════════════════════════════════
   10. CONTROLS — wire all button click events
═══════════════════════════════════════════════════════════════ */
function wireControls() {
  DOM.btnStart.addEventListener('click', () => Game.start());
  DOM.btnPause.addEventListener('click', () => Game.pause());
  DOM.btnStop.addEventListener('click',  () => Game.stop());
  DOM.btnReset.addEventListener('click', () => Game.reset());

  // Color buttons
  DOM.colorButtons.forEach(btn => {
    btn.addEventListener('click', () => Game.selectColor(btn.dataset.color));
  });
}

/* ═══════════════════════════════════════════════════════════════
   11. KEYBOARD — global shortcut handler
   ─────────────────────────────────────────────────────────────
   Shortcuts:
     Space      → Start (if idle) / Pause·Resume (if running/paused)
     S          → Stop
     X          → Reset
     R / 1      → Select Red
     B / 2      → Select Blue
     G / 3      → Select Green
     ←  →       → Cycle through color options (arrow keys)
═══════════════════════════════════════════════════════════════ */
function wireKeyboard() {
  const colorOrder = ['red', 'blue', 'green'];
  let focusedColorIdx = 0;

  document.addEventListener('keydown', e => {
    // Don't intercept when typing in login inputs
    if (DOM.loginOverlay && !DOM.loginOverlay.classList.contains('hidden')) return;
    if (document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    switch (e.key) {
      case ' ':
      case 'Space':
        e.preventDefault();
        if (STATE.status === 'idle' || STATE.status === 'stopped') {
          Game.start();
        } else {
          Game.pause();
        }
        break;

      case 's':
      case 'S':
        Game.stop();
        break;

      case 'x':
      case 'X':
        Game.reset();
        break;

      case 'r':
      case 'R':
      case '1':
        Game.selectColor('red');
        highlightColorBtn('red');
        break;

      case 'b':
      case 'B':
      case '2':
        Game.selectColor('blue');
        highlightColorBtn('blue');
        break;

      case 'g':
      case 'G':
      case '3':
        Game.selectColor('green');
        highlightColorBtn('green');
        break;

      case 'ArrowLeft':
        e.preventDefault();
        focusedColorIdx = (focusedColorIdx - 1 + 3) % 3;
        focusColorBtn(colorOrder[focusedColorIdx]);
        break;

      case 'ArrowRight':
        e.preventDefault();
        focusedColorIdx = (focusedColorIdx + 1) % 3;
        focusColorBtn(colorOrder[focusedColorIdx]);
        break;

      case 'Enter':
        // If a color button is focused, select it
        if (document.activeElement && document.activeElement.classList.contains('color-btn')) {
          Game.selectColor(document.activeElement.dataset.color);
        }
        break;
    }
  });

  function focusColorBtn(color) {
    const btn = document.querySelector(`.color-btn[data-color="${color}"]`);
    if (btn) btn.focus();
  }

  function highlightColorBtn(color) {
    const btn = document.querySelector(`.color-btn[data-color="${color}"]`);
    if (btn) {
      btn.classList.add('selected');
      setTimeout(() => {}, 50); // visual only; actual state set in selectColor
    }
  }
}

/* ═══════════════════════════════════════════════════════════════
   12. INIT — Boot sequence
═══════════════════════════════════════════════════════════════ */
function init() {
  cacheDOM();
  Auth.wireEvents();
  wireControls();
  wireKeyboard();
  UI.wireDropdown();   // ← user menu dropdown + logout

  // Initialise UI to idle state
  UI.setControlStates('idle');
  UI.setStatusDots('idle');

  // Focus username field on load
  DOM.loginUsername.focus();
}

// Run when DOM is ready (script is deferred so this is always safe)
document.addEventListener('DOMContentLoaded', init); 