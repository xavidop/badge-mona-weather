"""
Mona Weather: the forecast where you are, or in any of two dozen cities, in 8-bit.

Now, the next twelve hours and the week ahead from Open-Meteo, with no key
needed. "Here" is found from the badge's internet address. Mona dresses for
the weather.

Controls:
* Left / Right = Change city
* Up / Down = Now, hourly, or the week
* Select = Fetch again now
* Menu = Switch between Celsius and Fahrenheit
"""

import json
import math
import os
import sys

import fetch
import missing_details
from badgeware import State

try:
    import secrets
except ImportError:
    secrets = None

APP_DIR = "/system/apps/mona_weather"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

badge.mode(HIRES | VSYNC)
screen.antialias = image.OFF

WIDTH, HEIGHT = screen.width, screen.height

ICONS = image.load("assets/icons.png").spritesheet(10, 1)
MASCOT = image.load("assets/mascot.png").spritesheet(3, 1)
SUN, PARTLY, CLOUD, DRIZZLE, RAIN, SNOW, STORM, FOG, MOON, NIGHT_CLOUD = range(10)

CACHE_DIR = "/state/weather"
TEMP_FILE = CACHE_DIR + "/download.tmp"
HEADERS = {"User-Agent": "GitHub Universe Badge 2026 Weather"}
REFRESH_MS = 15 * 60 * 1000
RETRY_MS = 20000
CHANGE_DEBOUNCE_MS = 700

LOCATE_URL = "http://ip-api.com/json/?fields=status,lat,lon,city,countryCode"
FORECAST_URL = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
                "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,is_day"
                "&hourly=temperature_2m,weather_code,precipitation_probability"
                "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
                "&forecast_days=6&forecast_hours=12&timezone=auto%s")

# (name, latitude, longitude); the first entry is found from the badge's address
CITIES = (
    ("HERE", None, None),
    ("SAN FRANCISCO", 37.77, -122.42), ("NEW YORK", 40.71, -74.01), ("SEATTLE", 47.61, -122.33),
    ("AUSTIN", 30.27, -97.74), ("CHICAGO", 41.88, -87.63), ("TORONTO", 43.65, -79.38),
    ("MEXICO CITY", 19.43, -99.13), ("SAO PAULO", -23.55, -46.63), ("LONDON", 51.51, -0.13),
    ("MADRID", 40.42, -3.70), ("PARIS", 48.86, 2.35), ("BERLIN", 52.52, 13.41),
    ("AMSTERDAM", 52.37, 4.90), ("LISBON", 38.72, -9.14), ("LAGOS", 6.52, 3.38),
    ("NAIROBI", -1.29, 36.82), ("DUBAI", 25.20, 55.27), ("BANGALORE", 12.97, 77.59),
    ("SINGAPORE", 1.35, 103.82), ("TOKYO", 35.68, 139.69), ("SEOUL", 37.57, 126.98),
    ("SYDNEY", -33.87, 151.21), ("AUCKLAND", -36.85, 174.76),
)

# WMO weather codes: (label, day icon, night icon)
CODES = {
    0: ("CLEAR", SUN, MOON), 1: ("MOSTLY CLEAR", PARTLY, NIGHT_CLOUD), 2: ("PARTLY CLOUDY", PARTLY, NIGHT_CLOUD),
    3: ("OVERCAST", CLOUD, CLOUD), 45: ("FOG", FOG, FOG), 48: ("ICY FOG", FOG, FOG),
    51: ("LIGHT DRIZZLE", DRIZZLE, DRIZZLE), 53: ("DRIZZLE", DRIZZLE, DRIZZLE), 55: ("HEAVY DRIZZLE", DRIZZLE, DRIZZLE),
    56: ("FREEZING DRIZZLE", DRIZZLE, DRIZZLE), 57: ("FREEZING DRIZZLE", DRIZZLE, DRIZZLE),
    61: ("LIGHT RAIN", RAIN, RAIN), 63: ("RAIN", RAIN, RAIN), 65: ("HEAVY RAIN", RAIN, RAIN),
    66: ("FREEZING RAIN", RAIN, RAIN), 67: ("FREEZING RAIN", RAIN, RAIN),
    71: ("LIGHT SNOW", SNOW, SNOW), 73: ("SNOW", SNOW, SNOW), 75: ("HEAVY SNOW", SNOW, SNOW), 77: ("SNOW GRAINS", SNOW, SNOW),
    80: ("SHOWERS", RAIN, RAIN), 81: ("SHOWERS", RAIN, RAIN), 82: ("HEAVY SHOWERS", RAIN, RAIN),
    85: ("SNOW SHOWERS", SNOW, SNOW), 86: ("SNOW SHOWERS", SNOW, SNOW),
    95: ("THUNDERSTORM", STORM, STORM), 96: ("THUNDERSTORM", STORM, STORM), 99: ("THUNDERSTORM", STORM, STORM),
}

