"""Draw the sprite sheets for Mona Slugger and Mona Hoops from pixel maps.

    python3 tools/build_sprites.py slugger <assets dir>
    python3 tools/build_sprites.py hoops <assets dir>

Each sheet is a paletted PNG with transparency. Letters pick colours; '.' is
clear. Frames sit side by side in one row.
"""
import struct
import sys
import zlib
from pathlib import Path

# GitHub's Mona as the badge's own sprites draw her: a white outline, purple
# fur, a peach face with a lighter muzzle, two-pixel eyes (glint + pupil),
# magenta cheeks, and tentacles rather than legs.
MONA = {"A": (255, 255, 255), "B": (109, 36, 170), "C": (36, 0, 170), "D": (255, 182, 170),
        "E": (182, 0, 85), "F": (255, 219, 170)}

HEAD = (
    "....A......A....",
    "...ABA....ABA...",
    "...ABBA..ABBA...",
    "..ABBBBAABBBBA..",
    "..ABBBBBBBBBBA..",
    ".ABBBBBBBBBBBBA.",
    ".ABBDDDDDDDDBBA.",
    ".ABDDABDDDABDDA.",
    ".ABDDAEDDDAEDDA.",
    ".ABDDDDDDDDDDBA.",
    ".ABDEDDFFFDDEDA.",
    "..ABDDFFFFFDDA..",
    "..ABBDDDDDDDBA..",
    "...ABBBBBBBBA...",
)

# front view, standing and mid-jump (tentacles tucked wide). 16x20.
JUMPER = (
    HEAD + (
        "..ABBBBBBBBBBA..",
        ".ABBBBBBBBBBBBA.",
        "..ABA.ABBA.ABA..",
        "..ACA.ABBA.ACA..",
        "...A...AA...A...",
        "................",
    ),
    HEAD + (
        "..ABBBBBBBBBBA..",
        ".ABBBBBBBBBBBBA.",
        "ABA...ABBA...ABA",
        "ACA...ABBA...ACA",
        ".A.....AA.....A.",
        "................",
    ),
)
JUMPER_PENS = dict(MONA)

# from above for the crosser, with a hop frame. 16x16.
CROSSER = (
    HEAD[:13] + (
        "..ABA.ABBA.ABA..",
        "..ACA.ACCA.ACA..",
        "...A...AA...A...",
    ),
    HEAD[:13] + (
        ".ABA..ABBA..ABA.",
        ".ACA..ACCA..ACA.",
        "..A....AA....A..",
    ),
)
CROSSER_PENS = dict(MONA)

# in a yellow jersey, ball at the chest, then arms up on the release. 16x24.
SHOOTER = (
    HEAD + (
        "...AJJJJJJJJA...",
        "..ABJJJJJJJJBA..",
        "..ABJJJJJJJJBA..",
        "...AJJJJJJJJA...",
        "....AJJJJJJA....",
        "...ABA.ABBA.ABA.",
        "...ACA.ACCA.ACA.",
        "....A...AA...A..",
        "................",
        "................",
    ),
    HEAD + (
        "ABAAJJJJJJJJAABA",
        "ABA.JJJJJJJJ.ABA",
        ".A.AJJJJJJJJA.A.",
        "...AJJJJJJJJA...",
        "....AJJJJJJA....",
        "...ABA.ABBA.ABA.",
        "...ACA.ACCA.ACA.",
        "....A...AA...A..",
        "................",
        "................",
    ),
)
SHOOTER_PENS = dict(MONA, J=(255, 200, 48))

PROFILE = (
    "........................",
    ".....A....A.............",
    "....ABA..ABA............",
    "....ABBAABBBA...........",
    "...ABBBBBBBBBA..........",
    "...ABBBBBBDDDA..........",
    "..ABBBBBDDDDDDA.........",
    "..ABBBBBDDABDDA.........",
    "..ABBBBBDDAEDDA.........",
    "..ABBBBBDDDDFFA.........",
    "...ABBBBDDEDFFA.........",
    "...ABBBBBDDDDA..........",
    "....ABBBBBBBA...........",
)
# a right-handed batter in profile: ready with the bat up, the swing across
# the plate, and the follow-through. 24x24 each.
BATTER = (
    PROFILE + (
        ".....AKKKKKKA......HH...",
        "....AKKKKKKKKA....HH....",
        "....AKKKKKKKKKA..BB.....",
        "....AKKKKKKKKKBBB.......",
        "....AKKKKKKKKA..........",
        ".....AKKKKKKA...........",
        "....ABA.ABBA.ABA........",
        "....ACA.ACCA.ACA........",
        ".....A...AA...A.........",
        "........................",
        "........................",
    ),
    PROFILE + (
        ".....AKKKKKKA...........",
        "....AKKKKKKKKKBBBBBBBBBH",
        "....AKKKKKKKKKBBBBHHHHHH",
        "....AKKKKKKKKKA.........",
        "....AKKKKKKKKA..........",
        ".....AKKKKKKA...........",
        "....ABA.ABBA.ABA........",
        "....ACA.ACCA.ACA........",
        ".....A...AA...A.........",
        "........................",
        "........................",
    ),
    PROFILE + (
        ".....AKKKKKKA...........",
        "...BBAKKKKKKKKA.........",
        ".HHBB.AKKKKKKKKA........",
        "HH....AKKKKKKKKA........",
        ".....AKKKKKKKKA.........",
        ".....AKKKKKKA...........",
        "....ABA.ABBA.ABA........",
        "....ACA.ACCA.ACA........",
        ".....A...AA...A.........",
        "........................",
        "........................",
    ),
)
BATTER_PENS = dict(MONA, K=(220, 60, 60), H=(220, 180, 120))

