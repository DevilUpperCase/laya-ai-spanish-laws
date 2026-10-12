"""Small, attributed source captures for parser verification; not a completeness audit."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def capture(client, url, target):
    response = client.get(url, headers={"Accept": "application/xml"})
    response.raise_for_status()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    target.with_suffix(target.suffix + ".metadata.json").write_text(json.dumps({
        "url": str(response.url), "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(response.content).hexdigest(), "content_type": response.headers.get("content-type"),
        "notice": "Basado en datos de la Agencia Estatal Boletín Oficial del Estado. Texto consolidado meramente informativo." if "boe.es" in url else "Fuente: Instituto Nacional de Estadística. Inventario pendiente de revisión independiente."
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(0.3)


if __name__ == "__main__":
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        base = "https://www.boe.es/datosabiertos/api/legislacion-consolidada"
        capture(client, base + "?limit=10&offset=0", ROOT / "tests/fixtures/boe/discovery.xml")
        for identifier in ("BOE-A-1978-31229", "BOE-A-2015-11430", "BOE-A-1994-26003"):
            capture(client, base + "/id/" + identifier, ROOT / "tests/fixtures/boe" / (identifier + ".xml"))
        capture(client, "https://www.boe.es/legislacion/otros_diarios_oficiales.php", ROOT / "sources/snapshots/boe-directory.html")
        for filename in ("diccionario26.xlsx","cod_ccaa_provincia.htm","26codislas.xlsx","codmun_anual.htm"):
            capture(client, "https://www.ine.es/daco/daco42/codmun/" + filename, ROOT / "sources/snapshots" / filename)
    print("Official source fixtures captured; URLs, dates and hashes recorded.")
