# Mona Weather

The forecast where you are, or in any of two dozen cities, drawn in 8-bit with Mona dressed for the weather.

Shows the conditions now, the next twelve hours with rain chances, and the
week ahead. Forecasts come from Open-Meteo and "Here" is worked out from the
badge's internet address, neither needing a key. The last forecast for each
city is kept so the app still shows something offline.

## Controls

* Left / Right: change city ("Here" first, then 23 cities around the world)
* Up / Down: switch between Now, Hourly and Week
* Select: fetch again now
* Menu: switch between Celsius and Fahrenheit (the footer shows "MENU: F" or "MENU: C" for the unit it switches to)

## Requirements

* Wi-Fi: put the network name and password in `secrets.py` (`WIFI_SSID` and
  `WIFI_PASSWORD`), for example through the Settings app.
* Units default to Fahrenheit when `REGION` in `secrets.py` is `us`, otherwise
  Celsius; the choice is saved under `/state/weather`.
