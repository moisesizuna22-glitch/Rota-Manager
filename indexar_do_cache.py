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
    r"Q[A-Za-z]*\.?\s*([0-9]+[A-Za-z]?)\s*[-,/]?\s*L[A-Za-z]*\.?\s*([0-9]+[A-Za-z]?)",
    re.IGNORECASE,
)


def _normalizar_num_busca(v):
    """Tira zero à esquerda de valores numéricos ('09' -> '9') pra bater
    com o jeito que o usuário digita na busca. Mantém sufixo de letra
    (ex: '3A') em maiúsculo."""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    return str(int(v)) if v.isdigit() else v.upper()


def _extrair_quadra_lote(sup):
    if not sup:
        return None, None
    m = _PADRAO_QUADRA_LOTE.search(sup)
    if not m:
        return None, None
    return _normalizar_num_busca(m.group(1)), _normalizar_num_busca(m.group(2))


def _extrair_campos(props):
    """Extrai (quadra, lote, bairro, via, busca_end) das properties de um
    feature, adaptando ao formato usado por cada layer/cidade.

    - Aparecida (e Canedo, aparentemente igual): tudo embutido no campo
      'sup', tipo "Q 26, LT 43". Bairro em 'nsvia', rua em 'via',
      endereço formatado pronto em 'BuscaEnd'.
    - Goiânia: layer 'lotes_goiania' já vem com quadra/lote separados em
      'nm_qdr'/'nm_lot' — não tem 'sup'. Não tem bairro/via/busca_end
      prontos nesse layer (descoberto via --inspecionar); usa 'LABEL'
      como texto de referência quando não tem BuscaEnd.
    """
    if props.get("nm_qdr") is not None or props.get("nm_lot") is not None:
        quadra = _normalizar_num_busca(props.get("nm_qdr"))
        lote = _normalizar_num_busca(props.get("nm_lot"))
        bairro = props.get("nsvia") or props.get("bairro")
        via = props.get("via") or props.get("nm_via")
        busca_end = props.get("BuscaEnd") or props.get("LABEL")
        return quadra, lote, bairro, via, busca_end

    quadra, lote = _extrair_quadra_lote(props.get("sup"))
    bairro = props.get("nsvia")
    via = props.get("via")
    busca_end = props.get("BuscaEnd")
    return quadra, lote, bairro, via, busca_end


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


def _achatar_pontos(geometry_coords):
    """Percorre a geometria (Polygon, MultiPolygon, ou qualquer nível de
    aninhamento) e devolve uma lista de (x, y) — ignora dimensões extras
    (ex: z) e não assume uma profundidade fixa de listas."""
    pontos = []

    def _percorrer(nivel):
        if not nivel:
            return
        primeiro = nivel[0]
        # Se o primeiro elemento é um número, "nivel" já é um ponto tipo
        # [x, y] ou [x, y, z] — usa só os dois primeiros valores.
        if isinstance(primeiro, (int, float)):
            pontos.append((nivel[0], nivel[1]))
            return
        # Senão, "nivel" é uma lista de sub-listas — desce mais um nível.
        for sub in nivel:
            _percorrer(sub)

    _percorrer(geometry_coords)
    return pontos


def _profundidade(v):
    """Quantos níveis de lista até chegar num número (ponto). Polygon tem
    profundidade 3 ([[[x,y],...]]), MultiPolygon tem profundidade 4."""
    d = 0
    while isinstance(v, list) and v:
        v = v[0]
        d += 1
    return d


def _centroide_anel(anel):
    """Centróide de um anel (lista de pontos [x,y] ou [x,y,z]) via fórmula
    do polígono (shoelace) — área-ponderado, ao contrário da média simples
    de vértices, sempre representa o 'centro de massa' real da forma, sem
    o risco de cair fora do polígono em formatos côncavos/em L/esquina.
    Retorna (cx, cy, area_absoluta)."""
    n = len(anel)
    if n < 3:
        xs = [p[0] for p in anel]
        ys = [p[1] for p in anel]
        return sum(xs) / len(xs), sum(ys) / len(ys), 0.0

    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = anel[i][0], anel[i][1]
        x1, y1 = anel[(i + 1) % n][0], anel[(i + 1) % n][1]
        cruz = x0 * y1 - x1 * y0
        area2 += cruz
        cx += (x0 + x1) * cruz
        cy += (y0 + y1) * cruz

    area = area2 / 2.0
    if abs(area) < 1e-9:
        # polígono degenerado (área ~0, ex: linha reta) — cai pra média simples
        xs = [p[0] for p in anel]
        ys = [p[1] for p in anel]
        return sum(xs) / len(xs), sum(ys) / len(ys), 0.0

    return cx / (6 * area), cy / (6 * area), abs(area)


