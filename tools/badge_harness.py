import sys, os, json; sys.path.insert(0, '/state'); import kit, time
try: os.mkdir('/state/weather')
except OSError: pass
for n in os.listdir('/state/weather'): os.remove('/state/weather/' + n)
g, update = kit.load('/state/dev_weather', 'mona_weather')
print('units F?', g['state']['fahrenheit'], 'city', g['state']['city'])
cost, raw = kit.step(update); kit.shot('waiting', raw, cost)
ok, raw, cost = kit.run_until(update, lambda: g['weather'].forecast is not None or g['weather'].error, 45000)
w = g['weather']; print('here:', w.place, w.lat, w.lon, 'error', w.error, 'forecast', None if not w.forecast else (w.forecast['temp'], w.forecast['code'], w.forecast['units'], len(w.forecast['hours']), len(w.forecast['days'])))
if w.forecast is None:
    # no network: use the sample reply as a saved forecast for Madrid in Celsius
    g['state']['fahrenheit'] = False
    with open('/state/weather_sample.json') as s, open('/state/weather/10_c.json', 'w') as d: d.write(s.read())
    g['state']['city'] = 9; g['change_city'](1)
    kit.run_for(update, 200)
    print('fallback forecast loaded:', g['weather'].forecast is not None, g['weather'].cached)
_, avg, raw = kit.run_for(update, 400); kit.shot('now page', raw, avg)
kit.step(update, (BUTTON_DOWN,)); _, avg, raw = kit.run_for(update, 300); kit.shot('hourly page', raw, avg)
kit.step(update, (BUTTON_DOWN,)); _, avg, raw = kit.run_for(update, 300); kit.shot('week page', raw, avg)
kit.step(update, (BUTTON_UP,)); kit.step(update, (BUTTON_UP,))
kit.step(update, (BUTTON_RIGHT,)); kit.step(update, (BUTTON_RIGHT,))
ok, raw, cost = kit.run_until(update, lambda: g['weather'].forecast is not None or g['weather'].error, 30000)
print('city', g['weather'].name, 'forecast', g['weather'].forecast is not None, 'error', g['weather'].error)
_, avg, raw = kit.run_for(update, 400); kit.shot('another city', raw, avg)
kit.step(update, (BUTTON_MENU,))
ok, raw, cost = kit.run_until(update, lambda: g['weather'].forecast is not None or g['weather'].error, 30000)
print('units toggled; F?', g['state']['fahrenheit'], 'forecast', None if not g['weather'].forecast else g['weather'].forecast['units'])
_, avg, raw = kit.run_for(update, 400); kit.shot('toggled units', raw, avg)
g['on_exit'](); print('DONE weather', os.listdir('/state/weather'))
