"""
Extrator automatico de enderecos + coordenadas - iMile Redelivery

Pipeline:
  1. Login (RSA na senha) -> access_token
  2. handleDeviceInfoAfterLogin (registra o dispositivo pra sessao)
  3. queryDeliveryListV3, paginado, ate acabar
  4. A resposta ja vem com endereco formatado (consigneeAddressToGoogle) e
     coordenadas (latitude/longitude) prontos - NAO precisa geocodificar.
  5. Salva em .json, .csv e .xlsx (formato compativel com o Rota Manager)

Toda a assinatura (header "sign") e o login (RSA) foram reconstruidos via
engenharia reversa do libapp.so (Flutter/Dart AOT) usando Blutter + Frida,
e verificados byte a byte contra chamadas reais do app - inclusive um
sign real, com status 200, que foi decifrado e bateu 100% com o calculado.

Dependencias: pip install requests pycryptodome openpyxl
"""

import base64
import hashlib
import json
import os
import time
import uuid

import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from openpyxl import Workbook

# ---------------------------------------------------------------------------
# CONFIGURACAO - preenche com seu usuario/senha antes de rodar, OU exporta as
# variaveis de ambiente IMILE_USERNAME/IMILE_PASSWORD (usado pelo servidor.py
# quando roda esse script por conta de outro usuario, sem editar o arquivo).
# ---------------------------------------------------------------------------

USERNAME = os.environ.get("IMILE_USERNAME") or "D21043608701"
PASSWORD = os.environ.get("IMILE_PASSWORD") or "Smart12@"

OUTPUT_JSON = os.environ.get("IMILE_OUTPUT_JSON") or "imile_entregas.json"
OUTPUT_CSV = os.environ.get("IMILE_OUTPUT_CSV") or "imile_entregas.csv"
OUTPUT_XLSX = os.environ.get("IMILE_OUTPUT_XLSX") or "imile_entregas_rota.xlsx"

# ---------------------------------------------------------------------------
# Constantes confirmadas via engenharia reversa / captura real do app
# ---------------------------------------------------------------------------

AES_KEY_B64 = "wmy5XydVAvmu+poHSErDBC9DlB+W3iuBzgIOADczYcw="
AES_KEY = base64.b64decode(AES_KEY_B64)

APP_VERSION = "2.2.90"
BASE_URL = "https://driverapp.imile.com"
DEVICE_ID = "92f6c5d8ebfb45e4"

# Credencial fixa do "cliente" OAuth2 (Basic Auth), usada so no login.
# "authorization: Basic bmV3REE6bmV3REE=" -> base64("newDA:newDA")
CLIENT_BASIC_AUTH = "Basic bmV3REE6bmV3REE="

