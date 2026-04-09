import urllib.request
import sys

ids = [42063, 43431, 49260, 39574, 38771, 43689, 44713]
headers = {'User-Agent': 'Mozilla/5.0'}

print("[")
for id in ids:
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=tle"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            lines = [l.decode().strip() for l in r if l.strip()]
            if len(lines) >= 3:
                name = lines[0]
                l1 = lines[1]
                l2 = lines[2]
                print(f"    ({repr(name)}, {repr(l1)}, {repr(l2)}),")
            else:
                print(f"    # {id} - FETCH FAILED")
    except Exception as e:
        print(f"    # {id} - ERROR: {e}")
print("]")
