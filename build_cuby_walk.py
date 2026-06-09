"""
CUBY Build Script - Alpha Release

Purpose:
  Generates the deployable CUBY_walk_turn.json for the Bambu Lab CyberBrick
  system. The output is a "custom" config that:

  - Defines servo limits and names (inherited from baseline).
  - Wires the L Shoulder Button to activate the movement engine.
  - Wires the primary drive sticks (L Y, R X) to drive LED1 eye colors
    via native sender events (latching behavior - color stays when sticks
    return to center).
  - Injects a minimal, pure Python walking loop as a CODE effect.

Architecture (important for understanding constraints):
  There are three distinct layers:

  1. Sender event rules (this script wires them)
     - Static JSON rules that fire actuator events on the receiver
       based on stick/button values (gt_mid, lt_mid, down, etc.).
     - Used for LEDs (fast, native) and for activating the CODE effect.

  2. Native receiver actuators
     - LED1 (pre-defined effects in the baseline: 1=green, 2=white,
       3=red, 4=blue, 5=off).
     - PWM channels for servos (when direct controls are present).
     - These run in firmware, independent of any Python.

  3. Python CODE effect (the injected walking_code)
     - A single while-True loop that owns all servo movement.
     - Reads live data via rc_module.rc_slave_data().
     - Drives servos exclusively via ServosController (direct joystick
       controls are deliberately cleared to avoid jitter/fighting).
     - This loop must be explicitly activated by a CODE event (historical
       stability requirement - auto-start on power-up caused crashes,
       I2C contention, and jitter in earlier experiments).

  Why the button is required for movement:
    - The heavy while-True gait loop is not auto-started.
    - An explicit sender event is needed to activate the CODE effect.
    - LEDs can (and do) respond before the button because they use the
      native event path (layer 1 + 2). Movement cannot, because it lives
      in layer 3.

  Design goals for this Alpha:
    - Keep the movement loop as small and pure as possible.
    - Use native LED events for visual feedback (proven to work, zero
      overhead inside the gait loop).
    - Latching LEDs: once a direction color is set it stays on in idle.
    - Button gives a deliberate "arm + ready white" action.

  No functionality was changed in this cleanup pass. Only comments,
  structure, and embedded documentation were improved for clarity.
"""

import json

# =============================================================================
# Version / Release Marker
# =============================================================================
# Alpha release candidate. Movement, button activation, and latching LED
# behavior are considered stable for this milestone.
VERSION = "V1.23 Alpha"

# =============================================================================
# The injected walking engine (runs on the receiver as a CODE effect)
# =============================================================================
# This string becomes the body of the CODE actuator (effect 1).
# It is executed only after the sender fires a CODE activation event
# (currently wired to the L Shoulder Button).
#
# Design constraints observed during development:
#   - Must be a single, self-contained while-True loop (no external timers
#     or background tasks were reliable).
#   - Must own all servo output (direct joystick->PWM controls are cleared
#     in the generator to prevent jitter).
#   - Must read raw stick data via rc_module (not rely on sender controls).
#   - Must stay as small and pure as possible - LED control was deliberately
#     moved out to native sender events for stability and simplicity.
#   - rc_slave_init() must be called once at the top.
#
# The loop is intentionally tolerant of re-activation of the CODE effect
# (it just continues running its while-True).
# =============================================================================

walking_code = """# CUBY Walking Engine (injected as CODE effect 1)
# Activated by sender event from L Shoulder Button.
# All servo movement happens here. LEDs are handled natively by the sender.

import time, math, rc_module
from bbl.servos import ServosController

s = ServosController()
rc_module.rc_slave_init()

# Servo mapping (S1-S4 on the receiver board)
L_A, L_H, R_A, R_H = 1, 2, 3, 4

# Trims (center offsets) - adjust if the robot doesn't stand straight at 90 deg
T_LA, T_LH, T_RA, T_RH = 0, 0, 0, 0

# Direction multipliers (set to -1 to reverse a servo)
D_LA, D_LH, D_RA, D_RH = 1, 1, 1, 1

# Safe mechanical limits (degrees) - taken from the baseline JSON
lims = {1: (40, 120), 2: (45, 135), 3: (60, 140), 4: (45, 135)}

# Gait tuning parameters
W_SP, A_AM, H_AM = 8.0, 20.0, 25.0

phase = 0.0
last_t = time.ticks_ms()


def set_a(sv, ang):
    # Clamp and send angle to the given servo channel.
    mn, mx = lims[sv]
    s.set_angle(sv, max(mn, min(mx, ang)))


def stand():
    # Neutral standing pose (used on lost connection and at startup).
    set_a(L_A, 90 + T_LA)
    set_a(L_H, 90 + T_LH)
    set_a(R_A, 90 + T_RA)
    set_a(R_H, 90 + T_RH)


stand()

while True:
    d = rc_module.rc_slave_data()
    if d is None:
        stand()
        time.sleep(0.1)
        continue

    # Raw stick values from the transmitter (indices are fixed by rc_module)
    # [L1, L2, L3, R1, R2, R3, ...]
    ly, lx, rx, ry = d[2], d[1], d[4], d[5]

    cur_t = time.ticks_ms()
    dt = time.ticks_diff(cur_t, last_t) / 1000.0
    last_t = cur_t

    # Thresholds match the deadzones used in the sender config
    w_f, w_b, t_r, t_l = ly > 2348, ly < 1748, rx > 2248, rx < 1848

    if w_f or w_b or t_l or t_r:
        # Active locomotion
        phase += dt * W_SP
        if phase > 6.283:
            phase -= 6.283
        p = phase if t_r else -phase

        la = 90 + T_LA + D_LA * (A_AM * math.sin(p))
        ra = 90 + T_RA + D_RA * (A_AM * math.sin(p))

        if w_f:
            lh = 90 + T_LH - D_LH * (H_AM * math.cos(p))
            rh = 90 + T_RH - D_RH * (H_AM * math.cos(p))
        elif w_b:
            lh = 90 + T_LH + D_LH * (H_AM * math.cos(p))
            rh = 90 + T_RH + D_RH * (H_AM * math.cos(p))
        else:
            # Pure turn
            lh = 90 + T_LH + D_LH * (H_AM * math.cos(p))
            rh = 90 + T_RH - D_RH * (H_AM * math.cos(p))

        set_a(L_A, la)
        set_a(L_H, lh)
        set_a(R_A, ra)
        set_a(R_H, rh)
    else:
        # Idle + pose mode (small adjustments from left/right sticks)
        phase = 0.0
        la, ra, lh, rh = 90 + T_LA, 90 + T_RA, 90 + T_LH, 90 + T_RH

        if lx > 2348:
            la += 25 * D_LA
            ra += 25 * D_RA
        elif lx < 1748:
            la -= 25 * D_LA
            ra -= 25 * D_RA

        if ry > 2248:
            lh += 20 * D_LH
            rh += 20 * D_RH
        elif ry < 1848:
            lh -= 20 * D_LH
            rh -= 20 * D_RH

        set_a(L_A, la)
        set_a(L_H, lh)
        set_a(R_A, ra)
        set_a(R_H, rh)

    if hasattr(s, 'timing_proc'):
        s.timing_proc()
    time.sleep(0.01)
"""

