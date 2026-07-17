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
import io
import os
import threading
from contextlib import redirect_stdout
import sqlite3
from pathlib import Path

import mapbox_vector_tile
import mercantile

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data" if Path("/data").is_dir() else "."))
DB_PATH = DATA_DIR / "lotes_cache.sqlite3"

# ============================================================
# SCHEMA REAL (descoberto via --inspecionar)
# ============================================================
# Cada cidade tem sua própria layer (ex: 'lotes_aparecida'), então
# detectamos a layer automaticamente em vez de fixar um nome.
#
# Os campos não vêm separados - vem tudo dentro de 'sup', tipo:
#   "Q 26, LT 43"  ->  quadra=26, lote=43
# 'nsvia' é o bairro/loteamento (ex: "JD Tropical").
# 'via' é o nome da rua.
import re

_PADRAO_QUADRA_LOTE = re.compile(
    r"Q\w*\.?\s*([^\s,]+)\s*,?\s*LT\w*\.?\s*([^\s,]+)", re.IGNORECASE
)


def _extrair_quadra_lote(sup):
    if not sup:
        return None, None
    m = _PADRAO_QUADRA_LOTE.search(sup)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


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


def diagnostico():
    print(f"DATA_DIR resolvido para: {DATA_DIR.resolve()}")
    print(f"DATA_DIR existe? {DATA_DIR.is_dir()}")
    print(f"DB_PATH esperado: {DB_PATH.resolve()}")
    print(f"DB_PATH existe? {DB_PATH.exists()}")
    if DB_PATH.exists():
        print(f"Tamanho do arquivo: {DB_PATH.stat().st_size} bytes "
              f"({DB_PATH.stat().st_size / (1024*1024):.1f} MB)")

    print("\nConteúdo de DATA_DIR:")
    if DATA_DIR.is_dir():
        for item in sorted(DATA_DIR.iterdir()):
            tamanho = item.stat().st_size if item.is_file() else "-"
            print(f"  {item.name}  ({tamanho} bytes)" if item.is_file() else f"  {item.name}/ (pasta)")
    else:
        print("  DATA_DIR não existe como diretório")

    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            tabelas = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            print(f"\nTabelas encontradas no banco: {[t[0] for t in tabelas]}")
            conn.close()
        except Exception as e:
            print(f"\nErro ao abrir o banco: {e}")


def listar(limite=10):
    conn = get_conn()
    cidades = conn.execute(
        "SELECT DISTINCT cidade FROM tiles"
    ).fetchall()

    if not cidades:
        print("O cache parece vazio - nenhuma cidade encontrada na tabela 'tiles'.")
        return

    for (cidade,) in cidades:
        linhas = conn.execute(
            "SELECT z, x, y, LENGTH(data) as tamanho FROM tiles "
            "WHERE cidade=? AND data IS NOT NULL "
            "ORDER BY tamanho DESC LIMIT ?",
            (cidade, limite),
        ).fetchall()
        total_com_dado = conn.execute(
            "SELECT COUNT(*) FROM tiles WHERE cidade=? AND data IS NOT NULL",
            (cidade,),
        ).fetchone()[0]
        total_vazio = conn.execute(
            "SELECT COUNT(*) FROM tiles WHERE cidade=? AND data IS NULL",
            (cidade,),
        ).fetchone()[0]

        print(f"\n=== {cidade} ({total_com_dado} tiles com dado, {total_vazio} vazios) ===")
        if not linhas:
            print("  nenhum tile com dado encontrado")
            continue
        for z, x, y, tamanho in linhas:
            print(f"  z={z} x={x} y={y}  ({tamanho} bytes)")

    conn.close()


_progresso = {"rodando": False, "log": "", "concluido": False, "erro": None}
_progresso_lock = threading.Lock()


def indexar_em_background():
    """Roda indexar() numa thread separada, guardando o log/progresso em
    memoria pra ser consultado via --status, evitando timeout de proxy em
    execucoes longas."""
    global _progresso
    with _progresso_lock:
        if _progresso["rodando"]:
            return False
        _progresso = {"rodando": True, "log": "", "concluido": False, "erro": None}

    def _run():
        global _progresso
        buffer_local = io.StringIO()

        class _Tee:
            def write(self, s):
                buffer_local.write(s)
                with _progresso_lock:
                    _progresso["log"] = buffer_local.getvalue()
            def flush(self):
                pass

        try:
            with redirect_stdout(_Tee()):
                indexar()
        except Exception as e:
            with _progresso_lock:
                _progresso["erro"] = f"{type(e).__name__}: {e}"
        finally:
            with _progresso_lock:
                _progresso["rodando"] = False
                _progresso["concluido"] = True

    threading.Thread(target=_run, daemon=True).start()
    return True


def obter_progresso():
    with _progresso_lock:
        return dict(_progresso)


def criar_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lotes_busca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cidade TEXT NOT NULL,
            bairro TEXT,
            quadra TEXT,
            lote TEXT,
            via TEXT,
            busca_end TEXT,
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
    sem_match = 0
    exemplos_sem_match = []
    for i, (cidade, z, x, y, data) in enumerate(rows):
        try:
            tile = mapbox_vector_tile.decode(data)
        except Exception as e:
            print(f"  erro ao decodificar {cidade}/{z}/{x}/{y}: {e}")
            continue

        # a layer tem nome diferente por cidade (ex: lotes_aparecida) -
        # pega a primeira (e geralmente única) layer do tile
        if not tile:
            continue
        layer_name = next(iter(tile.keys()))
        layer = tile[layer_name]

        extent = layer.get("extent", 4096)
        for feature in layer.get("features", []):
            props = feature.get("properties", {})
            sup = props.get("sup")
            quadra, lote = _extrair_quadra_lote(sup)
            if quadra is None:
                sem_match += 1
                if sup and len(exemplos_sem_match) < 10 and sup not in exemplos_sem_match:
                    exemplos_sem_match.append(sup)
                continue
            bairro = props.get("nsvia")
            via = props.get("via")
            busca_end = props.get("BuscaEnd")

            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [])
            lat, lon = calcular_centroide(coords, extent, x, y, z)

            cur = conn.execute("""
                INSERT OR IGNORE INTO lotes_busca
                    (cidade, bairro, quadra, lote, via, busca_end,
                     centroid_lat, centroid_lon, tile_z, tile_x, tile_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cidade, bairro, quadra, lote, via, busca_end,
                  lat, lon, z, x, y))
            if cur.rowcount:
                total_lotes += 1

        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  ... {i + 1}/{len(rows)} tiles, {total_lotes} lotes indexados ate agora "
                  f"({sem_match} sem match no padrao Q/LT)")
            if exemplos_sem_match:
                print(f"      exemplos sem match ate agora: {exemplos_sem_match[:3]}")

    conn.commit()
    conn.close()
    print(f"\nConcluido: {total_lotes} lotes indexados em lotes_busca "
          f"({sem_match} features sem match no padrao Q/LT, ignoradas)")
    if exemplos_sem_match:
        print("\nExemplos de 'sup' que NAO bateram no padrao (pra ajustar o regex):")
        for ex in exemplos_sem_match:
            print(f"  {ex!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspecionar", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--indexar", action="store_true")
    ap.add_argument("--cidade", choices=["aparecida", "canedo", "goiania"])
    ap.add_argument("--z", type=int)
    ap.add_argument("--x", type=int)
    ap.add_argument("--y", type=int)
    args = ap.parse_args()

    if args.listar:
        listar()
    elif args.inspecionar:
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
