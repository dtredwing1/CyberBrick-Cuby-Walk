import json

# ==========================================
# V1.14: THE CLAW MACHINE ARCHITECTURE (Fixed)
# ==========================================
# Fix 1: Disable native PWM1-4 so firmware stops fighting Timer for servos
# Fix 2: Control BOTH LED1 and LED2 (one per eye)
# ==========================================

walking_code = """import time, math, rc_module
from bbl.servos import ServosController
from bbl.leds import LEDController
from machine import Timer

if not hasattr(ServosController, 'cuby_engine'):
 ServosController.cuby_engine = True
 ServosController.s = ServosController()
 ServosController.lc1 = LEDController("LED1")
 ServosController.lc2 = LEDController("LED2")
 rc_module.rc_slave_init()
 ServosController.phase = 0.0
 ServosController.last_t = time.ticks_ms()
 ServosController.led_colors = [0x00FF00, 0xFF0000, 0x0000FF, 0xFFFF00, 0x00FFFF, 0xFF00FF]
 ServosController.led_idx = 0
 ServosController.last_btn = 0
 ServosController.lc1.set_led_effect(0, 500, 255, 1, 0x00FF00)
 ServosController.lc2.set_led_effect(0, 500, 255, 1, 0x00FF00)
 L_A,L_H,R_A,R_H=1,2,3,4
 T_LA,T_LH,T_RA,T_RH=0,0,0,0
 D_LA,D_LH,D_RA,D_RH=1,1,1,1
 lims={1:(40,120),2:(45,135),3:(60,140),4:(45,135)}
 W_SP,A_AM,H_AM=8.0,20.0,25.0

 def set_a(sv,ang):
  mn,mx=lims[sv]
  ServosController.s.set_angle(sv,max(mn,min(mx,ang)))

 def stand():
  set_a(L_A,90+T_LA)
  set_a(L_H,90+T_LH)
  set_a(R_A,90+T_RA)
  set_a(R_H,90+T_RH)

 stand()

 def update_gait(t):
  try:
   d=rc_module.rc_slave_data()
   if d is None:
    stand()
    return
   btn=d[6]
   if btn==0 and ServosController.last_btn==1:
    ServosController.led_idx=(ServosController.led_idx+1)%len(ServosController.led_colors)
    c=ServosController.led_colors[ServosController.led_idx]
    ServosController.lc1.set_led_effect(0,500,255,1,c)
    ServosController.lc2.set_led_effect(0,500,255,1,c)
   ServosController.last_btn=btn
   ly,lx,rx,ry=d[2],d[1],d[4],d[5]
   cur_t=time.ticks_ms()
   dt=time.ticks_diff(cur_t,ServosController.last_t)/1000.0
   ServosController.last_t=cur_t
   w_f,w_b,t_r,t_l=ly>2348,ly<1748,rx>2248,rx<1848
   if w_f or w_b or t_l or t_r:
    ServosController.phase+=dt*W_SP
    if ServosController.phase>6.283:ServosController.phase-=6.283
    p=ServosController.phase if t_r else -ServosController.phase
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
    ServosController.phase=0.0
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
   if hasattr(ServosController.s,'timing_proc'):ServosController.s.timing_proc()
  except:
   pass

 ServosController.timer = Timer(0)
 ServosController.timer.init(period=40, mode=Timer.PERIODIC, callback=update_gait)
"""

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_baseline.json', 'r') as f:
    data = json.load(f)

# Strip native LED data from receiver to prevent firmware from touching I2C for LEDs
data['receiver_1']['LED1'] = {"data": [], "en": False, "name": "LED1"}
data['receiver_1']['LED2'] = {"data": [], "en": False, "name": "LED2"}

# Disable native PWM servo channels to stop firmware from fighting Timer for servo control
# Our ServosController talks to the PCA9685 directly over I2C — it doesn't need these.
for pwm in ['PWM1', 'PWM2', 'PWM3', 'PWM4']:
    data['receiver_1'][pwm] = {"en": False, "name": pwm}

for channel in data['sender']['channels']:
    # Clear joystick controls (we read them via rc_slave_data instead)
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []
    
    # Clear all joystick events (no CODE triggers from joystick movement)
    if channel.get('device') == 'joystick' and 'event' in channel:
        channel['event'] = []

    # L Shoulder Button: fires CODE effect 1 on press. NO native LED1 actuator!
    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {
                "actuator": "CODE",
                "receiver": 1,
                "set_value": [1],
                "type": "down"
            }
        ]

    # Clear the 3-Pos switch (not needed)
    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

    # Clear R Shoulder Stick events (prevent any stray LED2 triggers)
    if channel.get('name') == 'R Shoulder Stick':
        channel['event'] = []

data['receiver_1']['CODE'] = {
    "data": [
        {
            "code": walking_code,
            "effect": 1,
            "effect_name": "ClawMachine_Engine"
        }
    ],
    "en": True,
    "name": "CODE"
}

data['config_name'] = "CUBY_V1.14_ClawMachineFixed"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json with V1.14 Claw Machine Architecture (Fixed)!")



