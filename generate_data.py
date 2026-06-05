from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone, timedelta
import random
import math

INFLUXDB_URL    = "http://localhost:8086"
INFLUXDB_TOKEN  = "JsUtzRLzVNWE7xRUuPNQtl2enK39ms5wVFqXtpqXBb47LnslJc1oZN20t4qlsDSv22cqwT8aTwwzP76o-QXoSA=="
INFLUXDB_ORG    = "smarthome"
INFLUXDB_BUCKET = "energy"

FAZA_PRZED_START = datetime(2026, 5, 1,  0, 0, 0, tzinfo=timezone.utc)
FAZA_PRZED_STOP  = datetime(2026, 5, 15, 23, 59, 0, tzinfo=timezone.utc)
FAZA_PO_START    = datetime(2026, 5, 16, 0, 0, 0, tzinfo=timezone.utc)
FAZA_PO_STOP     = datetime(2026, 5, 31, 23, 59, 0, tzinfo=timezone.utc)
INTERWAL_MIN     = 10

def noise(scale=0.1):
    return random.gauss(0, scale)

def smooth_hour(hour, minute):
    return hour + minute / 60.0

def mieszkanie_przed(h, m, weekday):
    t = smooth_hour(h, m)
    if 0 <= t < 5.5:
        base = 0.55 + 0.08 * math.sin(t * math.pi / 3)
    elif 5.5 <= t < 9:
        base = 0.6 + 1.4 * (1 - math.exp(-(t - 5.5) * 1.5))
    elif 9 <= t < 16:
        if weekday < 5:
            base = 0.75 + 0.15 * math.sin(t * math.pi / 8)
        else:
            base = 1.4 + 0.3 * math.sin(t * math.pi / 6)
    elif 16 <= t < 22:
        base = 1.6 + 0.9 * math.sin((t - 16) * math.pi / 6)
    else:
        base = 0.58 + 0.05 * math.sin(t * math.pi)
    return round(max(0.3, base + noise(0.12)), 3)

def mieszkanie_po(h, m, weekday):
    t = smooth_hour(h, m)
    if 0 <= t < 5.5:
        base = 0.04 + 0.01 * math.sin(t)
    elif 5.5 <= t < 9:
        base = 0.05 + 1.3 * (1 - math.exp(-(t - 5.5) * 1.5))
    elif 9 <= t < 16:
        if weekday < 5:
            base = 0.07 + 0.02 * math.sin(t)
        else:
            base = 1.1 + 0.2 * math.sin(t * math.pi / 6)
    elif 16 <= t < 22:
        base = 1.5 + 0.75 * math.sin((t - 16) * math.pi / 6)
    elif 22 <= t < 23:
        base = 0.8 * math.exp(-(t - 22) * 2)
    else:
        base = 0.04
    return round(max(0.03, base + noise(0.08)), 3)

def biuro_przed(h, m, weekday):
    t = smooth_hour(h, m)
    if weekday >= 5:
        base = 0.85 + 0.12 * math.sin(t * math.pi / 12)
    elif 0 <= t < 7:
        base = 1.05 + 0.1 * math.sin(t * math.pi / 4)
    elif 7 <= t < 8:
        base = 1.05 + 1.1 * (t - 7)
    elif 8 <= t < 17:
        base = 3.6 + 0.4 * math.sin((t - 8) * math.pi / 9)
    elif 17 <= t < 18:
        base = 3.6 - 1.8 * (t - 17)
    else:
        base = 1.05 + 0.08 * math.sin(t * math.pi / 6)
    return round(max(0.7, base + noise(0.18)), 3)

def biuro_po(h, m, weekday):
    t = smooth_hour(h, m)
    if weekday >= 5:
        base = 0.11 + 0.02 * math.sin(t * math.pi / 12)
    elif 0 <= t < 7:
        base = 0.11 + 0.02 * math.sin(t)
    elif 7 <= t < 8:
        base = 0.11 + 1.1 * (t - 7)
    elif 8 <= t < 17:
        base = 3.3 + 0.35 * math.sin((t - 8) * math.pi / 9)
    elif 17 <= t < 18:
        base = 3.3 - 3.1 * (t - 17)
    else:
        base = 0.11 + 0.02 * math.sin(t)
    return round(max(0.09, base + noise(0.13)), 3)