# Chave publica RSA extraida direto do libapp.so (1024 bits).
RSA_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCrTwxoTL1REQ1vJgrXqVpbG+Ed
NF+JFvQ/SLSO4MARMnPUXMx320oGklKEchR+JLcuxfIbRariYZAv7M+uhUcEatKh
oYhA14zbshMpeEydpv2OFuPIz9t27miis0Qu2/WrZWj2GzZFi0tOdFvUeGT6aztJ
womra8WRl925BN5+vwIDAQAB
-----END PUBLIC KEY-----"""

_rsa_key = RSA.import_key(RSA_PUBLIC_KEY_PEM)
_rsa_cipher = PKCS1_v1_5.new(_rsa_key)


# ---------------------------------------------------------------------------
# Criptografia
# ---------------------------------------------------------------------------

def encrypt_password(senha: str) -> str:
    """RSA (PKCS1v1.5) + base64 - igual o Tool.encrypt() do app."""
    ciphertext = _rsa_cipher.encrypt(senha.encode())
    return base64.b64encode(ciphertext).decode()


def gerar_sign(timestamp_ms: int, device_id: str, token: str, request_uuid: str,
               app_version: str = APP_VERSION) -> str:
    """Gera o header 'sign' (AES-256-GCM) exatamente como o app faz.

    O terceiro campo da mensagem e o access_token da sessao atual (nao um
    "persistentId" fixo do dispositivo) - confirmado decifrando um sign
    real, capturado com status 200."""
    short_msg = f"{timestamp_ms}-{token}-{request_uuid}"
    long_msg = f"{timestamp_ms}-{app_version}-{device_id}-{token}-{request_uuid}"

    iv = hashlib.sha256(short_msg.encode()).digest()[:12]
    cipher = AES.new(AES_KEY, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(long_msg.encode())

    return base64.b64encode(iv + ciphertext + tag).decode()


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

def _headers_base() -> dict:
    return {
        "appcode": "com.imile.redelivery",
        "user-agent": "Dart/3.6 (dart:io)",
        "deviceid": DEVICE_ID,
        "appversion": APP_VERSION,
        "accept-encoding": "gzip",
        "model": "sdk_gphone64_x86_64",
        "locale": "en_US",
        "enablemultilogin": "true",
        "platform": "android",
        "timezone": "GMT",
        "lang": "en_US",
        "accept": "application/json",
        "sysversion": "34",
        "client": "REDeliveryApp",
        "changezonelanguage": "1",
    }


def montar_headers_autenticados(token: str) -> dict:
    timestamp_ms = int(time.time() * 1000)
    request_uuid = str(uuid.uuid4())
    sign = gerar_sign(timestamp_ms, DEVICE_ID, token, request_uuid)

    headers = _headers_base()
    headers.update({
        "requesttimemillis": str(timestamp_ms),
        "requestuuid": request_uuid,
        "authorization": f"Bearer {token}",
        "sign": sign,
        "content-type": "application/json",
    })
    return headers


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login(usuario: str, senha: str) -> dict:
    url = f"{BASE_URL}/ucenter/imile/login"
    timestamp_ms = int(time.time() * 1000)
    request_uuid = str(uuid.uuid4())

    params = {
        "userCode": usuario,
        "password": encrypt_password(senha),
        "lang": "en_US",
        "timeZone": "Asia/Shanghai",
    }
    headers = _headers_base()
    headers.update({
        "requesttimemillis": str(timestamp_ms),
        "requestuuid": request_uuid,
        "authorization": CLIENT_BASIC_AUTH,
        "sign": "",
    })

    resp = requests.post(url, params=params, headers=headers, timeout=15)
    data = resp.json()
    resp.raise_for_status()
    if data.get("status") != "success":
        raise RuntimeError(f"Login falhou: {data.get('message')}")
    return data


def obter_token(usuario: str, senha: str) -> str:
    data = login(usuario, senha)
    return data["resultObject"]["access_token"]


def handle_device_info_after_login(token: str, usuario: str) -> dict:
    url = f"{BASE_URL}/lm/express/driver/v1/driver/device/handleDeviceInfoAfterLogin"
    headers = montar_headers_autenticados(token)
    body = {
        "driverCode": usuario,
        "deviceId": DEVICE_ID,
        "deviceName": "",
        "deviceModelName": "sdk_gphone64_x86_64",
        "deviceSystemVersion": "14",
        "currentLongitude": 0.0,
        "currentLatitude": 0.0,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    data = resp.json()
    resp.raise_for_status()
    return data


# ---------------------------------------------------------------------------
# Lista de entregas
# ---------------------------------------------------------------------------

def buscar_pagina_entregas(token: str, page: int) -> list:
    url = f"{BASE_URL}/lm/express/driver/v1/driver/delivery/delivery/queryDeliveryListV3"
    headers = montar_headers_autenticados(token)
    body = {
        "groupMethod": 1,
        "deliveryTaskStatus": "delivery",
        "orderType": "",
        "problemReason": "",
        "problemType": "",
        "startDateTime": "",
        "endDateTime": "",
        "deliveredDateTime": "",
        "currentLongitude": 0.0,
        "currentLatitude": 0.0,
        "handedOver": False,
        "handedOverDateTime": "",
        "currentPage": page,
        "isDeliveredRangeReq": False,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    data = resp.json()
    resp.raise_for_status()
    if data.get("status") != "success":
        raise RuntimeError(f"Erro buscando entregas: {data.get('message')}")
    return data.get("resultObject") or []


def listar_todas_entregas(token: str) -> list:
    """Pagina ate acabar, e ja achata cada waybill (dentro de
    queryDeliveryStatusDTOS) em um item separado na lista final.

    Para tanto se a pagina vier vazia quanto se vier so com waybills que
    ja apareceram antes (alguns backends nao devolvem lista vazia quando
    acaba a paginacao, so repetem a ultima pagina)."""
    resultado = []
    vistos = set()
    page = 1
    while True:
        print(f"  buscando pagina {page}...")
        tarefas = buscar_pagina_entregas(token, page)
        if not tarefas:
            print("  pagina vazia, parando.")
            break

        novos_nessa_pagina = 0
        for tarefa in tarefas:
            waybills = tarefa.get("queryDeliveryStatusDTOS") or []
            for wb in waybills:
                numero = wb.get("waybillNo")
                if numero in vistos:
                    continue
                vistos.add(numero)
                novos_nessa_pagina += 1
                resultado.append({
                    "waybillNo": numero,
                    "consignee": wb.get("consignee"),
                    "consigneeMobile": wb.get("consigneeMobile"),
                    "enderecoOriginal": wb.get("consigneeAddress"),
                    "enderecoFormatado": wb.get("consigneeAddressToGoogle"),
                    "bairro": wb.get("area"),
                    "cidade": wb.get("city"),
                    "cep": wb.get("consigneeZipCode"),
                    "lat": wb.get("latitude"),
                    "lng": wb.get("longitude"),
                })

        print(f"  {novos_nessa_pagina} novos nessa pagina ({len(resultado)} no total).")
        print(f"[IMILE-API] PROGRESSO {len(resultado)}")
        if novos_nessa_pagina == 0:
            print("  nenhum item novo (repetiu a pagina anterior), parando.")
            break

        page += 1
        if page > 50:  # trava de seguranca
            print("  atingiu o limite de 50 paginas, parando por seguranca.")
            break
    return resultado


# ---------------------------------------------------------------------------
# Exportacao
# ---------------------------------------------------------------------------

def salvar_json(resultado: list, caminho: str):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)


def salvar_csv(resultado: list, caminho: str):
    import csv
    if not resultado:
        return
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(resultado[0].keys()))
        writer.writeheader()
        writer.writerows(resultado)


def salvar_xlsx_rota(resultado: list, caminho: str):
    """Salva no formato que o Rota Manager reconhece na importacao."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Rota"

    colunas = [
        "Sequencia", "Endereco_Original", "Endereco_Reformado",
        "Latitude", "Longitude", "Coordenadas", "Bairro", "CEP",
        "Telefone", "Nome", "Numero_Rastreio", "Rotas_Iguais",
    ]
    ws.append(colunas)

    for i, item in enumerate(resultado, start=1):
        lat = item.get("lat") or ""
        lng = item.get("lng") or ""
        coordenadas = f"{lat},{lng}" if lat and lng else ""
        ws.append([
            i,
            item.get("enderecoOriginal") or "",
            item.get("enderecoFormatado") or "",
            lat,
            lng,
            coordenadas,
            item.get("bairro") or "",
            item.get("cep") or "",
            item.get("consigneeMobile") or "",
            item.get("consignee") or "",
            item.get("waybillNo") or "",
            "",
        ])

    wb.save(caminho)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if USERNAME == "SEU_USUARIO_AQUI":
        print("Preenche USERNAME e PASSWORD no topo do arquivo antes de rodar.")
        return

    print("Fazendo login...")
    token = obter_token(USERNAME, PASSWORD)
    print("Login OK.")

    print("Registrando dispositivo na sessao...")
    handle_device_info_after_login(token, USERNAME)

    print("Buscando entregas (paginado)...")
    resultado = listar_todas_entregas(token)
    print(f"{len(resultado)} entregas encontradas.")
    print(f"[IMILE-API] TOTAL {len(resultado)}")

    if not resultado:
        print("Nenhuma entrega encontrada - nada pra salvar.")
        return

    salvar_json(resultado, OUTPUT_JSON)
    salvar_csv(resultado, OUTPUT_CSV)
    salvar_xlsx_rota(resultado, OUTPUT_XLSX)

    sem_coordenada = sum(1 for r in resultado if not r.get("lat") or not r.get("lng"))
    print(f"Salvo em {OUTPUT_JSON}, {OUTPUT_CSV} e {OUTPUT_XLSX}")
    print(f"{sem_coordenada} entregas sem coordenada.")


if __name__ == "__main__":
    main()
