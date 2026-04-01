# 🚀 AI Conveyor Color Segregation System

A production-ready, web-based industrial simulation built with **Vanilla JS + FastAPI + SQLite**.

---

## 📁 Project Structure

```
color-segregation-openenv/
│
├── static/
│   ├── index.html      ← Single-page application shell
│   ├── style.css       ← All styling & animations (glassmorphism, belt, etc.)
│   ├── script.js       ← Complete front-end logic (auth, game, API calls)
│   └── logo.svg        ← Accessible SVG logo (three colored dots)
│
├── app.py              ← FastAPI backend (auth, scores API, static serving)
├── inference.py        ← AI classification stub (swap in real model here)
├── openenv.yaml        ← Environment configuration template
└── README.md           ← This file
```

---

## ⚡ Quick Start

### 1 — Prerequisites

- **Python 3.10+**
- `pip` package manager

### 2 — Install dependencies

```bash
pip install fastapi uvicorn python-multipart pyyaml
# Optional (enables pixel-average heuristic in inference.py):
pip install Pillow
```

### 3 — Configure (optional)

Edit `openenv.yaml` or set environment variables:

```bash
# Example overrides
export FASTAPI_PORT=8000
export SECRET_KEY="your-real-secret-here"
export DB_PATH="scores.db"
```

### 4 — Run the backend

```bash
uvicorn app:app --reload --port 8000
```

You should see:
```
[DB] Initialised SQLite at 'scores.db'
[APP] AI Conveyor backend running on port 8000 (debug=True)
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5 — Open in browser

```
http://localhost:8000
```

---

## 🔑 Login Credentials (Mock Auth)

| Username | Password |
|----------|----------|
| admin    | admin    |
| demo     | demo     |
| user     | password |

> To add or change users, edit `MOCK_USERS` in `app.py`.  
> To disable mock auth and use a real user database, set `MOCK_AUTH: "false"` in `openenv.yaml` and implement real user lookup in `app.py`.

---

## 🎮 How to Play

1. **Login** with any credential above.
2. Press **▶ START** (or `Space`) to start the simulation.
3. A colored block (Red / Blue / Green) will travel across the belt.
4. **Click the matching color button** (or use a keyboard shortcut) **before the item reaches the right end**.
5. Scoring: **Correct → +5 pts** | **Wrong or missed → −10 pts**.
6. Press **🔄 RESET** to save your score to the database and start fresh.

---

## ⌨️ Keyboard Shortcuts

| Key          | Action                          |
|--------------|---------------------------------|
| `Space`      | Start (idle) / Pause·Resume     |
| `S`          | Stop simulation                 |
| `X`          | Reset & save score              |
| `R` or `1`   | Select **Red**                  |
| `B` or `2`   | Select **Blue**                 |
| `G` or `3`   | Select **Green**                |
| `←` / `→`    | Cycle color button focus        |
| `Enter`      | Confirm focused color button    |

---

## 🌐 API Reference

### `POST /api/login`
Authenticate and create a session.

**Request body:**
```json
{ "username": "admin", "password": "admin" }
```

**Response (200):**
```json
{ "success": true, "username": "admin" }
```
Sets an `httponly` session cookie (`session_token`).

---

### `POST /api/scores`
Save a score record.

**Request body:**
```json
{ "user": "admin", "score": 35, "timestamp": "2025-01-15T10:30:00Z" }
```

**Response (200):**
```json
{ "success": true, "message": "Score saved." }
```

---

### `GET /api/scores`
Retrieve score history (newest first, max 200).

**Response (200):**
```json
[
  { "user": "admin", "score": 35, "timestamp": "2025-01-15T10:30:00Z" },
  ...
]
```

---

### `GET /api/status`
Health check.

**Response (200):**
```json
{ "status": "ok", "timestamp": "...", "db": "scores.db", "debug": true }
```

---

## 🗄️ Database

- Engine: **SQLite** (Python built-in `sqlite3`)
- Default file: `scores.db` (created automatically in the project root)
- Table: `scores (id, username, score, timestamp)`
- To inspect: `sqlite3 scores.db "SELECT * FROM scores ORDER BY id DESC LIMIT 10;"`
- To reset: delete `scores.db` and restart the server.

To switch to PostgreSQL or MySQL, replace `get_db()` in `app.py` with an async driver (e.g., `asyncpg`, `aiomysql`) and update the `CREATE TABLE` DDL.

---

## 🤖 AI Inference (inference.py)

`inference.py` contains a stub `classify_color(image_or_patch)` function.

**Current behaviour:** Returns a random color (`red`/`blue`/`green`) for demo purposes.

**To wire in a real AI model:**
1. Train or download a color classifier (PyTorch, TensorFlow, ONNX, etc.).
2. Replace `_stub_classify()` in `inference.py` with real model inference (see docstring examples).
3. Set `ENABLE_INFERENCE_ENDPOINT: "true"` in `openenv.yaml`.
4. Add a `POST /api/classify` route in `app.py` that accepts base64 image → calls `classify_color()` → returns predicted color.
5. Call the endpoint from `script.js` (in `Belt.spawnItem()`) instead of using the JS client-side random picker.

---

## 🧪 Testing Checklist

### Functional

- [ ] **Login** — Enter valid credentials → app loads, username appears in header.
- [ ] **Invalid login** — Wrong password → error message shown, form shakes.
- [ ] **Enter key** — Pressing Enter in password field submits form.
- [ ] **Start** — Click ▶ START → item appears and moves across belt.
- [ ] **Color select** — Click Red/Blue/Green during item movement → button highlights.
- [ ] **Correct answer** — Select matching color → green ✓ flash, score +5.
- [ ] **Wrong answer** — Select wrong color → red ✗ flash, score −10.
- [ ] **Missed round** — Let item pass without selection → score −10.
- [ ] **Pause** — Click ⏸ PAUSE → item freezes mid-belt; click RESUME → continues from same position.
- [ ] **Stop** — Click ⏹ STOP → item disappears, no new items spawn.
- [ ] **Reset** — Click 🔄 RESET → score saved to DB, score resets to 0, history row appears.
- [ ] **History table** — After Reset, new row appears at top of score history.
- [ ] **Moves log** — Each round appends entry (latest at top).
- [ ] **Keyboard shortcuts** — Space, S, X, R/B/G, 1/2/3 all work.
- [ ] **API health** — `curl http://localhost:8000/api/status` returns `{"status":"ok",...}`.
- [ ] **Score persistence** — Restart backend → `GET /api/scores` still returns saved scores.

