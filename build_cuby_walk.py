"""
CUBY Walk Engine Generator — V1.23 (hardware-confirmed)

Purpose:
  Generates CUBY_walk_turn.json for the Bambu Lab CyberBrick receiver.
  Coordinated biped walking/turning via an injected Python CODE effect,
  with operator-chosen eye colors on a separate native LED path.

Architecture (three layers):
  1. Sender events  — button starts CODE; R-shoulder stick cycles LED1
  2. Native actuators — PWM servos (enabled, no direct stick controls);
                        LED1 effects defined in baseline
  3. Python CODE effect — while-True gait loop reads rc_slave_data(),
                          drives all four servos via ServosController

Why not the designer V1.1 approach:
  CUBY_V1.1.json maps each stick axis directly to one servo (native controls).
  That responds instantly at power-up but cannot coordinate a walking gait.
  We clear joystick controls and own servos in Python instead.

Confirmed capabilities (bench-tested V1.23):
  - L Shoulder Button starts the walk engine (CODE effect 1)
  - L Stick Y: forward / backward walking gait
  - R Stick X: turn left / right in place
  - L Stick X / R Stick Y: idle pose adjustments (lean, bow)
  - R Shoulder Stick up/down: cycles LED1 eyes (green/red/blue/off/white);
    color latches at neutral; independent of movement
  - L Shoulder 3-Pos: unused (no events wired)
  - Repeat button press restarts the engine (no singleton guard)

Failed approaches (documented for future reference):
  - CODE initial_value auto-boot (V1.16): does not start on this hardware
  - Joystick events firing CODE (V1.17–V1.18): never triggered the effect
  - Singleton guard on repeat button (V1.20–V1.22): second press killed
    the running loop and the new script exited, leaving dead servos
  - Disabling native PWM (V1.25): caused total loss of servo response

Repeat button behavior:
  Firmware stops the running CODE effect and launches a fresh script copy on
  each button down. A singleton guard is unsafe here. V1.23 uses the proven
  V1.15 loop with no guard — a second press restarts rather than breaks.

Usage:
  python build_cuby_walk.py
  Flash/import CUBY_walk_turn.json (config_name: CUBY_V1.23_ButtonWalk_ShoulderLED)
"""

import json

# ==========================================
# V1.23 — current production layout
# ==========================================

START_MODE = "button_shoulder_led"

# LED1 effect IDs from baseline: 1=green 2=white 3=red 4=blue 5=off
LED_CYCLE = [1, 3, 4, 5, 2]

SHOULDER_LED_EVENTS = [
    {"actuator": "LED1", "receiver": 1, "set_value": LED_CYCLE, "type": "gt_mid"},
    {"actuator": "LED1", "receiver": 1, "set_value": LED_CYCLE, "type": "lt_mid"},
]

walking_code = """import time, math, rc_module
from bbl.servos import ServosController

s=ServosController()
rc_module.rc_slave_init()
L_A,L_H,R_A,R_H=1,2,3,4
T_LA,T_LH,T_RA,T_RH=0,0,0,0
D_LA,D_LH,D_RA,D_RH=1,1,1,1
lims={1:(40,120),2:(45,135),3:(60,140),4:(45,135)}
W_SP,A_AM,H_AM=8.0,20.0,25.0
phase=0.0
last_t=time.ticks_ms()

def set_a(sv,ang):
 mn,mx=lims[sv]
 s.set_angle(sv,max(mn,min(mx,ang)))

def stand():
 set_a(L_A,90+T_LA)
 set_a(L_H,90+T_LH)
 set_a(R_A,90+T_RA)
 set_a(R_H,90+T_RH)

stand()

while True:
 d=rc_module.rc_slave_data()
 if d is None:
  stand()
  time.sleep(0.1)
  continue
 ly,lx,rx,ry=d[2],d[1],d[4],d[5]
 cur_t=time.ticks_ms()
 dt=time.ticks_diff(cur_t,last_t)/1000.0
 last_t=cur_t
 w_f,w_b,t_r,t_l=ly>2348,ly<1748,rx>2248,rx<1848
 if w_f or w_b or t_l or t_r:
  phase+=dt*W_SP
  if phase>6.283:phase-=6.283
  p=phase if t_r else -phase
  la=90+T_LA+D_LA*(A_AM*math.sin(p))
  ra=90+T_RA+D_RA*(A_AM*math.sin(p))
  if w_f:
   lh=90+T_LH-D_LH*(H_AM*math.cos(p))
   rh=90+T_RH-D_RH*(H_AM*math.cos(p))
  elif w_b:
   lh=90+T_LH+D_LH*(H_AM*math.cos(p))
   rh=90+T_RH+D_RH*(H_AM*math.cos(p))
  else:
   lh=90+T_LH+D_LH*(H_AM*math.cos(p))
   rh=90+T_RH-D_RH*(H_AM*math.cos(p))
  set_a(L_A,la);set_a(L_H,lh);set_a(R_A,ra);set_a(R_H,rh)
 else:
  phase=0.0
  la,ra,lh,rh=90+T_LA,90+T_RA,90+T_LH,90+T_RH
  if lx>2348:
   la+=25*D_LA;ra+=25*D_RA
  elif lx<1748:
   la-=25*D_LA;ra-=25*D_RA
  if ry>2248:
   lh+=20*D_LH;rh+=20*D_RH
  elif ry<1848:
   lh-=20*D_LH;rh-=20*D_RH
  set_a(L_A,la);set_a(L_H,lh);set_a(R_A,ra);set_a(R_H,rh)
 if hasattr(s,'timing_proc'):s.timing_proc()
 time.sleep(0.01)
"""

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_baseline.json', 'r') as f:
    data = json.load(f)

for recv in ('receiver_1', 'receiver_2'):
    if recv in data:
        for b in ('BUZZER1', 'BUZZER2'):
            data[recv].pop(b, None)

for channel in data['sender']['channels']:
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []

    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {"actuator": "CODE", "receiver": 1, "set_value": [1], "type": "down"}
        ]

    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

    if channel.get('name') == 'R Shoulder Stick':
        channel['event'] = list(SHOULDER_LED_EVENTS)

data['receiver_1']['CODE'] = {
    "data": [
        {
            "code": walking_code,
            "effect": 1,
            "effect_name": "WalkEngine"
        }
    ],
    "en": True,
    "name": "CODE"
}

data['config_name'] = "CUBY_V1.23_ButtonWalk_ShoulderLED"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json — V1.23")
print("  L Shoulder Button  -> start walk")
print("  R Shoulder Stick   -> cycle eye LEDs (up or down)")
print("  L Stick Y / R Stick X -> walk and turn")