# =============================================================================
# Load baseline and apply CUBY-specific customizations
# =============================================================================
# We start from a baseline JSON that already contains the correct servo
# limits, names, LED1 effect definitions, and overall receiver/sender
# structure. We then make targeted, minimal mutations:
#
# - Strip any BUZZER entries (confirmed no hardware buzzer on TX/RX).
# - Clear direct joystick->PWM controls (the Python loop owns the servos).
# - Wire the L Shoulder Button to activate movement + set ready white.
# - Wire the drive sticks to drive LED1 colors via native events.
# - Inject the walking_code as the active CODE effect.
#
# This approach keeps the generated config compatible with the CyberBrick
# app while giving us full control over the behavior.
# =============================================================================

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_baseline.json', 'r') as f:
    data = json.load(f)

# Defensively remove any buzzer actuator entries (confirmed: no hardware
# buzzer on either the transmitter or receiver CPUs).
for recv in ('receiver_1', 'receiver_2'):
    if recv in data:
        for b in ('BUZZER1', 'BUZZER2'):
            data[recv].pop(b, None)

for channel in data['sender']['channels']:
    # Clear any direct joystick controls. The walking loop reads raw data
    # via rc_slave_data() and drives the servos itself. Leaving the original
    # controls would cause the firmware and Python to fight over the PWMs
    # (observed as jitter in earlier experiments).
    if channel.get('device') == 'joystick' and 'controls' in channel:
        channel['controls'] = []

    # L Shoulder Button wiring:
    #   - Activates the walking engine (CODE effect 1).
    #   - Sets an initial "ready" state on the eyes (white steady).
    # The button is the explicit activation trigger for the CODE loop.
    # Historical note: auto-starting the loop on power-up repeatedly caused
    # crashes, I2C contention, and servo jitter. The button provides a clean,
    # deliberate hand-off.
    if channel.get('name') == 'L Shoulder Button':
        channel['event'] = [
            {
                "actuator": "CODE",
                "receiver": 1,
                "set_value": [1],
                "type": "down"
            },
            {
                "actuator": "LED1",
                "receiver": 1,
                "set_value": [2],
                "type": "down"
            }
        ]

    # The 3-Pos switch is not used for movement or LEDs in this config.
    if channel.get('name') == 'L Shoulder 3-Pos':
        channel['event'] = []

    # The R Shoulder Stick is not used for LEDs in this version.
    if channel.get('name') == 'R Shoulder Stick':
        channel['event'] = []

    # Native LED1 events driven directly by stick position.
    # These are sender-side rules that fire LED1 actuator commands.
    # They run completely independently of the Python movement loop.
    # We deliberately do NOT include an eq_mid rule so that the last
    # commanded direction color "latches" and stays on when the sticks
    # return to center (idle pose).
    if channel.get('name') == 'L Stick' and channel.get('data', {}).get('channel') == 'y':
        # L Stick vertical axis (forward / backward)
        channel['event'] = [
            {"actuator": "LED1", "receiver": 1, "set_value": [2], "type": "gt_mid"},  # white = forward
            {"actuator": "LED1", "receiver": 1, "set_value": [3], "type": "lt_mid"},  # red = backward
            # (intentionally no eq_mid - color latches on center)
        ]
    if channel.get('name') == 'R Stick' and channel.get('data', {}).get('channel') == 'x':
        # R Stick horizontal axis (turn left / right)
        channel['event'] = [
            {"actuator": "LED1", "receiver": 1, "set_value": [4], "type": "gt_mid"},  # blue = turn right
            {"actuator": "LED1", "receiver": 1, "set_value": [1], "type": "lt_mid"},  # green = turn left
            # (intentionally no eq_mid - color latches on center)
        ]

# Inject the walking engine as the active CODE effect on the receiver.
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

# Final metadata
data['config_name'] = "CUBY_V1.23_ButtonForMovement_Alpha"

with open('c:/Users/mott_/OneDrive/Documents/CyberBrick/Cuby/CUBY_walk_turn.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("Generated CUBY_walk_turn.json (Alpha) - button activates movement + ready white; LEDs latch on direction")