### Accessibility

- [ ] All interactive elements focusable via Tab.
- [ ] Login form submits on Enter.
- [ ] Color buttons have `aria-pressed` that updates on selection.
- [ ] Moves log has `aria-live="polite"` and updates screen readers.
- [ ] Score value in header has `aria-live="polite"`.
- [ ] Focus rings visible on all buttons.
- [ ] Sufficient contrast (test with browser DevTools / axe extension).

### Browser Compatibility

Tested on (no transpilation required — vanilla JS, no bundler):

| Browser         | Status |
|-----------------|--------|
| Chrome 120+     | ✅     |
| Firefox 121+    | ✅     |
| Safari 17+      | ✅     |
| Edge 120+       | ✅     |
| Mobile Chrome   | ✅     |
| Mobile Safari   | ✅     |

> **Note:** `backdrop-filter` (glassmorphism) requires Safari 9+, Chrome 76+, Firefox 103+. Degrades gracefully on older browsers (no blur, still functional).

---

## 🔧 Configuration Reference (`openenv.yaml`)

| Key                       | Default          | Description                                      |
|---------------------------|------------------|--------------------------------------------------|
| `FASTAPI_PORT`            | `8000`           | Port for uvicorn                                 |
| `DB_PATH`                 | `scores.db`      | SQLite database file path                        |
| `DEBUG`                   | `true`           | Enable verbose logging and auto-reload           |
| `SECRET_KEY`              | random on boot   | Session signing key — **change in production**   |
| `CORS_ORIGINS`            | `*`              | Allowed origins (tighten in production)          |
| `MOCK_AUTH`               | `true`           | Use built-in mock users                          |
| `ENABLE_INFERENCE_ENDPOINT`| `false`         | Expose POST /api/classify route                  |

Environment variables override YAML values.

---

## 🎨 Customisation

### Timing & Scoring (`script.js` → `CONFIG`)

```js
const CONFIG = {
  ITEM_TRAVEL_MS:     4500,   // ms for item to cross belt
  INTER_ITEM_DELAY_MS: 900,   // ms pause between items
  SCORE_CORRECT:        5,    // pts for correct answer
  SCORE_WRONG:        -10,    // pts for wrong / missed
  MAX_LOG_ENTRIES:     20,    // max moves log entries
  MOCK_AUTH:           true,  // true = JS-side mock auth
};
```

### Theme (`style.css` → `:root`)

```css
:root {
  --bg-from:     #0d1b3e;   /* gradient start */
  --bg-mid:      #1a0a3c;   /* gradient mid   */
  --bg-to:       #0b0c2a;   /* gradient end   */
  --accent-red:  #FF4C6A;
  --accent-blue: #4C8BFF;
  --accent-green:#36D68C;
  --item-duration: 4s;       /* belt item CSS fallback */
}
```

---

## ⚠️ Known Limitations

1. **Mock auth only** — No real password hashing or user registration. For production, add a `users` table and use `bcrypt`.
2. **In-memory sessions** — `_sessions` dict in `app.py` is lost on server restart. Use Redis or a DB-backed session store in production.
3. **No WebSocket** — Game state is client-side only; no server sync of running/paused state.
4. **Single player** — No multi-user real-time features.
5. **Google Fonts** — Loaded from CDN for typography. Remove the `@import` in `style.css` and use system fonts for full offline / privacy mode.
6. **SQLite concurrency** — SQLite handles moderate load fine for a local demo; swap to PostgreSQL for multi-user production deployments.

---

## 📜 License

MIT — free to use and modify for any purpose.

---

*Built with ❤️ using FastAPI + Vanilla JS + SQLite.*