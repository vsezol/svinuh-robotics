// Experiment: control over raw UDP instead of a web server. The robot
// joins an existing WiFi network (station mode, same network as your
// computer) and listens for tiny UDP packets. The control page itself
// lives on your computer (see server/) - this firmware only serves the
// camera feed (a small MJPEG endpoint), nothing else.
//
// Wire protocol:
//   F/B/L/R/S   move forward/backward/left/right, or stop
//   V<0-255>    set drive speed
//   D<0-255>    set LED brightness
//   PING        -> robot replies PONG (lets server/app.py find it)
//
// Copy secrets.h.example to secrets.h and fill in your WiFi network before
// flashing (secrets.h is gitignored, never committed).

#include <WiFi.h>
#include <WiFiUdp.h>
#include "secrets.h"

void initCameraStream();

const uint16_t UDP_PORT = 4210;
const unsigned long COMMAND_TIMEOUT_MS = 400; // auto-stop if packets stop arriving

// Same pins as web-cam-manual's L298N wiring.
int gpLb = 14, gpLf = 13, gpRb = 33, gpRf = 15, gpLed = 4, ENR = 2, ENL = 12;
int speed = 220;

WiFiUDP udp;
unsigned long lastCommandAt = 0;
bool moving = false;

void WheelAct(int speedR, int speedL, int nLf, int nLb, int nRf, int nRb) {
  ledcWrite(ENR, speedR);
  ledcWrite(ENL, speedL);
  digitalWrite(gpLf, nLf);
  digitalWrite(gpLb, nLb);
  digitalWrite(gpRf, nRf);
  digitalWrite(gpRb, nRb);
}

void handleCommand(char *buf, int len, IPAddress remoteIp, uint16_t remotePort) {
  if (len == 4 && !strncmp(buf, "PING", 4)) {
    udp.beginPacket(remoteIp, remotePort);
    udp.write((const uint8_t *)"PONG", 4);
    udp.endPacket();
    return;
  }

  switch (buf[0]) {
    case 'F': WheelAct(speed, speed, HIGH, LOW, HIGH, LOW); moving = true; break;
    case 'B': WheelAct(speed, speed, LOW, HIGH, LOW, HIGH); moving = true; break;
    case 'L': WheelAct(speed, speed, HIGH, LOW, LOW, HIGH); moving = true; break;
    case 'R': WheelAct(speed, speed, LOW, HIGH, HIGH, LOW); moving = true; break;
    case 'S': WheelAct(0, 0, LOW, LOW, LOW, LOW); moving = false; break;
    case 'V': speed = constrain(atoi(buf + 1), 0, 255); break;
    case 'D': ledcWrite(gpLed, constrain(atoi(buf + 1), 0, 255)); break;
  }
  lastCommandAt = millis();
}

void setup() {
  Serial.begin(115200);

  pinMode(gpLb, OUTPUT);
  pinMode(gpLf, OUTPUT);
  pinMode(gpRb, OUTPUT);
  pinMode(gpRf, OUTPUT);
  pinMode(gpLed, OUTPUT);
  ledcAttach(ENR, 5000, 8);
  ledcAttach(ENL, 5000, 8);
  ledcAttach(gpLed, 5000, 8);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected, IP: ");
  Serial.println(WiFi.localIP());

  udp.begin(UDP_PORT);
  Serial.printf("Listening for UDP on port %u\n", UDP_PORT);

  initCameraStream();
}

void loop() {
  int packetSize = udp.parsePacket();
  if (packetSize > 0 && packetSize < 16) {
    char buf[16] = {0};
    int len = udp.read(buf, sizeof(buf) - 1);
    handleCommand(buf, len, udp.remoteIP(), udp.remotePort());
  }

  // No connection to watch, so no connection to notice dropping - if
  // commands just stop arriving (WiFi hiccup, client crash), stop driving
  // instead of coasting on the last command forever.
  if (moving && millis() - lastCommandAt > COMMAND_TIMEOUT_MS) {
    WheelAct(0, 0, LOW, LOW, LOW, LOW);
    moving = false;
  }
}
