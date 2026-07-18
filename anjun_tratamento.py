"""
anjun_tratamento.py
====================
Fluxo PARALELO ao pipeline principal (rota.xlsx -> tratamento_dados.py),
feito sob medida pro CSV bruto do Anjun. Não mexe em tratamento_dados.py
nem no fluxo "Importar rota.xlsx" — só reaproveita a lógica de lá.

O problema que este script resolve
-----------------------------------
O campo "Address" do CSV do Anjun costuma vir assim:

    R 1013, SN, Goiânia, GO, (Rua 1013 Q33 L27)
    R 1029, Setor Pedro Ludovico, Goiânia, GO, (Rua 1029 108)
    Al Couto Magalhães, Goiânia, GO, (Alameda Couto Magalhães Solar
        Beberly Hills Apto 1204 Bloco A, 352, Solar Beverly Hills Apto 1204A)

Ou seja: o nome da rua aparece REPETIDO (uma vez no prefixo, outra vez
dentro dos parênteses) e o número/quadra-lote real às vezes vem sem
vírgula nenhuma separando do nome da rua ("Rua 1029 108") ou com "L"
sozinho no lugar de "LT" ("Q33 L27"). Passar esse texto direto pro
`standardize()` do tratamento_dados.py confunde a extração (ele acaba
lendo o próprio código da rua como se fosse o número, ou perdendo o
número por falta de vírgula).

Passo 1 (ANJUN) — feito aqui: pega o endereço bruto, tira a duplicação
entre prefixo/parênteses e devolve UMA linha limpa, já no formato que o
tratamento_dados.py sabe ler direito (rua + vírgula + número/quadra-lote).

Passo 2 (ATUAL) — feito reaproveitando tratamento_dados.py sem alterar
nada nele: `group_rows_p1` (agrupamento por semelhança) e depois
`consolidate_p2` + `write_excel_p2` (consolidação final), exatamente a
mesma lógica usada pelo fluxo "Importar rota.xlsx".

Uso:
    python anjun_tratamento.py entrada.csv saida.xlsx

Entrada esperada: CSV com colunas Address, City, State, Contact (mesmo
formato "delivery_list" que o csv_para_rota_xlsx.py já lê). Se o usuário
subir um .xlsx, o servidor converte pra CSV antes de chamar este script
(reaproveita o mesmo conversor usado pelo painel Anjun).
"""

import csv
import re
import sys
from pathlib import Path

import tratamento_dados as td

# ── Extração do endereço detalhado (mesma ideia do csv_para_rota_xlsx.py) ──

_RE_PARENTESES = re.compile(r"\((.*?)\)")

_RE_BAIRRO = re.compile(
    r'\bSetor\s+([A-ZÀ-Úa-zà-ú0-9 ]+?)(?:,|$)', re.IGNORECASE
)

# Rua com código logo após o prefixo: "Rua 1013", "R S 6", "Av C-160" etc.
_STREET_HEAD_RE = re.compile(
    r'^(RUA|R\.?|AVENIDA|AV\.?|PRA[CÇ]A|P[CÇ]\.?|ALAMEDA|AL\.?|TRAVESSA|TV\.?)'
    r'\s+(C[-\s]?\d+|T[-\s]?\d+|[A-Z]\s*\d+|\d+)',
    re.IGNORECASE,
)

# Quadra/Lote tolerante ao formato do Anjun, que às vezes usa só "L" no
# lugar de "LT" (ex.: "Q33 L27") e às vezes separa quadra e lote com
# pontuação/hífen em vez de espaço (ex.: "qd 137. lt 11"). O
# tratamento_dados.py original só reconhece "LT/LTE/LTS" com espaço puro
# entre os dois — por isso normalizamos aqui pra "QD .. LT .." antes de
# repassar pra lógica atual, sem precisar tocar nela.
_QDLT_RELAXADO_RE = re.compile(
    r'\bQD?\.?\s*(\d+[A-Z]?)[\.\-,\s]{0,3}L(?:T[ES]?)?\.?\s*(\d+)\b', re.IGNORECASE
)

