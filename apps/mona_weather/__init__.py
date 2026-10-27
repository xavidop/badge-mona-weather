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
PANEL = color.rgb(20, 20, 32, 200)
PANEL_ALT = color.rgb(255, 255, 255, 18)
TRACK = color.rgb(20, 20, 32, 90)
BLUE_LIGHT = color.rgb(130, 200, 255)
HEADER_H = 28

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
    """A dark bar with the city in the big font, arrows for the city list; tabs in the footer."""
    fill(0, 0, WIDTH, HEADER_H, PANEL)
    place = weather.place if weather.city == 0 else weather.name
    face = TITLE if text_width(place, TITLE) <= WIDTH - 60 else BODY
    write("<", 8, 6, CREAM_DIM, TITLE)
    write_centred(place, WIDTH // 2, 2 if face == TITLE else 8, CREAM, face)
    write_right(">", WIDTH - 8, 6, CREAM_DIM, TITLE)
    fill(0, HEIGHT - 20, WIDTH, 20, PANEL)
    x = 8
    for index, label in enumerate(PAGES):
        if index == page:
            fill(x - 3, HEIGHT - 18, text_width(label, BODY) + 6, 16, AMBER)
            write(label, x, HEIGHT - 17, INK, BODY)
        else:
            write(label, x, HEIGHT - 17, CREAM, BODY)
        x += text_width(label, BODY) + 14
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
        write_right(line[:22], WIDTH - 8, HEIGHT - 17, pen, SMALL)


def draw_mascot(icon, x, y):
    frame = 1 if icon == SUN else (2 if icon in (RAIN, DRIZZLE, STORM) else 0)
    bob = int(abs(math.sin(badge.ticks / 400)) * 3)
    screen.blit(MASCOT.sprite(frame, 0), rect(0, 0, 20, 26), rect(x, y - bob, 60, 78), image.NEAREST)


def draw_now(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    # everything readable sits on one dark card; Mona stands on the grass beside it
    fill(8, HEADER_H + 6, 232, 178, PANEL)
    draw_icon(icon, 20, HEADER_H + 20, 80)
    write(degrees(forecast["temp"]), 112, HEADER_H + 10, CREAM, BIG)
    write(label, 112, HEADER_H + 42, AMBER, BODY)
    rows = (
        ("FEELS LIKE", degrees(forecast["feels"])),
        ("HUMIDITY", "%d%%" % forecast["humidity"]),
        ("WIND", "%d %s" % (round(forecast["wind"]), forecast["units"][1].upper())),
        ("SUNRISE", forecast["sunrise"]),
        ("SUNSET", forecast["sunset"]),
    )
    for n, (name, value) in enumerate(rows):
        y = HEADER_H + 70 + n * 19
        if n % 2 == 0:
            fill(12, y - 2, 224, 18, PANEL_ALT)
        write(name, 20, y + 1, CREAM_DIM, SMALL)
        write_right(value, 230, y, CREAM, BODY)
    write("AS OF %s %s" % (forecast["time"], forecast["zone"]), 20, HEADER_H + 166, CREAM_DIM, SMALL)
    draw_mascot(icon, 250, 132)


def draw_hourly(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    hours = forecast["hours"][:12]
    temps = [h[1] for h in hours]
    low, high = min(temps), max(temps)
    span = max(1.0, high - low)
    left, top, width_all = 8, HEADER_H + 6, WIDTH - 16
    fill(left, top, width_all, HEIGHT - top - 26, PANEL)
    width = width_all // len(hours)
    for n, (when, temp, code, rain) in enumerate(hours):
        x = left + n * width
        if n % 2 == 0:
            fill(x, top, width, HEIGHT - top - 26, PANEL_ALT)
        hour = int(when[:2])
        day = forecast["day"] if n < 1 else not (hour < 7 or hour >= 19)
        _, hour_icon = icon_for(code, day)
        write_centred("%d" % hour, x + width // 2, top + 4, CREAM, BODY)
        draw_icon(hour_icon, x + width // 2 - 8, top + 20, 16)
        bar_h = int(16 + 60 * (temp - low) / span)
        base = HEIGHT - 50
        fill(x + 5, base - bar_h, width - 10, bar_h, AMBER if temp == high else CREAM)
        write_centred("%d" % round(temp), x + width // 2, base - bar_h - 15, CREAM, BODY)
        if rain:
            write_centred("%d%%" % rain, x + width // 2, base + 4, BLUE_LIGHT, SMALL)
    write("NEXT 12 HOURS, %s" % ("F" if state["fahrenheit"] else "C"), left + 6, HEIGHT - 34, CREAM_DIM, SMALL)
    write_right("BLUE = CHANCE OF RAIN", WIDTH - 14, HEIGHT - 34, BLUE_LIGHT, SMALL)


def draw_week(forecast):
    label, icon = icon_for(forecast["code"], forecast["day"])
    draw_sky(icon)
    draw_header()
    days = forecast["days"][:6]
    lows = [d[3] for d in days]
    highs = [d[2] for d in days]
    coldest, hottest = min(lows), max(highs)
    span = max(1.0, hottest - coldest)
    top = HEADER_H + 6
    fill(8, top, WIDTH - 16, HEIGHT - top - 26, PANEL)
    row_h = (HEIGHT - top - 30) // len(days)
    for n, (date, code, high, low, rain) in enumerate(days):
        y = top + 4 + n * row_h
        if n % 2 == 0:
            fill(10, y - 2, WIDTH - 20, row_h, PANEL_ALT)
        name = "TODAY" if n == 0 else WEEKDAYS[weekday(date)]
        write(name, 16, y + 5, CREAM, BODY)
        _, day_icon = icon_for(code, True)
        draw_icon(day_icon, 68, y, 22)
        write_right(degrees(low), 140, y + 5, CREAM_DIM, BODY)
        bar_left = 148 + int(100 * (low - coldest) / span)
        bar_right = 148 + int(100 * (high - coldest) / span)
        fill(148, y + 8, 100, 8, INK)
        fill(bar_left, y + 8, max(8, bar_right - bar_left), 8, AMBER)
        write(degrees(high), 256, y + 5, CREAM, BODY)
        if rain:
            write_right("%d%%" % rain, WIDTH - 14, y + 6, BLUE_LIGHT, SMALL)


def draw_waiting():
    draw_sky(PARTLY)
    draw_header()
    fill(100, HEADER_H + 20, WIDTH - 110, 130, PANEL)
    draw_mascot(CLOUD, 30, 128)
    if weather.error:
        write_centred("NO FORECAST YET", 205, HEADER_H + 30, CREAM, TITLE)
        screen.font = BODY
        screen.pen = CREAM_DIM
        screen.text(weather.error, rect(112, HEADER_H + 62, WIDTH - 130, 56), align=(LEFT, TOP))
        write_centred("SELECT: TRY AGAIN", 205, HEADER_H + 124, AMBER, BODY)
    else:
        write_centred("FETCHING FORECAST", 205, HEADER_H + 40, CREAM, TITLE)
        write_centred(weather.status.upper() + "." * (1 + (badge.ticks // 300) % 3), 205, HEADER_H + 80, AMBER, BODY)


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
