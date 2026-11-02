"""Sun and moon over Manila, from simple published approximations."""
import math
from datetime import datetime, timedelta, timezone

LAT, LON = 14.5995, 120.9842
MANILA = timezone(timedelta(hours=8))
SYNODIC = 29.530588853
NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


def manila(dt=None):
    dt = dt or datetime.now(timezone.utc)
    return dt.astimezone(MANILA)


def sun(dt):
    """Solar elevation and azimuth in degrees (NOAA approximation)."""
    u = dt.astimezone(timezone.utc)
    doy = u.timetuple().tm_yday
    hour = u.hour + u.minute / 60 + u.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hour * 60 + eqt + 4 * LON
    ha = math.radians(tst / 4 - 180)
    lat = math.radians(LAT)
    cosz = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)
    zen = math.acos(max(-1, min(1, cosz)))
    elev = 90 - math.degrees(zen)
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180
    return elev, az % 360


def moon_phase(dt):
    days = (dt.astimezone(timezone.utc) - NEW_MOON).total_seconds() / 86400
    return (days % SYNODIC) / SYNODIC


def phase_name(p):
    names = ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
             "full moon", "waning gibbous", "last quarter", "waning crescent"]
    return names[int((p * 8 + 0.5) % 8)]


def day_fraction(dt):
    m = manila(dt)
    return (m.hour * 3600 + m.minute * 60 + m.second) / 86400