# Quadra SOZINHA, sem lote (ex.: "qd 17"). O tratamento_dados.py não tem
# nenhum tratamento pra QD sem LT — sem isso, esses endereços ficavam sem
# nenhum número aproveitável.
_QD_SOZINHO_RE = re.compile(r'\bQD?\.?\s*(\d+[A-Z]?)\b', re.IGNORECASE)

_PREFIXO_RUA_RE = re.compile(
    r'^(RUA|R\.?|AVENIDA|AV\.?|PRA[CÇ]A|P[CÇ]\.?|ALAMEDA|AL\.?|TRAVESSA|TV\.?)\b',
    re.IGNORECASE,
)

# Onde termina o "nome da rua por extenso": no primeiro número solto ou na
# primeira palavra de prédio/complemento — evita engolir "Solar X",
# "Edifício Y" etc. como se fizessem parte do nome da rua.
_FIM_NOME_RUA_RE = re.compile(
    r'\b(\d+|SOLAR|RESIDENCIAL|RESID\.?|RES\.?|CONDOM[IÍ]NIO|COND\.?|'
    r'EDIF[IÍ]CIO|EDIFICIO|EDI\.?|ED\.?|EF\.?|VILLAGE|APTO?\.?|AP\.?|'
    r'BLOCO|BL\.?|TORRE|CASA|LOJA|SALA)\b',
    re.IGNORECASE,
)


def _numero_do_prefixo(address_bruto: str):
    """O campo Address do Anjun às vezes traz o número REAL da casa no
    prefixo, antes do parêntese (ex.: 'R 1035, 212, Goiânia, GO, ...').
    Quando o texto entre parênteses só tem apto/bloco/edifício e não tem
    número de casa próprio, esse '212' era descartado — aqui recuperamos
    ele como fallback. Só aceita se o 2º campo (logo após o nome/código da
    rua) for só dígitos; senão é cidade/bairro/outra coisa, não número."""
    prefixo = address_bruto.split('(', 1)[0]
    campos = [c.strip() for c in prefixo.split(',')]
    if len(campos) < 2:
        return None
    candidato = campos[1]
    if re.fullmatch(r'\d{1,6}', candidato):
        return candidato
    return None


def _limpar_rua_codificada(texto: str, numero_prefixo: str = None):
    """Ruas com código numérico logo após o prefixo (ex.: 'Rua 1013',
    'Rua S 6'). Devolve None se o prefixo não bater com esse padrão —
    nesse caso é rua por extenso, tratada em `_limpar_rua_por_extenso`.

    `numero_prefixo`: número de casa vindo do prefixo do Address (fora dos
    parênteses) — usado quando o texto entre parênteses não tem número
    próprio (só apto/bloco/edifício)."""
    m_head = _STREET_HEAD_RE.match(texto)
    if not m_head:
        return None

    cabecalho = texto[:m_head.end()]
    resto = texto[m_head.end():].strip().lstrip(',').strip()
    if not resto:
        return f"{cabecalho}, {numero_prefixo}" if numero_prefixo else cabecalho

    m_qdlt = _QDLT_RELAXADO_RE.search(resto)
    if m_qdlt:
        return f"{cabecalho}, QD {m_qdlt.group(1)} LT {m_qdlt.group(2)}"

    m_qd_so = _QD_SOZINHO_RE.match(resto)
    if m_qd_so:
        return f"{cabecalho}, {m_qd_so.group(1)}"

    m_num = re.match(r'^(\d+)\b', resto)
    if m_num:
        return f"{cabecalho}, {m_num.group(1)}"

    # sobrou só ruído (prédio, apto etc.) — se tiver número real vindo do
    # prefixo do Address, usa ele; senão mantém o ruído junto pro BLDG_RE
    # do tratamento_dados.py reconhecer nome de edifício/residencial/condomínio
    if numero_prefixo:
        return f"{cabecalho}, {numero_prefixo}, {resto}"
    return f"{cabecalho}, {resto}"


