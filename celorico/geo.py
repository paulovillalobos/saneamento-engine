"""Plot checks against DGT/SNIT map services (no authentication).

For a point (WGS84), fetch the features whose box touches a ~20 m square around it,
then keep only polygons that actually contain the point. Each answer records the
service URL, the raw response hash and the feature's own attributes, so it can be
re-checked later. Responses are stored under sources/geo/.

Every response is stored as a capture (kind geo.wfs.response) with its query, so it can be
replayed. Known bug, fixed in R6: rings after the first are all treated as holes, so a point in
the second part of a multi-part feature is reported as outside.

Services (Celorico de Basto, DTCC 0305):
- land-use classes (CRUS), vector:  SDISNITWFSCRUS_0305_1
- national agricultural reserve (RAN), vector: SDISNITWFSSRUP_RAN_PT1
- REN (ecological reserve) for Celorico is published as WMS images only; not queried here.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.sources import Store  # noqa: E402

UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://servicos.dgterritorio.pt/{service}/WFService.aspx"
LAYERS = {
    "land_use": {"service": "SDISNITWFSCRUS_{dtcc}_1", "type": "gmgml:CRUS_{name}_V",
                 "fields": ["Classe", "Categoria", "Designacao_PlantaOrdenamento", "Data_PublicacaoPDM", "Escala_PlantaOrdenamento"]},
    "ran": {"service": "SDISNITWFSSRUP_RAN_PT1", "type": "gmgml:RAN", "fields": None},
}
MUNICIPALITIES = {"0305": "Celorico_de_Basto"}
FEATURE = re.compile(r"<gml:featureMember>(.*?)</gml:featureMember>", re.S)
POSLIST = re.compile(r"<gml:posList[^>]*>([^<]+)</gml:posList>")
FIELD = re.compile(r"<gmgml:([A-Za-z_À-ÿ]+)>([^<]*)</gmgml:\1>")


def fetch(layer, lat, lon, dtcc="0305", half=0.0001):
    """Returns (service, typeName, params, url, body bytes)."""
    spec = LAYERS[layer]
    service = spec["service"].format(dtcc=dtcc)
    params = {
        "service": "WFS", "version": "1.1.0", "request": "GetFeature",
        "typeName": spec["type"].format(name=MUNICIPALITIES[dtcc]),
        "srsName": "EPSG:4326",
        "bbox": f"{lat - half},{lon - half},{lat + half},{lon + half},EPSG:4326",
    }
    url = BASE.format(service=service) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=60).read()
    return service, params["typeName"], params, url, body


def rings(feature_xml):
    """Each posList as a list of (lat, lon) pairs (WFS 1.1.0 / EPSG:4326 axis order)."""
    out = []
    for pl in POSLIST.findall(feature_xml):
        nums = [float(x) for x in pl.split()]
        out.append(list(zip(nums[0::2], nums[1::2])))
    return out


def contains(ring, lat, lon):
    inside = False
    for (y1, x1), (y2, x2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def query(layer, lat, lon, dtcc="0305"):
    service, type_name, params, url, raw = fetch(layer, lat, lon, dtcc)
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    capture = Store().add_capture(
        raw, kind="geo.wfs.response", subject=f"geo:dgt:{service}:{type_name}",
        origin=BASE.format(service=service), method="https-get@1", media_type="application/xml",
        retrieved_at=retrieved_at, query=dict(params, point={"lat": lat, "lon": lon}, status="recorded at retrieval"))
    return evaluate(layer, lat, lon, raw.decode("utf-8"), capture)


def evaluate(layer, lat, lon, body, capture):
    """Point-in-polygon over a stored response; deterministic, so it can be replayed."""
    digest = capture["capture"]
    url = capture["origin"]
    retrieved_at = capture["retrieved_at"]
    hits = []
    for fx in FEATURE.findall(body):
        rs = rings(fx)
        # first ring is the exterior; later rings are holes (point must not be in a hole)
        if rs and contains(rs[0], lat, lon) and not any(contains(h, lat, lon) for h in rs[1:]):
            attrs = dict(FIELD.findall(fx))
            keep = LAYERS[layer]["fields"]
            hits.append({k: v for k, v in attrs.items() if keep is None or k in keep or k == "ID"})
    return {
        "layer": layer, "point": {"lat": lat, "lon": lon}, "service_url": url,
        "retrieved_at": retrieved_at,
        "response_sha256": digest, "candidates": len(FEATURE.findall(body)),
        "contains_point": hits,
        "status": "found" if hits else ("outside_all_candidates" if FEATURE.findall(body) else "no_feature"),
    }


if __name__ == "__main__":
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    for layer in ("land_use", "ran"):
        print(json.dumps(query(layer, lat, lon), ensure_ascii=False, indent=1))
