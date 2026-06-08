import json

# ==========================================
# V1.15: MOVEMENT ONLY (Button-Triggered V1.9 Loop)
# ==========================================
# Exact same while-True loop that worked in V1.9.
# Triggered by L Shoulder Button instead of 3-Pos switch.
# No Timer. No LEDs. Just movement.
# ==========================================

walking_code = """import time, math, rc_module
from bbl.servos import ServosController
from bbl.buzzer import BuzzerController

bz=BuzzerController('BUZZER1',freq=880,duty=512)
bz.buzzer.freq(880)
bz.buzzer.duty(512)
time.sleep(0.15)
bz.buzzer.duty(0)
time.sleep(0.05)
bz.buzzer.freq(1760)
bz.buzzer.duty(512)
time.sleep(0.15)
bz.buzzer.duty(0)

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

for channel in data['sender']['channels']:
    # Clear joystick controls (we read via rc_slave_data)
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []

    # L Shoulder Button: fires CODE effect 1 on press
    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {
                "actuator": "CODE",
                "receiver": 1,
                "set_value": [1],
                "type": "down"
            }
        ]

    # Clear 3-Pos switch
    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

    # Clear R Shoulder Stick events
    if channel.get('name') == 'R Shoulder Stick':
        channel['event'] = []

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

data['config_name'] = "CUBY_V1.15_MovementOnly"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json with V1.15 Movement Only!")



