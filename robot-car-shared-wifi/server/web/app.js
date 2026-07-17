// This page and the server serving it both run on YOUR computer
// (server/app.py), which forwards each command as one UDP packet to the
// robot - see robot-car-shared-wifi.ino for the wire protocol. Video is NOT proxied
// through this server: the <img> below loads it directly from the robot.

let robotIp = null;
const configReady = fetch('/config').then(r => r.json()).then(cfg => { robotIp = cfg.robotIp; });

function send(cmd) {
  fetch(`/cmd?c=${cmd}`).catch(() => {});
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

// ---- Camera stream: loaded straight from the robot's own MJPEG endpoint,
// not proxied through this server. ----
const stream = document.getElementById('stream');
const toggleBtn = document.getElementById('toggle-stream');
const closeBtn = document.getElementById('close-stream');

function startStream() {
  configReady.then(() => {
    if (!robotIp) {
      alert("Don't know the robot's IP - check the terminal running server/app.py.");
      return;
    }
    stream.src = `http://${robotIp}:81/stream`;
    toggleBtn.textContent = 'Stop screen';
  });
}
function stopStream() {
  window.stop();
  toggleBtn.textContent = 'Start screen';
}
toggleBtn.onclick = () => {
  if (toggleBtn.textContent === 'Stop screen') stopStream();
  else startStream();
};
closeBtn.onclick = () => {
  stopStream();
  stream.removeAttribute('src');
};
