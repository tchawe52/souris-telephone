"""
Cedric souris pc : serveur Windows (fenêtre avec IP + PIN).
Le téléphone sert de souris/trackpad via WiFi ou câble USB.
"""
import asyncio
import json
import os
import random
import socket
import threading
import tkinter as tk

from aiohttp import web, WSMsgType
from pynput.mouse import Button, Controller

PORT = 8765
mouse = Controller()
BUTTONS = {"left": Button.left, "right": Button.right}

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Cedric souris pc</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: none; }
  html, body { margin: 0; height: 100%; background: #0f1115; color: #e8eaf0; font-family: system-ui, sans-serif; overflow: hidden; }
  #app { display: flex; flex-direction: column; height: 100%; padding: 10px; gap: 10px; }
  #top { display: flex; align-items: center; gap: 10px; font-size: 14px; }
  #dot { width: 10px; height: 10px; border-radius: 50%; background: #e5484d; }
  #dot.ok { background: #30a46c; }
  #top input { flex: 1; }
  #pad { flex: 1; border-radius: 18px; background: #1a1d24; border: 2px dashed #353a46; display: flex; align-items: center; justify-content: center; color: #6b7280; text-align: center; padding: 20px; line-height: 1.6; }
  #btns { display: flex; gap: 10px; height: 22%; }
  .b { flex: 1; border-radius: 18px; background: #262a34; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; }
  .b.on { background: #3e63dd; }
</style>
</head>
<body>
<div id="app">
  <div id="top">
    <div id="dot"></div><span id="st">Connexion…</span>
    <input id="sens" type="range" min="0.5" max="4" step="0.1" value="1.6" aria-label="Sensibilité">
  </div>
  <div id="pad">1 doigt : déplacer<br>Toucher : clic gauche<br>2 doigts touchés : clic droit<br>2 doigts glissés : défiler</div>
  <div id="btns">
    <div class="b" id="bl">Clic gauche</div>
    <div class="b" id="br">Clic droit</div>
  </div>
</div>
<script>
const params = new URLSearchParams(location.search);
const k = params.get('k') || prompt('Code PIN affiché sur le PC');
const dot = document.getElementById('dot'), st = document.getElementById('st');
const sens = document.getElementById('sens');
let ws;

function connect() {
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws?k=' + encodeURIComponent(k));
  ws.onopen = () => { dot.className = 'ok'; st.textContent = 'Connecté'; };
  ws.onclose = () => { dot.className = ''; st.textContent = 'Déconnecté'; setTimeout(connect, 1500); };
}
connect();
const send = o => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); };

// --- Envoi groupé des mouvements (1 fois par frame) ---
let ax = 0, ay = 0, sy = 0;
function loop() {
  if (ax || ay) {
    const dx = Math.trunc(ax), dy = Math.trunc(ay);
    if (dx || dy) { send({ t: 'move', dx, dy }); ax -= dx; ay -= dy; }
  }
  if (Math.abs(sy) >= 1) {
    const s = Math.trunc(sy); send({ t: 'scroll', dy: s }); sy -= s;
  }
  requestAnimationFrame(loop);
}
loop();

// --- Pavé tactile ---
const pad = document.getElementById('pad');
let lx = 0, ly = 0, startT = 0, moved = 0, maxTouches = 0;

const center = ts => {
  let x = 0, y = 0;
  for (const t of ts) { x += t.clientX; y += t.clientY; }
  return [x / ts.length, y / ts.length];
};

pad.addEventListener('touchstart', e => {
  e.preventDefault();
  if (e.touches.length === 1) { startT = Date.now(); moved = 0; maxTouches = 1; }
  maxTouches = Math.max(maxTouches, e.touches.length);
  [lx, ly] = center(e.touches);
}, { passive: false });

pad.addEventListener('touchmove', e => {
  e.preventDefault();
  const [x, y] = center(e.touches);
  const dx = x - lx, dy = y - ly;
  lx = x; ly = y;
  moved += Math.abs(dx) + Math.abs(dy);
  if (e.touches.length >= 2) {
    sy += -dy / 8;                         // défilement (sens naturel)
  } else {
    const speed = Math.hypot(dx, dy);
    const mult = parseFloat(sens.value) * (1 + Math.min(speed / 15, 2));
    ax += dx * mult; ay += dy * mult;
  }
}, { passive: false });

pad.addEventListener('touchend', e => {
  e.preventDefault();
  if (e.touches.length === 0) {
    if (moved < 12 && Date.now() - startT < 250) {
      send({ t: 'click', b: maxTouches >= 2 ? 'right' : 'left' });
    }
    maxTouches = 0;
  } else {
    [lx, ly] = center(e.touches);
  }
}, { passive: false });

// --- Boutons clic gauche / droit (maintenir = glisser-déposer) ---
function bindBtn(id, name) {
  const el = document.getElementById(id);
  el.addEventListener('touchstart', e => { e.preventDefault(); el.classList.add('on'); send({ t: 'down', b: name }); }, { passive: false });
  const up = e => { e.preventDefault(); el.classList.remove('on'); send({ t: 'up', b: name }); };
  el.addEventListener('touchend', up, { passive: false });
  el.addEventListener('touchcancel', up, { passive: false });
}
bindBtn('bl', 'left');
bindBtn('br', 'right');
</script>
</body>
</html>
"""


# ---------- PIN (gardé d'une fois sur l'autre) ----------
def pin_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "CedricSourisPC")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "pin.txt")


def gen_pin():
    return f"{random.randint(0, 9999):04d}"


def load_pin():
    try:
        with open(pin_path(), encoding="utf-8") as f:
            p = f.read().strip()
            if len(p) == 4 and p.isdigit():
                return p
    except OSError:
        pass
    p = gen_pin()
    save_pin(p)
    return p


def save_pin(p):
    try:
        with open(pin_path(), "w", encoding="utf-8") as f:
            f.write(p)
    except OSError:
        pass


PIN = load_pin()


# ---------- Adresses IP du PC ----------
def local_ips():
    ips = []
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
    except OSError:
        pass
    finally:
        s.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(("127.", "169.254.")) and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips or ["Aucune adresse : connecte le PC au WiFi"]


# ---------- Serveur ----------
async def index(request):
    return web.Response(text=HTML, content_type="text/html")


async def ws_handler(request):
    if request.query.get("k") != PIN:
        return web.Response(status=403, text="PIN invalide")
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    async for msg in ws:
        if msg.type != WSMsgType.TEXT:
            continue
        try:
            d = json.loads(msg.data)
            t = d.get("t")
            if t == "move":
                mouse.move(int(d["dx"]), int(d["dy"]))
            elif t == "click":
                mouse.click(BUTTONS[d["b"]])
            elif t == "down":
                mouse.press(BUTTONS[d["b"]])
            elif t == "up":
                mouse.release(BUTTONS[d["b"]])
            elif t == "scroll":
                mouse.scroll(0, int(d["dy"]))
        except Exception:
            pass
    for b in BUTTONS.values():
        mouse.release(b)
    return ws


state = {"status": "Démarrage…"}


def server_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        app = web.Application()
        app.router.add_get("/", index)
        app.router.add_get("/ws", ws_handler)
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        loop.run_until_complete(site.start())
        state["status"] = "En marche : le téléphone peut se connecter"
        loop.run_forever()
    except Exception as exc:
        state["status"] = f"Erreur : {exc}"


# ---------- Fenêtre ----------
BG, FG, MUTED, ACCENT = "#14161b", "#e8eaf0", "#8b93a7", "#3e63dd"

root = tk.Tk()
root.title("Cedric souris pc")
root.geometry("440x420")
root.resizable(False, False)
root.configure(bg=BG)

tk.Label(root, text="Cedric souris pc", font=("Segoe UI", 20, "bold"), bg=BG, fg=FG).pack(pady=(18, 4))
status_var = tk.StringVar(value=state["status"])
tk.Label(root, textvariable=status_var, font=("Segoe UI", 10), bg=BG, fg=MUTED, wraplength=400).pack()

tk.Label(root, text="Adresse IP du PC (à taper dans l'app)", font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(pady=(22, 2))
tk.Label(root, text="\n".join(local_ips()), font=("Consolas", 18, "bold"), bg=BG, fg=FG).pack()

tk.Label(root, text="Code PIN", font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(pady=(22, 2))
pin_var = tk.StringVar(value=PIN)
tk.Label(root, textvariable=pin_var, font=("Consolas", 36, "bold"), bg=BG, fg=ACCENT).pack()


def change_pin():
    global PIN
    PIN = gen_pin()
    save_pin(PIN)
    pin_var.set(PIN)


row = tk.Frame(root, bg=BG)
row.pack(pady=22)
tk.Button(row, text="Nouveau PIN", command=change_pin, font=("Segoe UI", 11), width=14).pack(side="left", padx=6)
tk.Button(row, text="Quitter", command=root.destroy, font=("Segoe UI", 11), width=14).pack(side="left", padx=6)

tk.Label(
    root,
    text="Garde cette fenêtre ouverte pendant l'utilisation.",
    font=("Segoe UI", 9), bg=BG, fg=MUTED,
).pack()


def refresh():
    status_var.set(state["status"])
    root.after(500, refresh)


threading.Thread(target=server_thread, daemon=True).start()
refresh()
root.mainloop()