# sky colours by icon, day and night
SKIES = {
    SUN: ((64, 150, 240), (160, 210, 250)), PARTLY: ((80, 150, 230), (170, 205, 240)),
    CLOUD: ((120, 130, 150), (170, 175, 185)), DRIZZLE: ((100, 115, 140), (150, 160, 175)),
    RAIN: ((70, 85, 115), (110, 125, 150)), SNOW: ((150, 165, 190), (210, 220, 235)),
    STORM: ((40, 40, 70), (80, 80, 110)), FOG: ((160, 165, 175), (200, 200, 205)),
    MOON: ((16, 24, 60), (40, 48, 96)), NIGHT_CLOUD: ((24, 30, 64), (50, 56, 100)),
}
GROUND = color.rgb(60, 140, 70)
GROUND_DARK = color.rgb(44, 110, 54)
INK = color.rgb(20, 20, 32)
CREAM = color.rgb(240, 232, 208)
CREAM_DIM = color.rgb(200, 196, 180)
AMBER = color.rgb(255, 200, 48)
RED = color.rgb(230, 70, 70)
BLUE = color.rgb(90, 160, 240)
PANEL = color.rgb(20, 20, 32, 170)
TRACK = color.rgb(20, 20, 32, 90)

TITLE = font.futile
BIG = font.ignore
BODY = font.nope
SMALL = font.sins

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
PAGES = ("NOW", "HOURLY", "WEEK")

try:
    os.mkdir(CACHE_DIR)
except OSError:
    pass

state = {"city": 0, "fahrenheit": None}
State.load("mona_weather", state)
if not isinstance(state.get("city"), int) or not 0 <= state["city"] < len(CITIES):
    state["city"] = 0
if state.get("fahrenheit") is None:
    state["fahrenheit"] = str(getattr(secrets, "REGION", "") or "").lower() == "us"
state["fahrenheit"] = bool(state["fahrenheit"])


def save_state():
    try:
        State.save("mona_weather", state)
    except OSError as error:
        print("Mona Weather: could not save:", error)


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


# ----------------------------------------------------------------------------
# downloads, polled a frame at a time

class Fetch:
    def __init__(self, url, path):
        self.path = path
        self.error = None
        self.done = False
        self.missing = missing_details.missing("WIFI_SSID")
        if self.missing:
            self.error = "Add the Wi-Fi name and password in Settings"
            self.request = None
            return
        remove_file(path)
        self.request = fetch.url(url, headers=HEADERS).to(path)

    @property
    def status(self):
        if self.request is None:
            return "no wi-fi details"
        return self.request.state or "fetching"

    def poll(self):
        if self.done or self.error:
            return False
        finished = bool(self.request)
        if self.request.error:
            self.error = str(self.request.error)
            remove_file(self.path)
            return False
        if finished:
            self.done = True
        return finished


# ----------------------------------------------------------------------------
# the forecast for the chosen city