def hala_przed(h, m, weekday):
    t = smooth_hour(h, m)
    if weekday >= 6:
        base = 3.8 + 0.4 * math.sin(t * math.pi / 12)
    elif 0 <= t < 6:
        base = 4.2 + 0.3 * math.sin(t * math.pi / 3)
    elif 6 <= t < 22:
        base = 11.0 + 4.5 * math.sin((t - 6) * math.pi / 16)
    else:
        base = 4.2 + 0.2 * math.sin(t)
    return round(max(3.0, base + noise(0.7)), 3)

def hala_po(h, m, weekday):
    t = smooth_hour(h, m)
    if weekday >= 6:
        base = 2.1 + 0.2 * math.sin(t * math.pi / 12)
    elif 0 <= t < 6:
        base = 2.1 + 0.15 * math.sin(t * math.pi / 3)
    elif 6 <= t < 10:
        base = 10.5 + 4.0 * math.sin((t - 6) * math.pi / 8)
    elif 10 <= t < 10.5:
        drop = (t - 10) / 0.5
        base = (10.5 + 4.0 * math.sin(4 * math.pi / 8)) * (1 - drop) + 3.5 * drop
    elif 10.5 <= t < 11:
        rise = (t - 10.5) / 0.5
        base = 3.5 + (10.5 + 3.5 * math.sin(4.5 * math.pi / 8) - 3.5) * rise
    elif 11 <= t < 18:
        base = 10.5 + 3.5 * math.sin((t - 6) * math.pi / 16)
    elif 18 <= t < 18.5:
        drop = (t - 18) / 0.5
        base = (10.5 + 3.5 * math.sin(12 * math.pi / 16)) * (1 - drop) + 3.2 * drop
    elif 18.5 <= t < 19:
        rise = (t - 18.5) / 0.5
        base = 3.2 + (10.0 - 3.2) * rise
    elif 19 <= t < 22:
        base = 10.0 + 2.5 * math.sin((t - 19) * math.pi / 6)
    else:
        base = 2.1 + 0.15 * math.sin(t)
    return round(max(2.0, base + noise(0.55)), 3)

def generate_points(start, stop, faza):
    points = []
    current = start
    total = int((stop - start).total_seconds() / 60 / INTERWAL_MIN)
    count = 0
    while current <= stop:
        h = current.hour
        m = current.minute
        wd = current.weekday()
        if faza == "przed":
            vals = [
                ("mieszkanie", mieszkanie_przed(h, m, wd)),
                ("biuro",      biuro_przed(h, m, wd)),
                ("hala",       hala_przed(h, m, wd)),
            ]
        else:
            vals = [
                ("mieszkanie", mieszkanie_po(h, m, wd)),
                ("biuro",      biuro_po(h, m, wd)),
                ("hala",       hala_po(h, m, wd)),
            ]
        for loc, pwr in vals:
            points.append(
                Point("energy_consumption")
                .tag("location", loc)
                .tag("faza", faza)
                .field("power", pwr)
                .time(current, write_precision="s")
            )
        current += timedelta(minutes=INTERWAL_MIN)
        count += 1
        if count % 500 == 0:
            print(f"  [{faza.upper()}] {round(count/total*100)}% ({count}/{total})")
    return points

def main():
    if INFLUXDB_TOKEN == "WKLEJ_TUTAJ_SWOJ_TOKEN":
        print("Uzupełnij INFLUXDB_TOKEN w skrypcie!")
        return
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    print("Generowanie fazy PRZED (1-15 maja)...")
    pts = generate_points(FAZA_PRZED_START, FAZA_PRZED_STOP, "przed")
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=pts)
    print(f"Zapisano {len(pts)} punktów.")

    print("Generowanie fazy PO (16-31 maja)...")
    pts2 = generate_points(FAZA_PO_START, FAZA_PO_STOP, "po")
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=pts2)
    print(f"Zapisano {len(pts2)} punktów.")

    client.close()
    print(f"Gotowe! Łącznie {len(pts)+len(pts2)} punktów.")
    print("Otwórz Grafanę i ustaw zakres: 1-31 maja 2026")

if __name__ == "__main__":
    main()