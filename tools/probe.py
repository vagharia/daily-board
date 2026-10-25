"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: X's embedded-timeline (syndication) page for a list of officials and journalists: does the handle
exist, how many posts come back, how recent the newest is, and how many are from the last three days."""
import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

HANDLES = """
realDonaldTrump POTUS WhiteHouse SecRubio StateDept StateDeptSpox DeptofWar SecWar PeteHegseth CENTCOM PressSec
USAdarFarsi US5thFleet USAFCENT USUN StateDept_NEA USAmbIsrael GovMikeHuckabee SEPeaceMissions JDVance
IsraeliPM netanyahu IDF Israel_katz IsraelMFA gidonsaar LTC_Shoshani AvichayAdraee IsraelPersian Israel_MOD dannydanon
khamenei_ir Khamenei_fa drpezeshkian araghchi IRIMFA_SPOX IRIMFA_EN Iran_UN mb_ghalibaf JZarif IRIMFA Gharibabadi
Takhtravanchi
mfa_russia MID_RF KremlinRussia_E MedvedevRussiaE RussiaUN Amb_Ulyanov Dpol_un
MFA_China SpokespersonCHN SpoxCHN_MaoNing SpoxCHN_LinJian Chinamission2un globaltimesnews HuXijin_GT XHNews
CGTNOfficial
BarakRavid laurnorman farnazfassihi JenGriffinFNC NatashaBertrand idreesali114 phildstewart lrozen ckubeNBC
JacquiHeinrich kylieatwood jongambrellAP EricSchmittNYT helenecooper laraseligman glubold AlexWardVox jonathanvswan
JDiamond1 DanLamothe APDiploWriter humeyra_pamuk jmhansler
manniefabian amit_segal talshalev1 yossi_melman AmosHarel yanivkubovich Doron_Kadosh OrHeller nirdvori
AviIssacharoff BenCaspit arik3000 LahavHarkov sfrantzman yonahjeremybob AmichaiStein1 ItayBlumental
jasonrezaian NegarMortazavi GEsfandiari SanamVakil alihashem_tv abasaslani s_m_marandi HoseinDalirian maziarbahari
hdagres
""".split()
URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}"


def ts(s):
    try:
        return int(datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y").timestamp())
    except Exception:  # noqa: BLE001
        return 0


def probe(h):
    r = http.get(URL.format(h=h), timeout=25, retries=0, headers={"Accept": "text/html"})
    t = r.text or ""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not m:
        return {"code": r.status_code, "len": len(t), "no_data": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:160]}
    d = json.loads(m.group(1))
    entries = (((d.get("props") or {}).get("pageProps") or {}).get("timeline") or {}).get("entries") or []
    tw = [e.get("content", {}).get("tweet") or {} for e in entries if e.get("type") == "tweet"]
    times = sorted((ts(x.get("created_at", "")) for x in tw), reverse=True)
    now = time.time()
    newest = max(tw, key=lambda x: ts(x.get("created_at", "")), default={})
    user = (newest.get("user") or {})
    return {"code": r.status_code, "n": len(tw), "newest": newest.get("created_at"),
            "last3d": sum(1 for x in times if now - x < 3 * 86400), "last24h": sum(1 for x in times if now - x < 86400),
            "name": user.get("name"), "followers": user.get("followers_count"),
            "sample": re.sub(r"\s+", " ", newest.get("full_text") or newest.get("text") or "")[:140]}


# sequential with a pause, to see how many requests the endpoint allows before it starts refusing (HTTP 429)
ORDER = ["BarakRavid", "araghchi", "MFA_China", "mfa_russia", "IDF", "CENTCOM", "IRIMFA_SPOX", "manniefabian",
         "amit_segal", "jongambrellAP", "Amb_Ulyanov", "KremlinRussia_E", "SpoxCHN_MaoNing", "netanyahu",
         "SecRubio", "StateDept", "IsraeliPM", "Israel_katz", "khamenei_ir", "drpezeshkian", "laurnorman",
         "farnazfassihi", "AvichayAdraee", "gidonsaar", "MedvedevRussiaE", "Chinamission2un", "LTC_Shoshani",
         "s_m_marandi", "abasaslani", "jasonrezaian"]
out = {"t": int(time.time()), "x": {}, "log": []}
for i, h in enumerate(ORDER):
    t0 = time.time()
    try:
        out["x"][h] = probe(h)
    except Exception as e:  # noqa: BLE001
        out["x"][h] = {"err": str(e)[:140]}
    out["log"].append([i, h, round(time.time() - t0, 1), out["x"][h].get("err") or out["x"][h].get("n")])
    time.sleep(4)
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("probe done", len(out["x"]))
