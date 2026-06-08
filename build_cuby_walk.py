import json

# ==========================================
# V1.11: THE MONOLITHIC TIMER (Auto-Boot Engine)
# ==========================================
walking_code = """import time, math, rc_module, machine
from bbl.servos import ServosController
from bbl.leds import LEDController
from machine import Timer

# Ensure we have a clean RTC mailbox on boot
try:
    if machine.RTC().memory() != b'led_next':
        machine.RTC().memory(b'')
except:
    machine.RTC().memory(b'')

if not hasattr(ServosController, 'cuby_engine'):
    ServosController.cuby_engine = True
    
    # Initialize all hardware here. 
    # Timer now has TOTAL MONOPOLY over the I2C bus!
    ServosController.s = ServosController()
    ServosController.lc = LEDController("LED1")
    rc_module.rc_slave_init()
    
    # Init LED
    ServosController.led_colors = [0x00FF00, 0xFF0000, 0x0000FF, 0xFFFF00, 0x00FFFF, 0xFF00FF]
    ServosController.led_idx = 0
    ServosController.lc.set_led_effect(0, 500, 255, 1, ServosController.led_colors[0]) # Start Green
    
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
            # 1. Check RTC Mailbox for LED Button Presses
            if machine.RTC().memory() == b'led_next':
                machine.RTC().memory(b'') # Clear mailbox
                ServosController.led_idx = (ServosController.led_idx + 1) % len(ServosController.led_colors)
                ServosController.lc.set_led_effect(0, 500, 255, 1, ServosController.led_colors[ServosController.led_idx])
                
            # 2. Read Remote Data
            d=rc_module.rc_slave_data()
            if d is None:
                stand()
                return
                
            # 3. Calculate Gait
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
            pass # Suppress all errors to protect background timer
            
    # Launch Timer!
    ServosController.timer.init(period=20, mode=Timer.PERIODIC, callback=update_gait)
"""

# ==========================================
# V1.11: THE LED RTC MESSENGER
# ==========================================
led_code = """import machine
machine.RTC().memory(b'led_next')
"""

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_baseline.json', 'r') as f:
    data = json.load(f)

for channel in data['sender']['channels']:
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []
    
    # 1. Auto-Boot Trigger: ANY Joystick movement fires CODE 1!
    if channel.get('name') in ['L Stick', 'R Stick']:
        channel['event'] = [
            {"actuator": "CODE", "receiver": 1, "set_value": [1], "type": "gt_mid"},
            {"actuator": "CODE", "receiver": 1, "set_value": [1], "type": "lt_mid"}
        ]
        
    # 2. LED Button: Fires CODE 2 (RTC Messenger) instead of native I2C
    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {"actuator": "CODE", "receiver": 1, "set_value": [2], "type": "down"}
        ]

    # Remove 3-Pos switch mappings entirely
    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

# Map CODE 1 and CODE 2 into the receiver block
data['receiver_1']['CODE'] = {
    "data": [
        {
            "code": walking_code,
            "effect": 1,
            "effect_name": "Monolithic_Timer"
        },
        {
            "code": led_code,
            "effect": 2,
            "effect_name": "RTC_Messenger"
        }
    ],
    "en": True,
    "name": "CODE"
}

data['config_name'] = "CUBY_V1.11_ZeroClick_Monolith"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json with V1.11 Monolithic Timer Hack!")


