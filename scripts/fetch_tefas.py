#!/usr/bin/env python3
"""
TradeDog - TEFAS Nightly Fund Refresh

TEFAS yeni JSON API'sinden YAT (yatırım), EMK (emeklilik) ve BYF (ETF)
listesini çeker, repo köküne yat.json / emk.json / byf.json olarak yazar.

API: POST https://www.tefas.gov.tr/api/funds/fonGetiriBazliBilgiGetir
Payload: {"fonTipi": "YAT|EMK|BYF", ...}
Response: {"resultList": [{"fonKodu","fonUnvan","fonTurAciklama",
           "tefasDurum","getiri1a","getiri3a","getiri6a","getiri1y",
           "getiriyb","getiri3y","getiri5y","riskDegeri"}, ...]}

BYF için ek alan: borsaTicker (Borsa İstanbul kodu, ZGD→ZGOLD gibi).
Mapping BYF_TICKER_MAP içinde tutulur. Yeni BYF eklendiğinde buraya
girdi eklemek yeterli — backend otomatik kullanır.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

TEFAS_ROOT = "https://www.tefas.gov.tr"
LIST_ENDPOINT = f"{TEFAS_ROOT}/api/funds/fonGetiriBazliBilgiGetir"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tefas.gov.tr/FonKarsilastirma.aspx",
}

# BYF (Borsa Yatırım Fonu / ETF) için Borsa İstanbul ticker'ı ile
# TEFAS 3-harfli fon kodu eşlemesi. Yeni BYF eklendiğinde buraya yaz.
# Hangisinin TEFAS kodu hangisinin Borsa ticker'ı olduğunu kontrol:
#   Borsa: https://www.kap.org.tr/tr/sirket-bilgileri/ozet/
#   TEFAS: https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=<kod>
BYF_TICKER_MAP: dict[str, str] = {
    # TEFAS kodu -> Borsa ticker
    "ZGD": "ZGOLD",
    "ZBB": "ZPBDL",
    "ZEA": "ZPLIB",
    "ZEO": "ZPX30",
    "ZPP": "ZPLUS",
    "ZKP": "ZPLAT",
    "ZKE": "ZHYS",
    "ZBP": "ZSILV",
    "ZSR": "ZSRDQ",
    "ZTM": "ZTUR",
    "ZTR": "ZTURK",
    "ZTK": "ZTKYE",
    "ZRE": "ZGYO",
    "ZPT": "ZPETR",
    "BTL": "ISTC",
    "NBS": "NNBSD",
    "BND": "BNHTI",
    "BLH": "BLHRH",
    "BOE": "BORSA",
    "DJA": "DJIST",
    "KHO": "KHOLD",
    "LTK": "LIKIT",
    "MDL": "MDOLA",
    "OHY": "OYAKP",
    "OHS": "OYAKS",
    "OPE": "OYUME",
    "OPK": "OYAGB",
    "ILK": "ILK22",
    "FGA": "FGOLD",
    "FUS": "FSP500",
    "FGS": "FGOLDD",
    # Bilinmeyen kodlar TEFAS kodu kendisi olarak kullanılır (fallback aşağıda).
}


def list_payload(fund_type: str) -> dict[str, Any]:
    """tefas-crawler 0.5.0 ile birebir uyumlu payload."""
    return {
        "dil": "TR",
        "fonTipi": fund_type,
        "kurucuKodu": None,
        "sfonTurKod": None,
        "fonTurAciklama": None,
        "islem": 1,
        "fonTurKod": None,
        "fonGrubu": None,
        "donemGetiri1a": "1",
        "donemGetiri3a": "1",
        "donemGetiri6a": "1",
        "donemGetiri1y": "1",
        "donemGetiriyb": "1",
        "donemGetiri3y": "1",
        "donemGetiri5y": "1",
        "basTarih": None,
        "bitTarih": None,
        "calismaTipi": 2,
        "getiriOrani": "1",
    }


def fetch_funds(fund_type: str, session: requests.Session, retries: int = 3) -> list[dict[str, Any]]:
    """fund_type ∈ {YAT, EMK, BYF}. Hata varsa exponential backoff ile retry."""
    payload = list_payload(fund_type)
    for attempt in range(retries):
        try:
            resp = session.post(LIST_ENDPOINT, json=payload, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            rows = body.get("resultList") or []
            if not isinstance(rows, list):
                raise ValueError(f"Beklenmedik resultList tipi: {type(rows)}")
            return rows
        except (requests.RequestException, ValueError) as exc:
            wait = 2 ** attempt
            print(
                f"[warn] {fund_type} fetch denemesi {attempt + 1}/{retries} basarisiz: "
                f"{exc} — {wait}s bekleniyor",
                file=sys.stderr,
            )
            if attempt == retries - 1:
                raise
            time.sleep(wait)
    return []


def normalize_fund(row: dict[str, Any], fund_type: str) -> dict[str, Any]:
    """API ham satırını JSON çıktısı için sadeleştir + alan adlarını camelCase tut."""
    out: dict[str, Any] = {
        "code": (row.get("fonKodu") or "").strip().upper(),
        "name": (row.get("fonUnvan") or "").strip(),
        "category": (row.get("fonTurAciklama") or "").strip(),
        "active": bool(row.get("tefasDurum", False)),
        "risk": row.get("riskDegeri"),
        "returns": {
            "1m": row.get("getiri1a"),
            "3m": row.get("getiri3a"),
            "6m": row.get("getiri6a"),
            "1y": row.get("getiri1y"),
            "ytd": row.get("getiriyb"),
            "3y": row.get("getiri3y"),
            "5y": row.get("getiri5y"),
        },
    }
    if fund_type == "BYF":
        # Borsa ticker mapping — yoksa TEFAS kodu fallback
        out["borsaTicker"] = BYF_TICKER_MAP.get(out["code"], out["code"])
    return out


def write_json(path: Path, kind: str, rows: list[dict[str, Any]]) -> None:
    payload = {
        "kind": kind,
        "updated_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "tefas.gov.tr/api/funds/fonGetiriBazliBilgiGetir",
        "count": len(rows),
        "funds": rows,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"[ok] {path.name}: {len(rows)} fon yazildi")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    session = requests.Session()
    session.headers.update(HEADERS)

    targets = [
        ("YAT", repo_root / "yat.json", 50),   # ≥ 50 yatırım fonu beklenir (1006 gerçekte)
        ("EMK", repo_root / "emk.json", 50),   # ≥ 50 emeklilik fonu (309 gerçekte)
        ("BYF", repo_root / "byf.json", 10),   # ≥ 10 ETF (31 gerçekte)
    ]

    failures = []
    for kind, out_path, min_count in targets:
        try:
            raw = fetch_funds(kind, session)
            print(f"[info] {kind} ham kayit sayisi: {len(raw)}")
            if len(raw) < min_count:
                failures.append(
                    f"{kind}: beklenen min {min_count}, gelen {len(raw)} — saglik kontrolu basarisiz"
                )
                continue
            normalized = [normalize_fund(r, kind) for r in raw]
            # fonKodu boş olanları at
            normalized = [r for r in normalized if r["code"]]
            # Alfabetik sırala (diff hijyenik olsun)
            normalized.sort(key=lambda r: r["code"])
            write_json(out_path, kind, normalized)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{kind}: {exc}")

    if failures:
        print("\n=== HATALAR ===", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
