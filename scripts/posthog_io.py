#!/usr/bin/env python3
"""
Ligação ao PostHog nos dois sentidos: ler eventos (HogQL) e escrever de volta.

O "escrever de volta" é o que fecha o ciclo. O PostHog recebe `feedback_submitted`
com o texto em bruto, mas o tema não vem lá — é inferido pelo agente. Sem
write-back, essa inteligência ficava presa num ficheiro JSON no repo e o
dashboard só saberia falar da campanha antiga. Ao devolver `feedback_classified`
ao PostHog, as dores passam a ser consultáveis ao lado dos resultados, na mesma
ferramenta e pelas mesmas pessoas.

Só stdlib (urllib) — ver nota sobre dependências no DECISIONS.md.
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid as uuid_lib

# Espaço de nomes fixo: o mesmo par (evento, chave) tem de dar sempre o mesmo
# UUID, entre execuções e entre máquinas. É o que torna o write-back idempotente.
UUID_NAMESPACE = uuid_lib.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def event_uuid(event_name, key):
    """UUID determinístico para um evento — reenviar não duplica."""
    return str(uuid_lib.uuid5(UUID_NAMESPACE, f"{event_name}:{key}"))

HOST = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com").rstrip("/")
PROJECT_ID = os.environ.get("POSTHOG_PROJECT_ID", "")
PERSONAL_KEY = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")
PROJECT_KEY = os.environ.get("POSTHOG_PROJECT_KEY", "")

CAPTURE_BATCH = 100


def _post(url, payload, headers=None, timeout=90, method="POST"):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def query(hogql, retries=3):
    """Corre HogQL e devolve as linhas. Retenta em erro transitório (5xx/rede)."""
    if not PROJECT_ID or not PERSONAL_KEY:
        raise RuntimeError(
            "Faltam POSTHOG_PROJECT_ID / POSTHOG_PERSONAL_API_KEY no ambiente."
        )
    url = f"{HOST}/api/projects/{PROJECT_ID}/query/"
    headers = {"Authorization": f"Bearer {PERSONAL_KEY}"}
    payload = {"query": {"kind": "HogQLQuery", "query": hogql}}

    last = None
    for attempt in range(retries):
        try:
            return _post(url, payload, headers)["results"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            last = f"HTTP {exc.code}: {detail}"
            if exc.code < 500 and exc.code != 429:
                raise RuntimeError(f"PostHog recusou a query — {last}") from exc
        except urllib.error.URLError as exc:
            last = f"rede: {exc}"
        time.sleep(2 ** attempt)
    raise RuntimeError(f"PostHog indisponível após {retries} tentativas — {last}")


def capture(events, dry_run=False):
    """Envia eventos para o PostHog. `events` = [{event, distinct_id, properties}].

    Devolve quantos foram enviados. Nunca levanta exceção: o write-back é um
    enriquecimento do dashboard, não deve derrubar o pipeline se falhar — mas
    o número devolvido entra no run_log para ficar visível se falhar.
    """
    if not events:
        return 0
    if not PROJECT_KEY:
        print("  [write-back] sem POSTHOG_PROJECT_KEY — ignorado")
        return 0
    if dry_run:
        print(f"  [write-back] dry-run: {len(events)} eventos não enviados")
        return 0

    sent = 0
    for i in range(0, len(events), CAPTURE_BATCH):
        chunk = events[i:i + CAPTURE_BATCH]
        batch = [
            {
                "event": e["event"],
                "properties": {**e.get("properties", {}),
                               "distinct_id": e.get("distinct_id", "pipeline"),
                               "$lib": "challenge-pipeline"},
                # O `uuid` é determinístico (ver `event_uuid`). O pipeline corre
                # todas as semanas sobre o mesmo feedback, e sem isto cada
                # execução criava outra cópia de cada classificação — ao fim de
                # cinco execuções o dashboard mostrava 755 classificações para
                # 151 feedbacks. O PostHog descarta eventos com um uuid que já viu.
                **({"uuid": e["uuid"]} if e.get("uuid") else {}),
                **({"timestamp": e["timestamp"]} if e.get("timestamp") else {}),
            }
            for e in chunk
        ]
        try:
            _post(f"{HOST}/batch/", {"api_key": PROJECT_KEY, "batch": batch}, timeout=45)
            sent += len(chunk)
        except Exception as exc:  # noqa: BLE001 — write-back nunca derruba o run
            print(f"  [write-back] falhou o lote {i // CAPTURE_BATCH}: {exc}")
    return sent


# ── Queries usadas pelos agentes ─────────────────────────────────────────────

FEEDBACK_QUERY = """
SELECT
  toString(uuid),
  properties.feedback_type,
  properties.text,
  properties.channel,
  toString(timestamp)
FROM events
WHERE event = 'feedback_submitted'
ORDER BY timestamp DESC
LIMIT 1000
"""

CAMPAIGN_QUERY = """
SELECT
  event,
  properties.creative_id,
  properties.angle_type,
  properties.theme,
  properties.headline,
  properties.utm_source,
  properties.device_type,
  properties.utm_campaign
FROM events
WHERE event IN ('creative_view', 'cta_click')
LIMIT 50000
"""


def fetch_feedback():
    rows = query(FEEDBACK_QUERY)
    return [
        {
            "ref": r[0],
            "feedback_type": r[1],
            "text": r[2],
            "channel": r[3],
            "timestamp": r[4],
        }
        for r in rows
        if r[2]
    ]


def fetch_campaign():
    rows = query(CAMPAIGN_QUERY)
    views, clicks = [], []
    for r in rows:
        props = {
            "creative_id": r[1],
            "angle_type": r[2],
            "theme": r[3],
            "headline": r[4],
            "utm_source": r[5],
            "device_type": r[6],
            "utm_campaign": r[7],
        }
        (views if r[0] == "creative_view" else clicks).append(props)
    return views, clicks