def _centroide_local(geometry_coords):
    """Acha o centróide local (coordenadas de pixel do tile, antes de
    converter pra lat/lon) de uma geometria Polygon ou MultiPolygon.
    Usa sempre o ANEL EXTERNO (contorno) de cada polígono — em
    MultiPolygon, escolhe o polígono de maior área (o lote principal,
    ignorando fragmentos pequenos de corte na borda do tile)."""
    if not geometry_coords:
        return None

    prof = _profundidade(geometry_coords)

    if prof == 3:
        poligonos = [geometry_coords]          # Polygon: um polígono só
    elif prof == 4:
        poligonos = geometry_coords             # MultiPolygon: vários
    else:
        poligonos = None

    if poligonos:
        melhor = None
        melhor_area = -1.0
        for poly in poligonos:
            if not poly or len(poly[0]) < 3:
                continue
            anel_externo = poly[0]  # primeiro anel = contorno externo
            cx, cy, area = _centroide_anel(anel_externo)
            if area > melhor_area:
                melhor_area = area
                melhor = (cx, cy)
        if melhor is not None:
            return melhor

    # Fallback (formato inesperado, ou nenhum anel válido) — média simples
    pontos = _achatar_pontos(geometry_coords)
    if not pontos:
        return None
    return (sum(p[0] for p in pontos) / len(pontos),
            sum(p[1] for p in pontos) / len(pontos))


def _frac_to_lnglat(tile_x, tile_y, tile_z, frac_x, frac_y):
    bounds = mercantile.bounds(tile_x, tile_y, tile_z)
    lon = bounds.west + frac_x * (bounds.east - bounds.west)
    lat = bounds.north - frac_y * (bounds.north - bounds.south)
    return lon, lat


def calcular_centroide(geometry_coords, extent, tile_x, tile_y, tile_z):
    centro_local = _centroide_local(geometry_coords)
    if centro_local is None:
        return None, None
    x_local, y_local = centro_local
    frac_x = x_local / extent
    frac_y = y_local / extent
    lon, lat = _frac_to_lnglat(tile_x, tile_y, tile_z, frac_x, frac_y)
    return lat, lon


def indexar():
    conn = get_conn()
    criar_schema(conn)

    # Limpa antes de reindexar: como agora normalizamos zero à esquerda
    # ('09' -> '9'), reindexar sem limpar deixaria conviver linha antiga
    # (não normalizada) e linha nova (normalizada) pra mesma quadra/lote,
    # já que o índice único não reconheceria elas como o mesmo registro.
    conn.execute("DELETE FROM lotes_busca")
    conn.commit()

    rows = conn.execute(
        "SELECT cidade, z, x, y, data FROM tiles WHERE data IS NOT NULL"
    ).fetchall()
    print(f"{len(rows)} tiles com dado no cache para decodificar")

    total_lotes = 0
    sem_match = 0
    erros_geometria = 0
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
            quadra, lote, bairro, via, busca_end = _extrair_campos(props)
            if quadra is None or lote is None:
                sem_match += 1
                # texto de referência pro exemplo: 'sup' no formato antigo,
                # ou o LABEL/props bruto no formato novo (Goiânia)
                ref = props.get("sup") or props.get("LABEL") or str(props)
                if ref and len(exemplos_sem_match) < 10 and ref not in exemplos_sem_match:
                    exemplos_sem_match.append(ref)
                continue

            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [])
            try:
                lat, lon = calcular_centroide(coords, extent, x, y, z)
            except Exception as e:
                erros_geometria += 1
                if erros_geometria <= 5:
                    print(f"  aviso: geometria inesperada em {cidade} Q{quadra} LT{lote} "
                          f"({type(e).__name__}: {e}) — gravado sem coordenada")
                lat, lon = None, None

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
                  f"({sem_match} sem match no padrao Q/LT, {erros_geometria} com erro de geometria)")
            if exemplos_sem_match:
                print(f"      exemplos sem match ate agora: {exemplos_sem_match[:3]}")

    conn.commit()
    conn.close()
    print(f"\nConcluido: {total_lotes} lotes indexados em lotes_busca "
          f"({sem_match} features sem match no padrao Q/LT, ignoradas; "
          f"{erros_geometria} com erro de geometria, gravadas sem coordenada)")
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
