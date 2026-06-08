import json

# Walking code with the Hardware Timer Asynchronous Hack
walking_code = """import time, math, rc_module
from bbl.servos import ServosController
from machine import Timer

# Phase 2: Hardware Timer Hack
# We cannot use an infinite loop because the firmware kills the thread on duplicate button presses.
# So we use a background Hardware Timer! This Python script just acts as a "Launcher".
if not hasattr(ServosController, 'cuby_engine'):
    ServosController.cuby_engine = True
    
    # Initialize and persist hardware controllers to survive Garbage Collection when thread dies
    ServosController.s = ServosController()
    rc_module.rc_slave_init()
    
    # Persist state
    ServosController.phase = 0.0
    ServosController.last_t = time.ticks_ms()
    ServosController.timer = Timer(-1)
    
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
            ly,lx,rx,ry=d[2],d[1],d[4],d[5]
            cur_t=time.ticks_ms()
            dt=time.ticks_diff(cur_t,ServosController.last_t)/1000.0
            ServosController.last_t=cur_t
            
            w_f,w_b,t_r,t_l=ly>2348,ly<1748,rx>2248,rx<1848
            if w_f or w_b or t_l or t_r:
                ServosController.phase += dt*W_SP
                if ServosController.phase>6.283: ServosController.phase-=6.283
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
            if hasattr(ServosController.s,'timing_proc'):
                ServosController.s.timing_proc()
        except Exception as e:
            pass # Suppress timer callback errors to prevent hard crash
            
    # Start the hardware timer to run forever in the background at 50Hz (20ms)
    ServosController.timer.init(period=20, mode=Timer.PERIODIC, callback=update_gait)
    
# Script ends here. Thread dies naturally. Timer continues forever!
"""

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_baseline.json', 'r') as f:
    data = json.load(f)

for channel in data['sender']['channels']:
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []
    
    # Restore the seamless single-button experience (LEDs + Engine)
    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {
                "actuator": "LED1",
                "receiver": 1,
                "set_value": [1, 3, 4, 5, 2],
                "type": "down"
            },
            {
                "actuator": "CODE",
                "receiver": 1,
                "set_value": [1, 1, 1, 1, 1], # Safe to trigger repeatedly now!
                "type": "down"
            }
        ]

    # Remove the 3-Pos switch mapping
    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

data['receiver_1']['CODE'] = {
    "data": [
        {
            "code": walking_code,
            "effect": 1,
            "effect_name": "Code  1"
        }
    ],
    "en": True,
    "name": "CODE"
}

data['config_name'] = "CUBY_V1.10_HardwareTimer"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json with V1.10 Hardware Timer Hack!")


