#!/bin/bash
set -e

if ! command -v pip3 &> /dev/null; then
    if command -v dnf &> /dev/null; then
        dnf install -y python3-pip
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip
    else
        python3 -m ensurepip --upgrade
    fi
fi

pip3 install --quiet mapbox-vector-tile mercantile

cat > /tmp/indexar_do_cache.py << 'PYEOF'
"""
indexar_do_cache.py
====================
Le os tiles .pbf JA CACHEADOS em lotes_cache.sqlite3 (gerado pelo
warmup_lotes.py / lotes_terceiros_cache.py) e monta uma tabela de busca
rapida por quadra/lote, sem precisar bater no Route Planner de novo.

Cria uma NOVA tabela `lotes_busca` dentro do MESMO arquivo lotes_cache.sqlite3
(nao duplica os 168MB de tiles em outro arquivo).

USO:
    # 1. primeiro descobre o schema (nomes dos campos) com um tile que
    #    voce sabe que tem lote:
    python indexar_do_cache.py --inspecionar --cidade aparecida --z 17 --x 12345 --y 6789

    # 2. depois de ajustar LAYER_NAME e FIELD_* abaixo, roda a indexacao:
    python indexar_do_cache.py --indexar
"""
import argparse
import os
import sqlite3
from pathlib import Path

import mapbox_vector_tile
import mercantile

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data" if Path("/data").is_dir() else "."))
DB_PATH = DATA_DIR / "lotes_cache.sqlite3"

# ============================================================
# AJUSTE COM BASE NO QUE O --inspecionar mostrar
# ============================================================
LAYER_NAME = "lotes"          # nome da layer dentro do pbf
FIELD_BAIRRO = "bairro"
FIELD_QUADRA = "quadra"
FIELD_LOTE = "lote"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def inspecionar(cidade, z, x, y):
    conn = get_conn()
    row = conn.execute(
        "SELECT data FROM tiles WHERE cidade=? AND z=? AND x=? AND y=?",
        (cidade, z, x, y),
    ).fetchone()
    conn.close()

    if row is None:
        print(f"Tile {cidade}/{z}/{x}/{y} nao esta no cache. "
              f"Rode o warmup_lotes.py pra essa cidade primeiro, ou "
              f"escolha outro z/x/y que voce sabe que tem lote.")
        return
    if row[0] is None:
        print(f"Tile {cidade}/{z}/{x}/{y} esta em cache mas e um TOMBSTONE "
              f"(area sem lote). Escolha outro tile.")
        return

    tile = mapbox_vector_tile.decode(row[0])
    print(f"Tile {cidade}/{z}/{x}/{y} - layers encontradas: {list(tile.keys())}")
    for layer_name, layer_data in tile.items():
        features = layer_data.get("features", [])
        print(f"  Layer '{layer_name}': {len(features)} features")
        if features:
            print(f"    Exemplo de properties: {features[0].get('properties')}")


def criar_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lotes_busca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cidade TEXT NOT NULL,
            bairro TEXT,
            quadra TEXT,
            lote TEXT,
            centroid_lat REAL,
            centroid_lon REAL,
            tile_z INTEGER,
            tile_x INTEGER,
            tile_y INTEGER
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unico_busca
        ON lotes_busca(cidade, bairro, quadra, lote)
    """)
    conn.commit()


def _frac_to_lnglat(tile_x, tile_y, tile_z, frac_x, frac_y):
    bounds = mercantile.bounds(tile_x, tile_y, tile_z)
    lon = bounds.west + frac_x * (bounds.east - bounds.west)
    lat = bounds.north - frac_y * (bounds.north - bounds.south)
    return lon, lat


def calcular_centroide(geometry_coords, extent, tile_x, tile_y, tile_z):
    pontos = []
    for anel in geometry_coords:
        for x_local, y_local in anel:
            frac_x = x_local / extent
            frac_y = y_local / extent
            lon, lat = _frac_to_lnglat(tile_x, tile_y, tile_z, frac_x, frac_y)
            pontos.append((lat, lon))
    if not pontos:
        return None, None
    return (sum(p[0] for p in pontos) / len(pontos),
            sum(p[1] for p in pontos) / len(pontos))


def indexar():
    conn = get_conn()
    criar_schema(conn)

    rows = conn.execute(
        "SELECT cidade, z, x, y, data FROM tiles WHERE data IS NOT NULL"
    ).fetchall()
    print(f"{len(rows)} tiles com dado no cache para decodificar")

    total_lotes = 0
    for i, (cidade, z, x, y, data) in enumerate(rows):
        try:
            tile = mapbox_vector_tile.decode(data)
        except Exception as e:
            print(f"  erro ao decodificar {cidade}/{z}/{x}/{y}: {e}")
            continue

        layer = tile.get(LAYER_NAME)
        if not layer:
            continue

        extent = layer.get("extent", 4096)
        for feature in layer.get("features", []):
            props = feature.get("properties", {})
            bairro = props.get(FIELD_BAIRRO)
            quadra = props.get(FIELD_QUADRA)
            lote = props.get(FIELD_LOTE)

            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [])
            lat, lon = calcular_centroide(coords, extent, x, y, z)

            cur = conn.execute("""
                INSERT OR IGNORE INTO lotes_busca
                    (cidade, bairro, quadra, lote, centroid_lat, centroid_lon,
                     tile_z, tile_x, tile_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cidade, bairro, quadra, lote, lat, lon, z, x, y))
            if cur.rowcount:
                total_lotes += 1

        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  ... {i + 1}/{len(rows)} tiles, {total_lotes} lotes indexados ate agora")

    conn.commit()
    conn.close()
    print(f"\nConcluido: {total_lotes} lotes indexados em lotes_busca "
          f"(dentro de {DB_PATH})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspecionar", action="store_true")
    ap.add_argument("--indexar", action="store_true")
    ap.add_argument("--cidade", choices=["aparecida", "canedo", "goiania"])
    ap.add_argument("--z", type=int)
    ap.add_argument("--x", type=int)
    ap.add_argument("--y", type=int)
    args = ap.parse_args()

    if args.inspecionar:
        if not all([args.cidade, args.z is not None, args.x is not None, args.y is not None]):
            print("Use: --inspecionar --cidade aparecida --z 17 --x 12345 --y 6789")
            return
        inspecionar(args.cidade, args.z, args.x, args.y)
    elif args.indexar:
        indexar()
    else:
        print("Use --inspecionar ou --indexar. Veja --help.")


if __name__ == "__main__":
    main()

PYEOF

python3 /tmp/indexar_do_cache.py --inspecionar --cidade aparecida --z 17 --x 12345 --y 6789