def _limpar_rua_por_extenso(texto: str, numero_prefixo: str = None) -> str:
    """Ruas sem código numérico (ex.: 'Alameda Couto Magalhães', 'Avenida
    Segunda Radial'). Acha o número real do imóvel entre os campos
    separados por vírgula, ignorando complementos com dígito (apto/bloco).

    Ordem de prioridade: QD+LT em qualquer lugar do texto > QD sozinho
    (sem lote) > número solto após o nome da rua > número vindo do
    prefixo do Address > deixa o ruído (apto/edifício) pro BLDG_RE do
    tratamento_dados.py."""
    m_pfx = _PREFIXO_RUA_RE.match(texto)
    prefixo = texto[:m_pfx.end()] if m_pfx else ''
    resto_completo = texto[m_pfx.end():].strip() if m_pfx else texto

    # Prioridade 1: QD + LT em qualquer lugar do resto (tolera pontuação/
    # hífen entre os dois, ex.: "qd 137. lt 11" ou "- qd 137")
    m_qdlt = _QDLT_RELAXADO_RE.search(resto_completo)
    if m_qdlt:
        nome_rua = resto_completo[:m_qdlt.start()].rstrip(', -').strip()
        if not nome_rua:
            nome_rua = resto_completo.split(',')[0].strip()
        return f"{prefixo} {nome_rua}, QD {m_qdlt.group(1)} LT {m_qdlt.group(2)}".strip()

    # Prioridade 2: QD sozinha, sem lote (ex.: "qd 17")
    m_qd_so = _QD_SOZINHO_RE.search(resto_completo)
    if m_qd_so:
        nome_rua = resto_completo[:m_qd_so.start()].rstrip(', -').strip()
        if not nome_rua:
            nome_rua = resto_completo.split(',')[0].strip()
        return f"{prefixo} {nome_rua}, {m_qd_so.group(1)}".strip()

    # Prioridade 3: número solto ou nome de prédio/complemento
    m_fim = _FIM_NOME_RUA_RE.search(resto_completo)
    if m_fim:
        nome_rua = resto_completo[:m_fim.start()].rstrip(', ').strip()
        cauda = resto_completo[m_fim.start():].strip()
    else:
        nome_rua = resto_completo.rstrip(', ').strip()
        cauda = ''

    if not nome_rua:
        nome_rua = resto_completo.split(',')[0].strip()

    if not cauda:
        if numero_prefixo:
            return f"{prefixo} {nome_rua}, {numero_prefixo}".strip()
        return f"{prefixo} {nome_rua}".strip()

    campos_cauda = [c.strip() for c in cauda.split(',') if c.strip()]
    numero = next((c for c in campos_cauda if re.fullmatch(r'\d+', c)), None)
    if numero:
        return f"{prefixo} {nome_rua}, {numero}".strip()

    if numero_prefixo:
        return f"{prefixo} {nome_rua}, {numero_prefixo}, {cauda}".strip()
    return f"{prefixo} {nome_rua}, {cauda}".strip()


def normalizar_detalhe_anjun(detalhe: str, numero_prefixo: str = None) -> str:
    """Recebe só o trecho de endereço (sem cidade/UF/CEP) e devolve uma
    versão limpa, pronta pro `standardize()` do tratamento_dados.py."""
    if not detalhe or not detalhe.strip():
        return detalhe or ''
    texto = detalhe.strip()
    codificada = _limpar_rua_codificada(texto, numero_prefixo)
    if codificada is not None:
        return codificada
    return _limpar_rua_por_extenso(texto, numero_prefixo)