def weekday(date):
    year, month, day = int(date[0:4]), int(date[5:7]), int(date[8:10])
    if month < 3:
        month += 12
        year -= 1
    century, year = divmod(year, 100)
    h = (day + 13 * (month + 1) // 5 + year + year // 4 + century // 4 + 5 * century) % 7
    return (h + 5) % 7


def parse_forecast(path):
    with open(path) as handle:
        reply = json.load(handle)
    current = reply["current"]
    hourly = reply["hourly"]
    daily = reply["daily"]
    hours = []
    for n in range(len(hourly["time"])):
        hours.append((hourly["time"][n][11:16], hourly["temperature_2m"][n], hourly["weather_code"][n], hourly["precipitation_probability"][n]))
    days = []
    for n in range(len(daily["time"])):
        days.append((daily["time"][n], daily["weather_code"][n], daily["temperature_2m_max"][n], daily["temperature_2m_min"][n], daily["precipitation_probability_max"][n]))
    return {
        "temp": current["temperature_2m"], "feels": current["apparent_temperature"],
        "humidity": current["relative_humidity_2m"], "wind": current["wind_speed_10m"],
        "code": current["weather_code"], "day": bool(current["is_day"]), "time": current["time"][11:16],
        "units": (reply["current_units"]["temperature_2m"], reply["current_units"]["wind_speed_10m"]),
        "sunrise": daily["sunrise"][0][11:16], "sunset": daily["sunset"][0][11:16],
        "hours": hours, "days": days, "zone": reply.get("timezone_abbreviation", ""),
    }


class Weather:
    def __init__(self, city_index):
        self.city = city_index
        self.name, self.lat, self.lon = CITIES[city_index]
        self.place = self.name
        self.forecast = None
        self.fetch = None
        self.stage = None
        self.error = None
        self.status = ""
        self.next_at = 0
        self.fetched_at = None
        self.cached = False
        self.cache = "%s/%d_%s.json" % (CACHE_DIR, city_index, "f" if state["fahrenheit"] else "c")
        if file_exists(self.cache):
            try:
                self.forecast = parse_forecast(self.cache)
                self.cached = True
            except (OSError, ValueError, KeyError, TypeError):
                remove_file(self.cache)
        if self.lat is None and file_exists(CACHE_DIR + "/here.json"):
            try:
                with open(CACHE_DIR + "/here.json") as handle:
                    here = json.load(handle)
                self.lat, self.lon, self.place = here["lat"], here["lon"], here["place"]
            except (OSError, ValueError, KeyError, TypeError):
                remove_file(CACHE_DIR + "/here.json")

    def refresh_now(self):
        self.next_at = 0
        self.error = None

    def forecast_url(self):
        units = "&temperature_unit=fahrenheit&wind_speed_unit=mph" if state["fahrenheit"] else ""
        return FORECAST_URL % (self.lat, self.lon, units)

    def update(self):
        if self.fetch is None:
            if badge.ticks < self.next_at:
                return
            if self.lat is None or (self.city == 0 and self.forecast is None and not self.cached):
                self.stage = "locate"
                self.fetch = Fetch(LOCATE_URL, TEMP_FILE)
                self.status = "finding you"
            else:
                self.stage = "forecast"
                self.fetch = Fetch(self.forecast_url(), TEMP_FILE)
                self.status = "fetching forecast"
            return
        if self.fetch.poll():
            try:
                if self.stage == "locate":
                    with open(TEMP_FILE) as handle:
                        here = json.load(handle)
                    if here.get("status") != "success":
                        raise ValueError("could not locate")
                    self.lat, self.lon = here["lat"], here["lon"]
                    self.place = ("%s %s" % (here.get("city", ""), here.get("countryCode", ""))).strip().upper() or "HERE"
                    with open(CACHE_DIR + "/here.json", "w") as handle:
                        json.dump({"lat": self.lat, "lon": self.lon, "place": self.place}, handle)
                    self.fetch = None
                    self.next_at = 0
                    remove_file(TEMP_FILE)
                    return
                self.forecast = parse_forecast(TEMP_FILE)
                os.rename(TEMP_FILE, self.cache)
                self.cached = False
                self.error = None
                self.fetched_at = badge.ticks
                self.next_at = badge.ticks + REFRESH_MS
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.fail("bad reply: %s" % error)
            remove_file(TEMP_FILE)
            self.fetch = None
        elif self.fetch.error:
            self.fail(self.fetch.error)
            self.fetch = None

    def fail(self, reason):
        print("Mona Weather:", self.stage, "failed:", reason)
        self.error = reason
        self.next_at = badge.ticks + RETRY_MS


weather = Weather(state["city"])
page = 0
changed_at = None       # when the city last changed, to debounce fetching


def change_city(delta):
    global weather, changed_at
    state["city"] = (state["city"] + delta) % len(CITIES)
    weather = Weather(state["city"])
    weather.next_at = badge.ticks + CHANGE_DEBOUNCE_MS
    changed_at = badge.ticks
    save_state()


def toggle_units():
    global weather
    state["fahrenheit"] = not state["fahrenheit"]
    save_state()
    weather = Weather(state["city"])


# ----------------------------------------------------------------------------
# drawing

def fill(x, y, w, h, pen):
    screen.pen = pen
    screen.rectangle(x, y, w, h)


def write(text, x, y, pen, face=BODY):
    screen.font = face
    screen.pen = pen
    screen.text(text, x, y)


def text_width(text, face=BODY):
    screen.font = face
    return screen.measure_text(text)[0]


def write_centred(text, cx, y, pen, face=BODY):
    write(text, cx - text_width(text, face) // 2, y, pen, face)


def write_right(text, right, y, pen, face=BODY):
    write(text, right - text_width(text, face), y, pen, face)


def icon_for(code, day=True):
    label, day_icon, night_icon = CODES.get(code, ("UNKNOWN", CLOUD, CLOUD))
    return label, (day_icon if day else night_icon)


def draw_icon(index, x, y, size):
    screen.blit(ICONS.sprite(index, 0), rect(0, 0, 16, 16), rect(x, y, size, size), image.NEAREST)


def degrees(value):
    return "%d%s" % (round(value), "F" if state["fahrenheit"] else "C")


def draw_sky(icon):
    top, low = SKIES.get(icon, SKIES[CLOUD])
    fill(0, 0, WIDTH, HEIGHT // 2, color.rgb(*top))
    fill(0, HEIGHT // 2, WIDTH, HEIGHT - HEIGHT // 2, color.rgb(*low))
    fill(0, HEIGHT - 22, WIDTH, 22, GROUND)
    fill(0, HEIGHT - 22, WIDTH, 2, GROUND_DARK)
    if icon in (RAIN, DRIZZLE, STORM):
        step = 14 if icon == DRIZZLE else 9
        for n in range(0, WIDTH, step):
            y = (n * 7 + badge.ticks // 4) % (HEIGHT - 22)
            fill(n, y, 1, 6 if icon != DRIZZLE else 3, BLUE)
    elif icon == SNOW:
        for n in range(0, WIDTH, 16):
            y = (n * 5 + badge.ticks // 14) % (HEIGHT - 22)
            fill(n + (badge.ticks // 300 + n) % 5, y, 2, 2, CREAM)


def draw_header():
    fill(0, 0, WIDTH, 22, PANEL)
    place = weather.place if weather.city == 0 else weather.name
    write("<", 6, 4, CREAM_DIM, BODY)
    write_centred(place, WIDTH // 2, 4, CREAM, BODY)
    write_right(">", WIDTH - 6, 4, CREAM_DIM, BODY)
    x = 8
    for index, label in enumerate(PAGES):
        pen = AMBER if index == page else CREAM_DIM
        write(label, x, HEIGHT - 17, pen, SMALL)
        x += text_width(label, SMALL) + 12
    # the network status sits right-aligned in the footer, kept short of the tabs
    line, pen = None, CREAM_DIM
    if weather.error:
        line, pen = ("NO WI-FI" if "Wi-Fi" in weather.error else "NO SIGNAL"), RED
    elif weather.fetch is not None:
        line, pen = weather.status.upper() + "." * (1 + (badge.ticks // 300) % 3), AMBER
    elif weather.cached:
        line = "SAVED FORECAST"
    elif weather.fetched_at is not None:
        age = (badge.ticks - weather.fetched_at) // 60000
        line = "UPDATED JUST NOW" if age < 1 else "UPDATED %dM AGO" % age
    if line:
        write_right(line[:24], WIDTH - 8, HEIGHT - 17, pen, SMALL)


def draw_mascot(icon, x, y):
    frame = 1 if icon == SUN else (2 if icon in (RAIN, DRIZZLE, STORM) else 0)
    bob = int(abs(math.sin(badge.ticks / 400)) * 3)
    screen.blit(MASCOT.sprite(frame, 0), rect(0, 0, 20, 26), rect(x, y - bob, 60, 78), image.NEAREST)


def draw_now(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    draw_icon(icon, 22, 44, 96)
    write(degrees(forecast["temp"]), 130, 40, CREAM, BIG)
    write(label, 130, 72, AMBER, BODY)
    rows = (
        ("FEELS", degrees(forecast["feels"])),
        ("HUMIDITY", "%d%%" % forecast["humidity"]),
        ("WIND", "%d %s" % (round(forecast["wind"]), forecast["units"][1].upper())),
        ("SUN", "%s - %s" % (forecast["sunrise"], forecast["sunset"])),
    )
    for n, (name, value) in enumerate(rows):
        y = 96 + n * 20
        write(name, 130, y + 1, CREAM_DIM, SMALL)
        write(value, 196, y, CREAM, BODY)
    write("AS OF %s %s" % (forecast["time"], forecast["zone"]), 130, 180, CREAM_DIM, SMALL)
    draw_mascot(icon, 36, 140)


def draw_hourly(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    hours = forecast["hours"][:12]
    temps = [h[1] for h in hours]
    low, high = min(temps), max(temps)
    span = max(1.0, high - low)
    width = (WIDTH - 16) // len(hours)
    fill(8, 26, WIDTH - 16, HEIGHT - 50, TRACK)
    for n, (when, temp, code, rain) in enumerate(hours):
        x = 8 + n * width
        day = forecast["day"] if n < 1 else not (int(when[:2]) < 7 or int(when[:2]) >= 19)
        _, hour_icon = icon_for(code, day)
        write_centred(when[:2], x + width // 2, 30, CREAM_DIM, SMALL)
        draw_icon(hour_icon, x + width // 2 - 8, 44, 16)
        bar_h = int(20 + 70 * (temp - low) / span)
        fill(x + 4, 170 - bar_h, width - 8, bar_h, AMBER if temp == high else CREAM)
        write_centred("%d" % round(temp), x + width // 2, 170 - bar_h - 14, CREAM, SMALL)
        if rain:
            write_centred("%d%%" % rain, x + width // 2, 174, BLUE, SMALL)
    write("NEXT 12 HOURS", 12, 196, CREAM_DIM, SMALL)
    write_right("RAIN CHANCE IN BLUE", WIDTH - 12, 196, BLUE, SMALL)


def draw_week(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    days = forecast["days"][:6]
    lows = [d[3] for d in days]
    highs = [d[2] for d in days]
    coldest, hottest = min(lows), max(highs)
    span = max(1.0, hottest - coldest)
    fill(8, 26, WIDTH - 16, HEIGHT - 50, TRACK)
    for n, (date, code, high, low, rain) in enumerate(days):
        y = 30 + n * 27
        name = "TODAY" if n == 0 else WEEKDAYS[weekday(date)]
        write(name, 14, y + 4, CREAM, BODY)
        _, day_icon = icon_for(code, True)
        draw_icon(day_icon, 72, y, 20)
        write_right(degrees(low), 136, y + 4, CREAM_DIM, BODY)
        left = 144 + int(110 * (low - coldest) / span)
        right = 144 + int(110 * (high - coldest) / span)
        fill(144, y + 8, 110, 6, INK)
        fill(left, y + 8, max(6, right - left), 6, AMBER)
        write(degrees(high), 262, y + 4, CREAM, BODY)
        if rain:
            write_right("%d%%" % rain, WIDTH - 14, y + 5, BLUE, SMALL)


def draw_waiting():
    draw_sky(PARTLY)
    draw_header()
    draw_mascot(CLOUD, 36, 120)
    if weather.error:
        write_centred("NO FORECAST YET", WIDTH // 2 + 30, 80, CREAM, TITLE)
        screen.font = SMALL
        screen.pen = CREAM
        screen.text(weather.error, rect(120, 112, 190, 60), align=(LEFT, TOP))
        write_centred("SELECT: TRY AGAIN", WIDTH // 2 + 30, 180, AMBER, SMALL)
    else:
        write_centred("FETCHING THE FORECAST", WIDTH // 2 + 30, 90, CREAM, TITLE)
        write_centred(weather.status.upper() + "." * (1 + (badge.ticks // 300) % 3), WIDTH // 2 + 30, 124, AMBER, BODY)


def update():
    global page
    if badge.pressed(BUTTON_LEFT):
        change_city(-1)
    if badge.pressed(BUTTON_RIGHT):
        change_city(1)
    if badge.pressed(BUTTON_UP):
        page = (page - 1) % len(PAGES)
    if badge.pressed(BUTTON_DOWN):
        page = (page + 1) % len(PAGES)
    if badge.pressed(BUTTON_MENU):
        toggle_units()
    if badge.pressed(BUTTON_SELECT):
        weather.refresh_now()
    weather.update()
    forecast = weather.forecast
    if forecast is None:
        draw_waiting()
    elif page == 0:
        draw_now(forecast)
    elif page == 1:
        draw_hourly(forecast)
    else:
        draw_week(forecast)


def on_exit():
    save_state()


remove_file(TEMP_FILE)
run(update)
