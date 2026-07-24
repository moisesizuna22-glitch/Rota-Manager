"""
Extrator automatico de enderecos + coordenadas - Anjun Express

Pipeline:
  1. Login (usuario/senha) -> token JWT
  2. Lista as tarefas de despacho em aberto (dispatchTask)
  3. Para cada tarefa, pega a lista de encomendas (waybills) com endereco em texto
  4. Geocodifica cada endereco (lat/lng) via API oficial do Anjun
  5. Salva tudo num CSV e num JSON, prontos pra importar no Rota Manager

Uso:
  python anjun_extrator.py
"""

import hashlib
import json
import csv
import re
import time
import sys
from datetime import datetime

import requests
from openpyxl import Workbook

from anjun_tratamento import extrair_endereco_anjun

_RE_QD_ABREV = re.compile(r'\bQD\b', re.IGNORECASE)
_RE_LT_ABREV = re.compile(r'\bLT\b', re.IGNORECASE)


def _expandir_qd_lt(endereco: str) -> str:
    """Pos-processa a saida de extrair_endereco_anjun() trocando as
    abreviacoes 'QD'/'LT' por extenso, sem mexer no resto do texto."""
    endereco = _RE_QD_ABREV.sub('Quadra', endereco)
    endereco = _RE_LT_ABREV.sub('Lote', endereco)
    return endereco

# ============================================================
# CONFIGURACAO - preenche com seu usuario e senha do Anjun
# ============================================================
USERNAME = "02030332135"      # ex: "02030332135"
PASSWORD = "smart1234"        # senha normal, sem hash - o script faz o MD5 sozinho

# Hosts observados na captura de trafego (mesma infra, subdominios diferentes)
HOST_AUTH = "https://newmanage.anjunexpress.com"      # login, lista de tarefas
HOST_CLIENT = "https://client.supplier.anjunexpress.com"  # waybills, geocodificacao

# Delay entre chamadas de geocodificacao, pra nao sobrecarregar o servidor
GEOCODE_DELAY_SECONDS = 0.3

OUTPUT_JSON = "anjun_entregas.json"
OUTPUT_CSV = "anjun_entregas.csv"
OUTPUT_XLSX = "anjun_entregas_rota.xlsx"  # esse e o que voce importa no Rota Manager


def headers_base(token=None):
    """Monta os headers padrao usados pela API. O header 'token' so entra depois do login."""
    h = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 17; sdk_gphone16k_x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.7827.5 Mobile Safari/537.36 uni-app-x/4.76"
        ),
        "system": "h5",
        "content-type": "application/json",
        "Accept-Language": "pu",
    }
    if token:
        h["token"] = token
    return h


def login(username: str, password: str) -> str:
    """Faz login e devolve o token JWT.

    O app faz MD5 DUPLO da senha: primeiro MD5 da senha em si, depois MD5
    de novo em cima do hash resultante (como texto hexadecimal).
    """
    primeiro_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    senha_md5 = hashlib.md5(primeiro_hash.encode("utf-8")).hexdigest()
    url = f"{HOST_AUTH}/user/pm/account/pda/login"
    body = {"username": username, "password": senha_md5}

    resp = requests.post(url, headers=headers_base(), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"Login falhou: {data.get('msg') or data}")

    token = data["data"]["token"]
    print(f"[login] OK - token obtido (expira em ~5 dias)")
    return token


def listar_tarefas(token: str) -> list:
    """Lista as tarefas de despacho em aberto (completeState=0)."""
    url = f"{HOST_AUTH}/api/wms/console/v1/dispatch/queryTaskListNew"
    body = {"pageNumber": 1, "pageSize": 50, "params": {"completeState": 0, "dispatchTaskId": None}}

    resp = requests.post(url, headers=headers_base(token), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"Erro ao listar tarefas: {data.get('msg') or data}")

    tarefas = data["data"]["records"]
    print(f"[tarefas] {len(tarefas)} tarefa(s) em aberto encontrada(s)")
    return tarefas


def listar_waybills(token: str, task_id: int) -> list:
    """Pega a lista de encomendas (com endereco em texto, sem coordenada) de uma tarefa."""
    url = f"{HOST_CLIENT}/api/wms/console/v1/dispatch/queryWaybillInfoNew"
    params = {"taskId": task_id}

    resp = requests.get(url, headers=headers_base(token), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"Erro ao listar waybills da tarefa {task_id}: {data.get('msg') or data}")

    waybills = data["data"].get("deliveryList") or []
    print(f"  [waybills] tarefa {task_id}: {len(waybills)} encomenda(s)")
    return waybills


