"""
Limpa/padroniza enderecos brutos usando o Gemini, seguindo as regras
descritas em gemini_md.md. Usado pelo anjun_extrator.py e imile_extrator.py
antes de gerar o xlsx, pra chegar no Rota Manager ja com o endereco
organizado (Endereco_Reformado).

Uso: gemini_enderecos.limpar_enderecos(["end 1 bruto", "end 2 bruto", ...])
     -> ["end 1 limpo", "end 2 limpo", ...] (mesma ordem, mesmo tamanho)

Se a chave nao estiver configurada ou a chamada falhar, devolve os
enderecos originais sem quebrar a extracao.
"""

import json
import os
from pathlib import Path

import requests

# gemini-2.5-flash foi descontinuado pra chaves novas (404 "no longer
# available to new users"); gemini-flash-latest aponta sempre pro flash
# mais recente disponivel, evitando esse tipo de quebra no futuro.
# Defina GEMINI_API_KEY no ambiente onde o servidor.py roda - sem isso, os
# enderecos ficam sem correcao (ver limpar_enderecos abaixo).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

_REGRAS = (Path(__file__).parent / "gemini_md.md").read_text(encoding="utf-8")
_INSTRUCAO = (
    _REGRAS
    + "\n\nIMPORTANTE: ignore a secao 'Formato da Resposta' acima. A entrada e um "
      "JSON array de strings (enderecos brutos). Responda SOMENTE com um JSON array "
      "de strings, mesma ordem e mesmo tamanho da entrada, cada item sendo o "
      "'Endereco Organizado' correspondente."
)

_LOTE = 40  # enderecos por chamada, pra nao estourar o prompt


def _limpar_lote(enderecos: list) -> list:
    body = {
        "system_instruction": {"parts": [{"text": _INSTRUCAO}]},
        "contents": [{"parts": [{"text": json.dumps(enderecos, ensure_ascii=False)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    resp = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY}, json=body, timeout=60)
    resp.raise_for_status()
    texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    corrigidos = json.loads(texto)
    if len(corrigidos) != len(enderecos):
        raise ValueError(f"Gemini devolveu {len(corrigidos)} enderecos, esperava {len(enderecos)}")
    return corrigidos


def limpar_enderecos(enderecos: list) -> list:
    """Limpa uma lista de enderecos brutos, em lotes. Se um lote falhar
    (rede, chave invalida, resposta malformada), mantem os enderecos
    originais desse lote em vez de derrubar a extracao inteira."""
    if not GEMINI_API_KEY:
        return list(enderecos)

    resultado = []
    for i in range(0, len(enderecos), _LOTE):
        lote = enderecos[i:i + _LOTE]
        try:
            corrigidos = _limpar_lote(lote)
            resultado.extend(corrigidos)
            print(f"  [GEMINI] {i + len(lote)}/{len(enderecos)} enderecos corrigidos")
        except Exception as e:
            print(f"  [GEMINI] lote {i}-{i + len(lote)} falhou, mantendo original: {e}")
            resultado.extend(lote)
    return resultado


def _demo():
    """Self-check offline (sem chamar a API de verdade): valida que o
    batching e o fallback por lote funcionam."""
    calls = []

    def fake_lote(lote):
        calls.append(lote)
        if len(calls) == 2:
            raise RuntimeError("simulado")
        return [f"OK: {e}" for e in lote]

    global _limpar_lote
    original = _limpar_lote
    _limpar_lote = fake_lote
    try:
        enderecos = [f"end {i}" for i in range(_LOTE + 5)]
        out = limpar_enderecos(enderecos)
        assert len(out) == len(enderecos)
        assert out[0] == "OK: end 0", out[0]
        assert out[_LOTE] == "end 40", out[_LOTE]  # 2o lote falhou -> manteve original
        print("[gemini_enderecos] self-check OK")
    finally:
        _limpar_lote = original


if __name__ == "__main__":
    _demo()