# the pitcher far away: set, and the arm up in the windup. 12x16 each.
PITCHER = (
    (
        "...P....P...",
        "...PPPPPP...",
        "..PPEPPEPP..",
        "..PPPPPPPP..",
        "...PPPPPP...",
        "....UUUU....",
        "...UUUUUU...",
        "..PUUUUUUP..",
        "..P.UUUU.P..",
        "....UUUU....",
        "....UU.UU...",
        "....UU.UU...",
        "....PP.PP...",
        "...SS..SS...",
        "............",
        "............",
    ),
    (
        "...P....P.PP",
        "...PPPPPP.P.",
        "..PPEPPEPPP.",
        "..PPPPPPPP..",
        "...PPPPPP...",
        "....UUUU....",
        "...UUUUUUP..",
        "..PUUUUUU...",
        "..P.UUUU....",
        "....UUUU....",
        "....UU.UU...",
        "....UU.UU...",
        "....PP.PP...",
        "...SS..SS...",
        "............",
        "............",
    ),
)
PITCHER_PENS = {"P": (48, 96, 200), "E": (30, 30, 40), "U": (240, 240, 240), "S": (40, 40, 40)}

BASEBALL = (
    ".WWWW.",
    "WRWWRW",
    "WWRRWW",
    "WWRRWW",
    "WRWWRW",
    ".WWWW.",
)
BASEBALL_PENS = {"W": (250, 250, 250), "R": (220, 60, 60)}

BASKETBALL = (
    "..OOOO..",
    ".OOKOOO.",
    "OOOKOOOO",
    "KKKKKKKK",
    "OOOKOOOO",
    "OOOKOOOO",
    ".OOKOOO.",
    "..OOOO..",
)
BASKETBALL_PENS = {"O": (240, 130, 40), "K": (60, 30, 20)}

# platforms for the jumper: solid, crumbling, and a spring. 24x6 / 10x8.
PLATFORM = (
    "GGGGGGGGGGGGGGGGGGGGGGGG",
    "GgggggggggggggggggggggggG",
    "DDDDDDDDDDDDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDDDDDDDDDD",
    ".DDDDDDDDDDDDDDDDDDDDDD.",
    "..DDDDDDDDDDDDDDDDDDDD..",
)
CRUMBLE = (
    "RRRRRR.RRRRRRRRR.RRRRRRR",
    "rrrrrr.rrrrrrrrr.rrrrrrr",
    "BBBBB...BBBBBBB...BBBBBB",
    "BBBB.....BBBBB.....BBBBB",
    ".BBB.....BBBB.......BBB.",
    "..BB......BBB........BB.",
)
SPRING = (
    "..KKKKKK..",
    ".KKKKKKKK.",
    "..S....S..",
    "...S..S...",
    "..S....S..",
    "...S..S...",
    ".KKKKKKKK.",
    "KKKKKKKKKK",
)
PLATFORM_PENS = {"G": (90, 200, 90), "g": (140, 230, 120), "D": (120, 80, 40),
                 "R": (200, 100, 80), "r": (230, 150, 120), "B": (110, 70, 50),
                 "K": (220, 80, 60), "S": (240, 240, 240)}