def geocodificar(token: str, waybill: dict) -> dict:
    """Manda um endereco pra geocodificacao e devolve lat/lng + endereco formatado.

    Observacao: a API aceita uma lista (addressList) com varios enderecos por
    chamada. Na captura de trafego o app manda um por vez, mas isso pode ser
    so um jeito de implementar do front-end - se quiser tentar mandar varios
    juntos pra reduzir o numero de chamadas, e so agrupar antes de chamar essa
    funcao. Deixei um por vez aqui pra reproduzir exatamente o que foi observado
    e reduzir risco de erro inesperado do servidor.
    """
    url = f"{HOST_CLIENT}/api/address/v1/address/v1/info"
    body = {
        "addressList": [
            {
                "address": waybill.get("receiveAddress"),
                "area": waybill.get("area"),
                "city": waybill.get("city"),
                "waybillNumber": waybill.get("waybillNumber"),
                "state": waybill.get("state"),
                "zipCode": waybill.get("receiveZipcode"),
            }
        ]
    }

    resp = requests.post(url, headers=headers_base(token), json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200 or not data.get("data"):
        print(f"    [!] geocodificacao falhou pra {waybill.get('waybillNumber')}: {data.get('msg') or data}")
        return {}

    return data["data"][0]


def salvar_xlsx_rota(resultado: list, caminho: str):
    """Gera um .xlsx no formato que o Rota Manager reconhece na importacao
    (mesma logica de deteccao de colunas da funcao ler_processado() do
    servidor.py - ele usa regex nos nomes das colunas, entao os nomes
    abaixo nao precisam ser identicos a outro arquivo, so bater no padrao).

    Como o endereco ja vem geocodificado oficialmente pelo proprio Anjun,
    esse xlsx pula a etapa de "tratamento" (dedupe/limpeza de OCR) e ja
    sai pronto pra importar direto no fluxo principal do Rota Manager.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "rota"

    colunas = [
        "Sequencia", "Endereco_Original", "Endereco_Normalizado", "Endereco_Reformado",
        "Latitude", "Longitude", "Coordenadas",
        "Bairro", "CEP", "Telefone", "Nome", "Numero_Rastreio",
        "Rotas_Iguais",
    ]
    ws.append(colunas)

    for i, item in enumerate(resultado, start=1):
        lat = item.get("lat") or ""
        lng = item.get("lng") or ""
        coord = f"{lat},{lng}" if lat and lng else ""
        ws.append([
            i,
            item.get("enderecoOriginal") or "",
            item.get("enderecoNormalizado") or "",
            item.get("enderecoFormatado") or item.get("enderecoOriginal") or "",
            lat,
            lng,
            coord,
            item.get("area") or "",
            item.get("zipCode") or "",
            item.get("receiveMobile") or "",
            item.get("receiveName") or "",
            item.get("waybillNumber") or "",
            1,
        ])

    wb.save(caminho)
    print(f"[ok] tambem salvo em {caminho} (pronto pra importar no Rota Manager)")


def main():
    if USERNAME == "SEU_USUARIO_AQUI" or PASSWORD == "SUA_SENHA_AQUI":
        print("Edita o script primeiro e preenche USERNAME e PASSWORD no topo do arquivo.")
        sys.exit(1)

    token = login(USERNAME, PASSWORD)
    tarefas = listar_tarefas(token)

    resultado = []

    for tarefa in tarefas:
        task_id = tarefa["taskId"]
        dispatch_number = tarefa.get("dispatchTaskNumber")
        waybills = listar_waybills(token, task_id)

        for wb in waybills:
            geo = geocodificar(token, wb)
            time.sleep(GEOCODE_DELAY_SECONDS)

            resultado.append({
                "dispatchTaskNumber": dispatch_number,
                "taskId": task_id,
                "waybillNumber": wb.get("waybillNumber"),
                "scanOrderNumber": wb.get("scanOrderNumber"),
                "receiveName": wb.get("receiveName"),
                "receiveMobile": wb.get("receiveMobile"),
                "enderecoOriginal": wb.get("receiveAddress"),
                "enderecoNormalizado": _expandir_qd_lt(extrair_endereco_anjun(wb.get("receiveAddress") or "")),
                "area": wb.get("area"),
                "city": wb.get("city"),
                "state": wb.get("state"),
                "zipCode": wb.get("receiveZipcode"),
                "enderecoFormatado": geo.get("formattedAddress"),
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
            })

    # --- salva JSON ---
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] {len(resultado)} entregas salvas em {OUTPUT_JSON}")

    # --- salva CSV ---
    if resultado:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(resultado[0].keys()))
            writer.writeheader()
            writer.writerows(resultado)
        print(f"[ok] tambem salvo em {OUTPUT_CSV} (abre direto no Excel)")

    # --- salva XLSX no formato do Rota Manager ---
    if resultado:
        salvar_xlsx_rota(resultado, OUTPUT_XLSX)


if __name__ == "__main__":
    print(f"=== Extrator Anjun - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    main()
