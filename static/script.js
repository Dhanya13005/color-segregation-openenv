'use strict';

/* ================= CONFIG ================= */
const CONFIG = {
  ITEM_SPEED: 4500,
  DELAY: 1200,
  SCORE_CORRECT: 5,
  SCORE_WRONG: -10,
  COLORS: ['red', 'blue', 'green'],

  // ✅ UPDATED USERS (YOUR EMAIL ADDED)
  MOCK_AUTH: true,
  MOCK_USERS: {
    admin: 'admin',
    demo: 'demo',
    user: 'password',
    "2300032840@kluniversity.in": "123"
  }
};

/* ================= STATE ================= */
let state = {
  running: false,
  paused: false,
  currentColor: null,
  selectedColor: null,
  score: 0
};

/* ================= DOM ================= */
const loginOverlay = document.getElementById("login-overlay");
const loginBtn = document.getElementById("login-btn");
const usernameInput = document.getElementById("login-username");
const passwordInput = document.getElementById("login-password");
const loginError = document.getElementById("login-error");

const app = document.getElementById("app");
const usernameDisplay = document.getElementById("username-display");

const item = document.getElementById("conveyor-item");
const scoreEl = document.getElementById("score-value");
const logEl = document.getElementById("moves-log");

const btnStart = document.getElementById("btn-start");
const btnPause = document.getElementById("btn-pause");
const btnStop = document.getElementById("btn-stop");
const btnReset = document.getElementById("btn-reset");

const colorButtons = document.querySelectorAll(".color-btn");

/* ================= LOGIN ================= */

loginBtn.onclick = () => {
  const user = usernameInput.value.trim();
  const pass = passwordInput.value;

  if (!user || !pass) {
    loginError.innerText = "Enter username & password";
    loginError.classList.remove("hidden");
    return;
  }

  if (CONFIG.MOCK_USERS[user] === pass) {
    // ✅ SUCCESS LOGIN
    loginOverlay.style.display = "none";
    app.classList.remove("hidden");
    usernameDisplay.innerText = user;
  } else {
    loginError.innerText = "Invalid credentials";
    loginError.classList.remove("hidden");
  }
};

/* ================= UTILS ================= */

function randomColor() {
  return CONFIG.COLORS[Math.floor(Math.random() * CONFIG.COLORS.length)];
}

function updateScore(val) {
  state.score += val;
  scoreEl.textContent = state.score;
}

function logMove(text, type) {
  const div = document.createElement("div");
  div.className = "move-entry " + type;
  div.innerHTML = `→ ${text} <span>${new Date().toLocaleTimeString()}</span>`;
  logEl.prepend(div);
}

/* ================= GAME ================= */

function spawnItem() {
  if (!state.running || state.paused) return;

  state.currentColor = randomColor();
  state.selectedColor = null;

  item.className = "item-" + state.currentColor;
  item.style.left = "-80px";

  let start = Date.now();

  function move() {
    if (!state.running) return;
    if (state.paused) {
      requestAnimationFrame(move);
      return;
    }

    let progress = (Date.now() - start) / CONFIG.ITEM_SPEED;
    let x = progress * window.innerWidth;

    item.style.left = x + "px";

    if (progress >= 1) {
      evaluate();
      return;
    }

    requestAnimationFrame(move);
  }

  move();
}

/* ================= EVALUATION ================= */

function evaluate() {
  let correct = state.selectedColor === state.currentColor;

  if (correct) {
    updateScore(CONFIG.SCORE_CORRECT);
    logMove(`${state.currentColor} correct`, "correct");
  } else {
    updateScore(CONFIG.SCORE_WRONG);
    logMove(`${state.currentColor} wrong`, "wrong");
  }

  item.style.left = "-200px";

  setTimeout(spawnItem, CONFIG.DELAY);
}

/* ================= BUTTONS ================= */

btnStart.onclick = () => {
  if (state.running) return;

  state.running = true;
  state.paused = false;
  spawnItem();
};

btnPause.onclick = () => {
  if (!state.running) return;

  state.paused = !state.paused;
  btnPause.innerText = state.paused ? "▶ Resume" : "⏸ Pause";
};

btnStop.onclick = () => {
  state.running = false;
  state.paused = false;
  item.style.left = "-200px";
};

btnReset.onclick = () => {
  state.running = false;
  state.paused = false;
  state.score = 0;
  scoreEl.textContent = 0;
  logEl.innerHTML = "";
  item.style.left = "-200px";
};

/* ================= COLOR SELECT ================= */

colorButtons.forEach(btn => {
  btn.onclick = () => {
    if (!state.running) return;

    state.selectedColor = btn.dataset.color;

    colorButtons.forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
  };
});