def extrair_endereco_anjun(address_bruto: str) -> str:
    """Tira a duplicação entre o prefixo do campo Address (rua, número,
    cidade, UF) e o texto detalhado entre parênteses: usa o detalhado
    (mais completo) quando existe; senão usa o próprio prefixo.

    Quando existe parêntese, também tenta recuperar o número de casa real
    que às vezes só aparece no prefixo (fora do parêntese) — ver
    `_numero_do_prefixo`."""
    if not address_bruto or not address_bruto.strip():
        return ''
    m = _RE_PARENTESES.search(address_bruto)
    tem_parenteses = bool(m and m.group(1).strip())
    detalhe = m.group(1).strip() if tem_parenteses else address_bruto.strip()
    numero_prefixo = _numero_do_prefixo(address_bruto) if tem_parenteses else None
    return normalizar_detalhe_anjun(detalhe, numero_prefixo)


def extrair_bairro_anjun(address_bruto: str) -> str:
    m = _RE_BAIRRO.search(address_bruto or '')
    return m.group(1).strip() if m else ''


# ── Passo 1 (Anjun) + Passo 2 (lógica atual, reaproveitada) ──

def _ler_csv_anjun(caminho_csv: Path) -> list:
    with open(caminho_csv, encoding='utf-8-sig', newline='') as f:
        leitor = csv.DictReader(f)
        return list(leitor)


def _linhas_para_passo1(linhas_csv: list) -> list:
    rows = []
    for i, linha in enumerate(linhas_csv, start=1):
        address_bruto = (linha.get('Address') or linha.get('address') or '').strip()
        contato = (linha.get('Contact') or linha.get('contato') or '').strip()
        endereco_limpo = extrair_endereco_anjun(address_bruto)
        bairro = extrair_bairro_anjun(address_bruto)
        rows.append({
            'raw_row': [],
            'stop': str(i),
            'address': endereco_limpo,
            'coord': '',
            # campos extras (o group_rows_p1 do tratamento_dados.py só lê
            # 'address'/'stop' e acrescenta as chaves group_*, então esses
            # campos passam intactos pro passo 2 abaixo)
            '_original': address_bruto,
            '_contato': contato,
            '_bairro': bairro,
        })
    return rows


def _passo1_para_passo2(rows_agrupados: list) -> list:
    saida = []
    for r in rows_agrupados:
        saida.append({
            'reformado': r.get('group_label', '') or r.get('address', ''),
            'original': r.get('_original', ''),
            'bairro': r.get('_bairro', ''),
            'seq': r.get('stop', ''),
            'stop': r.get('stop', ''),
            'coord': r.get('coord', ''),
            'zip': '',
            'lat': '',
            'lon': '',
            'contato': r.get('_contato', ''),
        })
    return saida


def processar_anjun(caminho_csv: str, caminho_saida: str) -> str:
    caminho_csv = Path(caminho_csv)
    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_csv}")

    linhas_csv = _ler_csv_anjun(caminho_csv)
    if not linhas_csv:
        raise ValueError("CSV vazio.")

    print(f"Lendo: {caminho_csv} ({len(linhas_csv)} linha(s))")

    print("Fazendo o tratamento Anjun (limpando/deduplicando endereços)...")
    rows_p1 = _linhas_para_passo1(linhas_csv)

    print("Agrupando (mesma lógica do tratamento_dados.py)...")
    rows_p1 = td.group_rows_p1(rows_p1)

    print("Consolidando...")
    rows_p2 = _passo1_para_passo2(rows_p1)
    groups = td.consolidate_p2(rows_p2)

    caminho_saida = Path(caminho_saida)
    print(f"Salvando: {caminho_saida}")
    td.write_excel_p2(groups, str(caminho_saida))

    print(f"✅ {len(linhas_csv)} linha(s) -> {len(groups)} endereço(s) único(s) "
          f"| {sum(1 for g in groups if g['count'] > 1)} com duplicatas")

    return str(caminho_saida)


def main():
    if len(sys.argv) < 3:
        print("Uso: python anjun_tratamento.py entrada.csv saida.xlsx")
        sys.exit(1)
    processar_anjun(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
