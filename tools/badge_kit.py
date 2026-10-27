# Shared on-badge harness kit: fake run/buttons, frame stepping, RLE screenshots.
import sys, os, time, builtins
from array import array
captured = []
class Result:
    result = None
builtins.run = lambda fn: (captured.append(fn), Result())[1]
held_now = set(); pressed_now = set()
badge.pressed = lambda b=None: (b in pressed_now) if b is not None else set(pressed_now)
badge.held = lambda b=None: (b in held_now) if b is not None else set(held_now)
try: os.mkdir('/state/shots')
except OSError: pass
for n in os.listdir('/state/shots'): os.remove('/state/shots/' + n)
shots = [0]
def load(dev, app):
    try: os.remove('/state/%s.json' % app)
    except OSError: pass
    sys.path.insert(0, dev); os.chdir(dev)
    src = open(dev + '/__init__.py').read().replace('APP_DIR = "/system/apps/%s"' % app, 'APP_DIR = "%s"' % dev)
    g = {'__name__': app + '_dev'}
    t = time.ticks_ms(); exec(src, g); print('import', time.ticks_diff(time.ticks_ms(), t), 'ms')
    badge.update()
    return g, captured[-1]
def rle(raw):
    pixels = array('H', raw); out = array('H'); prev = pixels[0]; count = 0
    for value in pixels:
        if value == prev and count < 65535: count += 1
        else: out.append(count); out.append(prev); prev = value; count = 1
    out.append(count); out.append(prev); return out
def step(update, buttons=()):
    global pressed_now, held_now
    buttons = set(buttons); pressed_now = buttons - held_now; held_now = buttons
    t = time.ticks_ms(); update(); cost = time.ticks_diff(time.ticks_ms(), t)
    raw = bytes(screen.raw); badge.update(); return cost, raw
def shot(label, raw, cost=None):
    with open('/state/shots/%d.rle' % shots[0], 'wb') as f: f.write(rle(raw))
    print('SHOT %d [%s] frame %s ms' % (shots[0], label, cost)); shots[0] += 1
def run_for(update, ms, buttons=()):
    start = time.ticks_ms(); worst = 0; total = 0; n = 0; raw = None
    while time.ticks_diff(time.ticks_ms(), start) < ms:
        cost, raw = step(update, buttons); worst = max(worst, cost); total += cost; n += 1
    return worst, total // max(1, n), raw
def run_until(update, cond, limit_ms, buttons=()):
    start = time.ticks_ms(); raw = None; cost = 0
    while time.ticks_diff(time.ticks_ms(), start) < limit_ms:
        cost, raw = step(update, buttons)
        if cond(): break
    return cond(), raw, cost
