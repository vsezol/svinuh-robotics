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

// ---- Movement: hold to move, release to stop ----
function bindHold(id, cmd) {
  const el = document.getElementById(id);
  const press = (ev) => { ev.preventDefault(); send(cmd); };
  const release = (ev) => { ev.preventDefault(); send('S'); };
  el.addEventListener('pointerdown', press);
  el.addEventListener('pointerup', release);
  el.addEventListener('pointerleave', release);
  el.addEventListener('pointercancel', release);
}
bindHold('forward', 'F');
bindHold('backward', 'B');
bindHold('turnleft', 'L');
bindHold('turnright', 'R');

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
