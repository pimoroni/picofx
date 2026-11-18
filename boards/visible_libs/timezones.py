# SPDX-FileCopyrightText: 2026 Ryan Hill for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Local time in a named time zone, daylight saving included, for programs that show the time of day.
# The board's clock stays on UTC (Coordinated Universal Time), as NTP sets it. Each reading is shifted
# from it, so a clock left running stays right across a changeover. Adapted from timezones.py in
# pimoroni/artmatrix, whose zone names it shares.

import time


# Daylight saving rules, each giving when the clocks go forward, then back, as (month, week, weekday,
# hour), then whether those hours are UTC. Week 0 is the month's last and 1 to 4 count from its start.
# Weekday 0 is Monday. Hours not in UTC are local standard time, as 23:00 for 24:00 daylight time
RULES = {
    "eu": ((3, 0, 6, 1), (10, 0, 6, 1), True),
    "us": ((3, 2, 6, 2), (11, 1, 6, 1), False),
    "australia": ((10, 1, 6, 2), (4, 1, 6, 2), False),
    "nz": ((9, 0, 6, 2), (4, 1, 6, 2), False),
    "egypt": ((4, 0, 4, 0), (10, 0, 3, 23), False),
    "cuba": ((3, 2, 6, 0), (11, 1, 6, 0), False),
}

# Each zone as (key, name, minutes ahead of UTC in standard time, daylight saving rule), west to east.
# A key is what TIME_ZONE in secrets.py holds
ZONES = (
    ("american_samoa", "American Samoa", -660, None),
    ("hawaii", "Hawaii", -600, None),
    ("alaska", "Alaska", -540, "us"),
    ("pacific", "US & Canada Pacific", -480, "us"),
    ("arizona", "Arizona", -420, None),
    ("mountain", "US & Canada Mountain", -420, "us"),
    ("mexico", "Mexico City", -360, None),
    ("central", "US & Canada Central", -360, "us"),
    ("colombia", "Colombia, Peru & Panama", -300, None),
    ("cuba", "Cuba", -300, "cuba"),
    ("eastern", "US & Canada Eastern", -300, "us"),
    ("venezuela", "Venezuela, Bolivia & Puerto Rico", -240, None),
    ("atlantic", "Atlantic Canada", -240, "us"),
    ("newfoundland", "Newfoundland", -210, "us"),
    ("brazil", "Brazil & Argentina", -180, None),
    ("cape_verde", "Cape Verde", -60, None),
    ("azores", "Azores", -60, "eu"),
    ("utc", "UTC", 0, None),
    ("uk", "UK, Ireland & Portugal", 0, "eu"),
    ("west_africa", "West Africa", 60, None),
    ("central_europe", "Central Europe", 60, "eu"),
    ("eastern_europe", "Eastern Europe", 120, "eu"),
    ("egypt", "Egypt", 120, "egypt"),
    ("south_africa", "South Africa", 120, None),
    ("moscow", "Moscow, Turkey & Saudi Arabia", 180, None),
    ("iran", "Iran", 210, None),
    ("gulf", "UAE & Oman", 240, None),
    ("pakistan", "Pakistan", 300, None),
    ("india", "India & Sri Lanka", 330, None),
    ("nepal", "Nepal", 345, None),
    ("bangladesh", "Bangladesh", 360, None),
    ("indochina", "Thailand, Vietnam & Jakarta", 420, None),
    ("china", "China, Singapore & Perth", 480, None),
    ("japan", "Japan & Korea", 540, None),
    ("darwin", "Darwin", 570, None),
    ("adelaide", "Adelaide", 570, "australia"),
    ("brisbane", "Brisbane", 600, None),
    ("sydney", "Sydney, Melbourne & Hobart", 600, "australia"),
    ("solomon", "Solomon Islands & New Caledonia", 660, None),
    ("fiji", "Fiji", 720, None),
    ("nz", "New Zealand", 720, "nz"),
    ("samoa_tonga", "Samoa & Tonga", 780, None),
    ("line_islands", "Kiribati Line Islands", 840, None),
)

# The zone and UTC year the changeovers below were calculated for, so each is calculated once a year
__cached = None
__offset = 0
__forward = None
__back = None

# The key TIME_ZONE in secrets.py holds, read on first use since an edit to secrets.py needs a restart
__secrets_key = None


def __secrets_zone():
    global __secrets_key

    if __secrets_key is None:
        # A board without secrets.py or without TIME_ZONE keeps UTC, as does an empty setting
        try:
            from secrets import TIME_ZONE
        except ImportError:
            TIME_ZONE = ""
        __secrets_key = TIME_ZONE or "utc"
    return __secrets_key


def __zone(key):
    for row in ZONES:
        if row[0] == key:
            return row
    raise ValueError(f"no time zone named '{key}'. Use a key from ZONES in timezones.py, such as 'uk'")


def __changeover(year, when, minutes, in_utc):
    # Seconds since the epoch that the clocks change at, from one half of a rule
    month, week, weekday, hour = when
    if week:
        first = time.mktime((year, month, 1, 0, 0, 0, 0, 0))
        day = first + ((weekday - time.gmtime(first)[6]) % 7 + (week - 1) * 7) * 86400
    else:
        # The month's last day is the day before the next month's first
        last = time.mktime((year + month // 12, month % 12 + 1, 1, 0, 0, 0, 0, 0)) - 86400
        day = last - (time.gmtime(last)[6] - weekday) % 7 * 86400
    return day + hour * 3600 - (0 if in_utc else minutes * 60)


def utc_offset(secs=None, zone=None):
    """Calculate the minutes a zone is ahead of UTC at a time, daylight saving included.

    secs= is seconds since the epoch, now if not given. zone= is a key from ZONES, the one
    TIME_ZONE in secrets.py names if not given, and UTC where that is empty or missing.
    """
    global __cached, __offset, __forward, __back

    if secs is None:
        secs = time.time()
    if zone is None:
        zone = __secrets_zone()

    year = time.gmtime(secs)[0]

    # Check if the changeovers are for another zone or year
    if __cached != (zone, year):
        _, _, __offset, rule = __zone(zone)
        __forward = __back = None
        if rule:
            start, end, in_utc = RULES[rule]
            __forward = __changeover(year, start, __offset, in_utc)
            __back = __changeover(year, end, __offset, in_utc)
        # Set last, so an unknown zone raises on every call
        __cached = (zone, year)

    if __forward is None:
        return __offset

    # Check if the zone goes forward and back in the same calendar year, as northern zones do
    if __forward < __back:
        saving = __forward <= secs < __back
    else:
        # Southern zones go forward late in the year and back early in it
        saving = secs >= __forward or secs < __back
    return __offset + 60 if saving else __offset


def localtime(secs=None, zone=None):
    """Convert a time to a zone's local time, as the tuple time.localtime() gives.

    secs= and zone= are as utc_offset() takes them.
    """
    if secs is None:
        secs = time.time()
    return time.gmtime(secs + utc_offset(secs, zone) * 60)