# traffic seen from above, heading right (flipped at draw time for the other
# lane): a car, a truck, and a log for the river. 24x12 / 36x12.
CAR = (
    "....CCCCCCCCCCCCCCC.....",
    "..CCCCCCCWWWCCCCCCCCC...",
    ".CCCCCCCWWWWWCCCCCCCCCC.",
    "CCCCCCCCWWWWWCCCCCCCCCCY",
    "CCCCCCCCWWWWWCCCCCCCCCCY",
    ".CCCCCCCWWWWWCCCCCCCCCC.",
    "..CCCCCCCWWWCCCCCCCCC...",
    "....CCCCCCCCCCCCCCC.....",
    "...KK............KK.....",
    "...KK............KK.....",
    "........................",
    "........................",
)
TRUCK = (
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCCCCCCCC.",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCC",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCY",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCY",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCY",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCY",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCWWCCCCCC",
    "TTTTTTTTTTTTTTTTTTTTTTTT.CCCCCCCCCC.",
    "..KK............KK.....KK........KK.",
    "..KK............KK.....KK........KK.",
    "....................................",
    "....................................",
)
LOG = (
    ".LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL.",
    "LLLLLLLlLLLLLLLLLLLlLLLLLLLLLLLLLLLL",
    "LLLllLLLLLLLLllLLLLLLLLLllLLLLLLLLLL",
    "LLLLLLLLLLlLLLLLLLLLLLLLLLLLllLLLLLL",
    "LLLLlLLLLLLLLLLLLLllLLLLLLLLLLLLLlLL",
    "LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL",
    ".LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL.",
    "....................................",
    "....................................",
    "....................................",
    "....................................",
    "....................................",
)
TRAFFIC_PENS = {"C": (230, 70, 70), "W": (170, 220, 250), "Y": (255, 230, 120), "K": (30, 30, 40),
                "T": (80, 140, 220), "L": (130, 90, 50), "l": (170, 120, 70)}

# weather icons, 16x16: sun, partly cloudy, cloud, drizzle, rain, snow, storm, fog, moon, partly cloudy night
SUN = (
    "................",
    ".......Y........",
    "...Y...Y...Y....",
    "....Y.....Y.....",
    "......YYYY......",
    ".....YYYYYY.....",
    "....YYYYYYYY....",
    ".YY.YYYYYYYY.YY.",
    "....YYYYYYYY....",
    ".....YYYYYY.....",
    "......YYYY......",
    "....Y.....Y.....",
    "...Y...Y...Y....",
    ".......Y........",
    "................",
    "................",
)
CLOUD = (
    "................",
    "................",
    "................",
    "......WWWW......",
    ".....WWWWWW.....",
    "...WWWWWWWWWW...",
    "..WWWWWWWWWWWW..",
    ".WWWWWWWWWWWWWW.",
    ".WWWWWWWWWWWWWW.",
    "..WWWWWWWWWWWW..",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
)
def over(base, top):
    return tuple(''.join(t if t != '.' else b for b, t in zip(brow, trow)) for brow, trow in zip(base, top))
PARTLY = over((
    "................",
    "..........Y.....",
    "........Y.Y.Y...",
    ".........YYY....",
    ".......YYYYYYY..",
    ".........YYY....",
    "........Y.Y.Y...",
    "..........Y.....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
), tuple(row.replace('W', 'w') for row in CLOUD[:0]) + CLOUD)
DRIZZLE = over(CLOUD, (
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "....b.....b.....",
    "................",
    ".......b........",
    "................",
    "....b.....b.....",
    "................",
))
RAIN = over(CLOUD, (
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "...b...b...b....",
    "...b...b...b....",
    ".....b...b......",
    ".....b...b......",
    "...b...b...b....",
    "...b...b...b....",
))
SNOW = over(CLOUD, (
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "...A.......A....",
    "..AAA..A..AAA...",
    "...A..AAA..A....",
    ".......A........",
    "....A.....A.....",
    "...AAA...AAA....",
))
STORM = over(tuple(row.replace('W', 'G') for row in CLOUD), (
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "........YY......",
    ".......YY.......",
    "......YYYY......",
    ".......YY.......",
    "......YY........",
    ".....Y..........",
    "................",
))
FOG = (
    "................",
    "................",
    "................",
    "..GGGGGGGGGGG...",
    "................",
    "....GGGGGGGGGGG.",
    "................",
    ".GGGGGGGGGGGG...",
    "................",
    "...GGGGGGGGGGG..",
    "................",
    ".GGGGGGGGGG.....",
    "................",
    "................",
    "................",
    "................",
)
MOON = (
    "................",
    "................",
    "......LLLL......",
    ".....LLLLLL.....",
    "....LLLL........",
    "...LLLL.........",
    "...LLL..........",
    "...LLL..........",
    "...LLL..........",
    "...LLLL.........",
    "....LLLL....L...",
    ".....LLLLLLLL...",
    "......LLLLLL....",
    "................",
    "................",
    "................",
)
NIGHT_CLOUD = over((
    "................",
    "........LLL.....",
    ".......LLLLL....",
    "......LLL.......",
    "......LLL.......",
    "......LLLL..L...",
    ".......LLLLLL...",
    "........LLLL....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
), CLOUD)
WEATHER_PENS = {"Y": (255, 210, 60), "W": (240, 240, 245), "G": (150, 150, 165), "b": (90, 160, 240),
                "A": (255, 255, 255), "L": (240, 230, 160)}

