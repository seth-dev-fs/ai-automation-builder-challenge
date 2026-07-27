#!/usr/bin/env python3
"""
Wrapper do LLM (Gemini 2.5 Flash) com contrato de output à força.

O pressuposto é que o modelo VAI falhar — não é uma hipótese remota, é o caso
normal ao fim de algumas centenas de chamadas. Portanto o wrapper trata a
resposta como input não confiável e aplica três camadas:

  1. Restrição na origem — `responseMimeType: application/json` +
     `responseSchema`. Nota não-óbvia: no 2.5 Flash é preciso pôr também
     `thinkingConfig.thinkingBudget = 0` quando se usa output estruturado, senão
     o "pensamento" consome o orçamento de tokens e o JSON vem truncado a meio.
     Já perdi horas com isto noutro projeto.

  2. Validação nossa depois de responder — o schema da Google garante a forma,
     não garante a substância. Um `urgency: 9` numa escala de 1 a 5 passa o
     schema se o enum não estiver declarado; um copy de 400 caracteres também.
     Cada chamada passa um `validator` próprio, e quando ele rejeita, o erro
     concreto volta ao modelo no retry ("devolveste X, era esperado Y").

  3. Desistência controlada — ao fim das tentativas, `call_json` levanta
     `LLMUnavailable`. Quem chama tem de ter um caminho determinístico. Nunca
     se devolve o controlo ao modelo nem se deixa passar o output inválido.

Sem SDK: urllib puro. Menos uma dependência que pode partir o CI, e o repo
já era stdlib-only.
"""

import json
import re
import os
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_ATTEMPTS = 3

# O plano gratuito do Gemini permite 10 pedidos por minuto. O pipeline faz 10 a
# 14 chamadas seguidas, portanto sem espaçamento bate no limite a meio e degrada
# criativos que não tinham nada de errado. Seis segundos e meio entre chamadas
# mantém-nos dentro do limite; num plano pago, põe-se a zero pela variável.
MIN_INTERVAL = float(os.environ.get("GEMINI_MIN_INTERVAL", "6.5"))
_last_call_at = 0.0

# Registo de tudo o que aconteceu — vai para analysis/run_log.json.
TRACE = {
    "calls": [],
    "attempts": 0,
    "schema_rejections": 0,
    "transport_errors": 0,
    "degradations": [],
}


class LLMUnavailable(RuntimeError):
    """O modelo não devolveu output utilizável dentro das tentativas."""


class ContractError(ValueError):
    """A resposta veio bem formada mas violou o contrato de negócio."""


def _retry_delay_from(detail):
    """O 429 do Gemini traz o tempo de espera sugerido. Vale mais do que adivinhar."""
    match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', detail)
    return min(int(match.group(1)) + 1, 60) if match else None


def _throttle():
    global _last_call_at
    wait = MIN_INTERVAL - (time.time() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.time()


def _request(prompt, system, schema, temperature):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise LLMUnavailable("GEMINI_API_KEY não definida")

    _throttle()

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": schema,
            # Ver docstring: sem isto o JSON estruturado vem truncado.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    req = urllib.request.Request(
        f"{API_BASE}/{MODEL}:generateContent?key={key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.load(resp)

    candidates = body.get("candidates") or []
    if not candidates:
        # Sem candidates é quase sempre bloqueio de segurança ou erro do lado
        # deles. Retentar tem hipótese; inventar um fallback aqui não tem.
        raise urllib.error.URLError(
            f"resposta sem candidates: {json.dumps(body)[:300]}"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    usage = body.get("usageMetadata", {})
    return text, usage


def call_json(name, prompt, schema, validator=None, system=None, temperature=0.2):
    """Chama o modelo e devolve JSON validado, ou levanta LLMUnavailable.

    `validator(data) -> data` deve levantar ContractError com uma mensagem
    específica quando o conteúdo violar as regras de negócio. A mensagem é
    reinjetada no retry, por isso vale a pena ser concreta.
    """
    conversation = prompt
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        TRACE["attempts"] += 1
        started = time.time()
        try:
            raw, usage = _request(conversation, system, schema, temperature)
            data = json.loads(raw)
            if validator:
                data = validator(data)

            TRACE["calls"].append({
                "agent": name,
                "attempt": attempt,
                "status": "ok",
                "seconds": round(time.time() - started, 2),
                "tokens_in": usage.get("promptTokenCount"),
                "tokens_out": usage.get("candidatesTokenCount"),
            })
            return data

        except (json.JSONDecodeError, ContractError) as exc:
            TRACE["schema_rejections"] += 1
            last_error = str(exc)
            kind = "json_malformado" if isinstance(exc, json.JSONDecodeError) else "contrato"
            TRACE["calls"].append({
                "agent": name, "attempt": attempt, "status": f"rejeitado:{kind}",
                "error": last_error[:200],
            })
            # Reinjetar o erro concreto: a diferença entre "tenta outra vez" e
            # "tenta outra vez, e olha o que falhou da última".
            conversation = (
                f"{prompt}\n\n"
                f"--- A tua resposta anterior foi REJEITADA ---\n"
                f"Motivo: {last_error}\n"
                f"Corrige e devolve APENAS o JSON válido, respeitando o schema."
            )

        except urllib.error.HTTPError as exc:
            TRACE["transport_errors"] += 1
            # 800 e não 300: o `retryDelay` do 429 aparece no fim do corpo, e
            # truncar cedo de mais deitava fora justamente a parte útil.
            detail = exc.read().decode("utf-8", "replace")[:800]
            last_error = f"HTTP {exc.code}: {detail}"
            TRACE["calls"].append({
                "agent": name, "attempt": attempt, "status": "erro_http",
                "error": last_error[:200],
            })
            if exc.code in (400, 401, 403):
                break  # chave/pedido inválidos — retentar não resolve
            # Num 429, o próprio erro diz quanto esperar. Ignorar isso e usar o
            # backoff genérico é bater na porta outra vez cedo de mais.
            time.sleep(_retry_delay_from(detail) or min(2 ** attempt * 2, 30))

        except LLMUnavailable:
            # Erro de configuração (chave em falta), não transitório. Esperar
            # 30 segundos entre tentativas não faz aparecer uma chave.
            raise

        except Exception as exc:  # noqa: BLE001 — rede, timeout, sem candidates
            TRACE["transport_errors"] += 1
            last_error = str(exc)
            TRACE["calls"].append({
                "agent": name, "attempt": attempt, "status": "erro_transporte",
                "error": last_error[:200],
            })
            time.sleep(min(2 ** attempt * 2, 30))

    raise LLMUnavailable(f"[{name}] falhou {MAX_ATTEMPTS} tentativas — {last_error}")


def call_text(name, prompt, system=None, temperature=0.3, min_chars=200):
    """Variante para prosa (o relatório). Valida comprimento mínimo, nada mais."""
    schema = {
        "type": "OBJECT",
        "properties": {"markdown": {"type": "STRING"}},
        "required": ["markdown"],
    }

    def validate(data):
        text = (data.get("markdown") or "").strip()
        if len(text) < min_chars:
            raise ContractError(
                f"markdown com {len(text)} caracteres, mínimo {min_chars}"
            )
        return {"markdown": text}

    return call_json(name, prompt, schema, validate, system, temperature)["markdown"]


def note_degradation(agent, reason):
    """Regista que um agente passou ao caminho determinístico."""
    TRACE["degradations"].append({"agent": agent, "reason": str(reason)[:300]})
    print(f"  ⚠️  {agent}: a degradar para o caminho determinístico — {reason}")


def is_degraded():
    return bool(TRACE["degradations"])
