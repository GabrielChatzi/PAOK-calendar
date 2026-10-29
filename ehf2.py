import json, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))
base = "https://ehfec.eurohandball.com/umbraco/api/competitionmatchesapi"
q = "contentId=138859&competitionId=0NO-qzR3XKKIL4ING3vbOA"
def show(tag, ms):
    print(tag, len(ms))
    for m in ms: print("   ", m["matchID"], m["venue"]["date"]["utc"][:16], m["comp"]["round"]["name"], "|", m["homeTeam"]["team"]["fullName"], "-", m["guestTeam"]["team"]["fullName"])
init = get(f"{base}/GetInitMatches?{q}")["matches"]; show("INIT", init)
for fut, anchor in (("false", init[0]["matchID"]), ("false", init[-1]["matchID"]), ("true", init[-1]["matchID"]), ("true", init[0]["matchID"])):
    try: show(f"fut={fut} anchor={anchor}", get(f"{base}/GetMatches?{q}&matchId={anchor}&futureMatches={fut}")["matches"])
    except Exception as e: print("ERR", fut, anchor, e)