# the mascot for the weather app: plain, in sunglasses, under an umbrella. 20x26.
def mascot(extra_top, glasses):
    head = list(HEAD)
    if glasses:
        head[7] = ".ABDSSSSDDSSSSDA."[:16]
        head[8] = ".ABDSSSDDDDSSSDA."[:16]
        head[7] = ".ABSSSSDDSSSSDA."
        head[8] = ".ABDSSSDDDSSSDA."
    rows = ["." * 20 for _ in range(6)]
    if extra_top:
        rows = list(extra_top)
    body = [
        "..ABBBBBBBBBBA..",
        ".ABBBBBBBBBBBBA.",
        "..ABA.ABBA.ABA..",
        "..ACA.ABBA.ACA..",
        "...A...AA...A...",
        "................",
    ]
    return tuple(rows) + tuple(".." + r + ".." for r in head + body)
UMBRELLA = (
    ".......UUUUUU.......",
    ".....UUUUUUUUUU.....",
    "...UUUUUUUUUUUUUU...",
    "..UUUUUUUUUUUUUUUU..",
    ".UUUUUUUUUUUUUUUUUU.",
    ".........KK.........",
)
MASCOT = (mascot(None, False), mascot(None, True), mascot(UMBRELLA, False))
MASCOT_PENS = dict(MONA, S=(30, 30, 40), U=(230, 70, 70), K=(60, 40, 30))


def png(path, width, height, palette, pixels):
    rows = b"".join(b"\x00" + bytes(pixels[y * width:(y + 1) * width]) for y in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
            + chunk(b"PLTE", b"".join(bytes(entry[:3]) for entry in palette))
            + chunk(b"tRNS", bytes(entry[3] for entry in palette))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    Path(path).write_bytes(data)
    print(path, width, "x", height, len(data), "bytes")


class Sheet:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.palette = [(0, 0, 0, 0)]
        self.pixels = [0] * (width * height)

    def put(self, x, y, rgb):
        entry = (rgb[0], rgb[1], rgb[2], 255)
        if entry not in self.palette:
            self.palette.append(entry)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = self.palette.index(entry)

    def stamp(self, rows, pens, left, top):
        for y, line in enumerate(rows):
            for x, key in enumerate(line):
                if key in pens:
                    self.put(left + x, top + y, pens[key])


def strip(path, frames, pens):
    width, height = len(frames[0][0]), len(frames[0])
    sheet = Sheet(width * len(frames), height)
    for index, rows in enumerate(frames):
        sheet.stamp(rows, pens, index * width, 0)
    png(path, sheet.width, sheet.height, sheet.palette, sheet.pixels)


def main():
    game = sys.argv[1]
    assets = Path(sys.argv[2])
    assets.mkdir(exist_ok=True)
    if game == "slugger":
        strip(assets / "batter.png", BATTER, BATTER_PENS)
        strip(assets / "pitcher.png", PITCHER, PITCHER_PENS)
        strip(assets / "ball.png", (BASEBALL,), BASEBALL_PENS)
    elif game == "hoops":
        strip(assets / "shooter.png", SHOOTER, SHOOTER_PENS)
        strip(assets / "ball.png", (BASKETBALL,), BASKETBALL_PENS)
    elif game == "jump":
        strip(assets / "jumper.png", JUMPER, JUMPER_PENS)
        strip(assets / "platforms.png", (PLATFORM, CRUMBLE), PLATFORM_PENS)
        strip(assets / "spring.png", (SPRING,), PLATFORM_PENS)
    elif game == "weather":
        strip(assets / "icons.png", (SUN, PARTLY, CLOUD, DRIZZLE, RAIN, SNOW, STORM, FOG, MOON, NIGHT_CLOUD), WEATHER_PENS)
        strip(assets / "mascot.png", MASCOT, MASCOT_PENS)
    elif game == "crossing":
        strip(assets / "crosser.png", CROSSER, CROSSER_PENS)
        strip(assets / "car.png", (CAR,), TRAFFIC_PENS)
        strip(assets / "truck.png", (TRUCK,), TRAFFIC_PENS)
        strip(assets / "log.png", (LOG,), TRAFFIC_PENS)
    else:
        raise SystemExit("game must be slugger, hoops, jump, crossing or weather")


if __name__ == "__main__":
    main()
