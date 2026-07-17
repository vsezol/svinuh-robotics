// Wire protocol to the robot over WebSocket (ws://<host>/ws):
//   F / B / L / R / S   move forward / backward / left / right / stop (1 byte)
//   V<0-255>            set drive speed, e.g. "V220"
//   D<0-255>            set LED brightness, e.g. "D128"
// Every control used to be its own HTTP GET (~300+ bytes, fresh TCP
// connection each time). One open WebSocket now costs 1-4 bytes per command.

const host = location.hostname;

let ws;
function connect() {
  ws = new WebSocket(`ws://${host}/ws`);
  ws.onclose = () => setTimeout(connect, 500);
  ws.onerror = () => ws.close();
}
connect();

function send(cmd) {
  if (ws.readyState === WebSocket.OPEN) ws.send(cmd);
}

// ---- Movement: hold to move, release to stop. Pointer and WASD both
// drive the same press/release pair, so a keypress lights up the on-screen
// button exactly like touching it would. ----
const DPAD = { forward: 'F', backward: 'B', turnleft: 'L', turnright: 'R' };
const pressed = new Set();

function press(id) {
  if (pressed.has(id)) return; // ignore key auto-repeat
  pressed.add(id);
  document.getElementById(id).classList.add('pressed');
  send(DPAD[id]);
}
function release(id) {
  pressed.delete(id);
  document.getElementById(id).classList.remove('pressed');
  send('S');
}

for (const id in DPAD) {
  const el = document.getElementById(id);
  el.addEventListener('pointerdown', (ev) => { ev.preventDefault(); press(id); });
  el.addEventListener('pointerup', (ev) => { ev.preventDefault(); release(id); });
  el.addEventListener('pointerleave', (ev) => { ev.preventDefault(); release(id); });
  el.addEventListener('pointercancel', (ev) => { ev.preventDefault(); release(id); });
}

const KEY_TO_ID = { w: 'forward', s: 'backward', a: 'turnleft', d: 'turnright' };
document.addEventListener('keydown', (ev) => {
  const id = KEY_TO_ID[ev.key.toLowerCase()];
  if (id) press(id);
});
document.addEventListener('keyup', (ev) => {
  const id = KEY_TO_ID[ev.key.toLowerCase()];
  if (id) release(id);
});
// Don't leave the robot driving if the tab loses focus mid-keypress.
window.addEventListener('blur', () => [...pressed].forEach(release));

// ---- Speed / LED sliders: throttle while dragging, always send final value ----
function bindSlider(id, prefix, throttleMs) {
  const el = document.getElementById(id);
  let last = 0;
  el.addEventListener('input', () => {
    const now = Date.now();
    if (now - last < throttleMs) return;
    last = now;
    send(prefix + el.value);
  });
  el.addEventListener('change', () => send(prefix + el.value));
}
bindSlider('speed', 'V', 100);
bindSlider('flash', 'D', 100);

// ---- Camera stream ----
const stream = document.getElementById('stream');
const toggleBtn = document.getElementById('toggle-stream');
const stillBtn = document.getElementById('get-still');
const closeBtn = document.getElementById('close-stream');

function startStream() {
  stream.src = `http://${host}:81/stream`;
  toggleBtn.textContent = 'Stop screen';
}
function stopStream() {
  window.stop();
  toggleBtn.textContent = 'Start screen';
}
toggleBtn.onclick = () => {
  if (toggleBtn.textContent === 'Stop screen') stopStream();
  else startStream();
};
stillBtn.onclick = () => {
  stopStream();
  stream.src = `http://${host}/capture?_cb=${Date.now()}`;
};
closeBtn.onclick = () => {
  stopStream();
  stream.removeAttribute('src');
};
