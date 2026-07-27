#!/usr/bin/env python3
"""
Agente 1 — análise de feedback.

Lê os `feedback_submitted` do PostHog, classifica cada um (tema, sentimento,
urgência) e agrupa em clusters.

Duas decisões de desenho que valem a pena explicar:

* **O LLM rotula, o código agrupa.** Seria natural pedir ao modelo "agrupa-me
  isto em clusters". Não faço isso: pedir agrupamento devolve grupos diferentes
  a cada execução, com nomes diferentes, e nada disto se consegue comparar de
  semana para semana. O modelo faz o que faz bem — ler texto ambíguo em
  português e atribuir-lhe um rótulo de uma lista fechada. A contagem, as
  percentagens e o ordenamento são aritmética, e a aritmética faz-se em código.

* **Índices em vez de UUIDs no prompt.** Cada lote vai numerado de 0 a N e o
  modelo devolve o índice. Mandar UUIDs de 36 caracteres para ele copiar de
  volta é gastar tokens a pedir um erro de transcrição que depois tenho de
  detetar. O índice é validado à saída — se faltar um, o lote é rejeitado.
"""

import json
import time
from collections import defaultdict

import llm
import taxonomy

BATCH_SIZE = 25
MAX_QUOTES = 4

SYSTEM = """És um analista de feedback de clientes de um produto SaaS português.
Classificas feedback com rigor e sem embelezar. Não inventas temas fora da lista.
Quando um feedback é ambíguo, escolhes 'outro' em vez de forçar um tema."""

ITEM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "i": {"type": "INTEGER"},
                    "theme": {"type": "STRING", "enum": taxonomy.THEMES},
                    "sentiment": {"type": "STRING", "enum": taxonomy.SENTIMENTS},
                    "urgency": {"type": "INTEGER"},
                    "summary": {"type": "STRING"},
                },
                "required": ["i", "theme", "sentiment", "urgency", "summary"],
            },
        }
    },
    "required": ["items"],
}


def _prompt(batch):
    linhas = "\n".join(
        f'{n}. [{item["feedback_type"]}] {item["text"]}'
        for n, item in enumerate(batch)
    )
    temas = "\n".join(f"- {t}: {taxonomy.THEME_LABELS[t]}" for t in taxonomy.THEMES)
    return f"""Classifica cada feedback abaixo.

TEMAS PERMITIDOS (usa exatamente estes slugs):
{temas}

REGRAS:
- `theme`: um e um só, da lista acima. Se não encaixar em nenhum, usa "outro".
- `sentiment`: negative para queixas, positive para elogios, neutral para
  observações sem carga. Respeita o rótulo entre parêntesis retos, exceto se o
  texto o contradisser claramente.
- `urgency`: 1 a 5. 5 = o cliente perdeu dinheiro, dados ou trabalho, ou está
  prestes a cancelar. 4 = fricção que se repete e bloqueia a tarefa principal.
  3 = incómodo real. 2 = observação menor. 1 = elogio ou neutro.
- `summary`: a dor ou o elogio em menos de 120 caracteres, em português, na
  terceira pessoa. Sem aspas, sem repetir o texto original à letra.
- Devolve exatamente {len(batch)} itens, com `i` de 0 a {len(batch) - 1}.

FEEDBACK:
{linhas}"""


def _validator(expected):
    def validate(data):
        items = data.get("items") or []
        if len(items) != expected:
            raise llm.ContractError(
                f"devolveste {len(items)} itens, eram esperados {expected}"
            )
        seen = set()
        for item in items:
            idx = item.get("i")
            if not isinstance(idx, int) or not 0 <= idx < expected:
                raise llm.ContractError(f"índice inválido: {idx!r}")
            if idx in seen:
                raise llm.ContractError(f"índice {idx} repetido")
            seen.add(idx)
            if item.get("theme") not in taxonomy.THEMES:
                raise llm.ContractError(
                    f"tema '{item.get('theme')}' não está na lista permitida"
                )
            if item.get("sentiment") not in taxonomy.SENTIMENTS:
                raise llm.ContractError(f"sentimento '{item.get('sentiment')}' inválido")
            urgency = item.get("urgency")
            if not isinstance(urgency, int) or not 1 <= urgency <= 5:
                raise llm.ContractError(f"urgency={urgency!r} fora da escala 1-5")
            summary = (item.get("summary") or "").strip()
            if not summary:
                raise llm.ContractError(f"summary vazio no item {idx}")
            if len(summary) > 160:
                raise llm.ContractError(
                    f"summary do item {idx} tem {len(summary)} caracteres (máx. 160)"
                )
        return data
    return validate


def classify(feedback):
    """Classifica todos os feedbacks. Degrada por lote, não em bloco.

    Se um lote falhar, só esse lote passa ao classificador determinístico — os
    restantes continuam a ser classificados pelo modelo. Uma falha de rede a
    meio não deita fora o trabalho todo.
    """
    classified = []
    for start in range(0, len(feedback), BATCH_SIZE):
        batch = feedback[start:start + BATCH_SIZE]
        label = f"feedback_analyst[{start}:{start + len(batch)}]"
        try:
            data = llm.call_json(
                label, _prompt(batch), ITEM_SCHEMA, _validator(len(batch)), SYSTEM
            )
            by_index = {item["i"]: item for item in data["items"]}
            for n, item in enumerate(batch):
                result = by_index[n]
                classified.append({
                    "ref": item["ref"],
                    "text": item["text"],
                    "feedback_type": item["feedback_type"],
                    "channel": item["channel"],
                    "timestamp": item["timestamp"],
                    "theme": result["theme"],
                    "sentiment": result["sentiment"],
                    "urgency": result["urgency"],
                    "summary": result["summary"].strip(),
                    "classified_by": "llm",
                })
        except llm.LLMUnavailable as exc:
            llm.note_degradation(label, exc)
            for item in batch:
                result = taxonomy.classify_fallback(item["text"], item["feedback_type"])
                classified.append({
                    "ref": item["ref"],
                    "text": item["text"],
                    "feedback_type": item["feedback_type"],
                    "channel": item["channel"],
                    "timestamp": item["timestamp"],
                    "classified_by": "fallback",
                    **result,
                })
    return classified


def build_clusters(classified, campaign_themes=()):
    """Agrupa por tema. Tudo aritmética — nenhum destes números vem do modelo."""
    by_theme = defaultdict(list)
    for item in classified:
        by_theme[item["theme"]].append(item)

    total = len(classified) or 1
    clusters = []
    for theme, items in by_theme.items():
        complaints = [i for i in items if i["sentiment"] == "negative"]
        praise = [i for i in items if i["sentiment"] == "positive"]
        urgencies = [i["urgency"] for i in items]
        pain_urgencies = [i["urgency"] for i in complaints] or [0]

        # As citações que representam o cluster: as mais urgentes primeiro, e
        # sem repetir texto (os dados semeados têm frases duplicadas).
        quotes, seen = [], set()
        for item in sorted(items, key=lambda i: -i["urgency"]):
            key = taxonomy.strip_accents(item["text"])[:60]
            if key in seen:
                continue
            seen.add(key)
            quotes.append({
                "ref": item["ref"],
                "text": item["text"],
                "urgency": item["urgency"],
                "sentiment": item["sentiment"],
            })
            if len(quotes) >= MAX_QUOTES:
                break

        clusters.append({
            "theme": theme,
            "label": taxonomy.THEME_LABELS.get(theme, theme),
            "total": len(items),
            "share_pct": round(100 * len(items) / total, 1),
            "complaints": len(complaints),
            "praise": len(praise),
            "pain_ratio": round(len(complaints) / len(items), 2),
            "avg_urgency": round(sum(urgencies) / len(items), 2),
            "avg_pain_urgency": round(sum(pain_urgencies) / len(pain_urgencies), 2),
            "covered_by_previous_campaign": theme in campaign_themes,
            "top_quotes": quotes,
        })

    return sorted(clusters, key=lambda c: (-c["complaints"], -c["total"]))


def to_posthog_events(classified):
    """Write-back: devolve a classificação ao PostHog, um evento por feedback.

    Sem isto o dashboard só sabe falar da campanha antiga — o tema do feedback
    não existe como propriedade nos eventos originais. É esta escrita que põe
    'quais são as dores' e 'o que converteu' na mesma ferramenta.
    """
    return [
        {
            "event": "feedback_classified",
            "distinct_id": f"feedback_{item['ref'][:12]}",
            "properties": {
                "feedback_ref": item["ref"],
                "theme": item["theme"],
                "theme_label": taxonomy.THEME_LABELS.get(item["theme"], item["theme"]),
                "sentiment": item["sentiment"],
                "urgency": item["urgency"],
                "feedback_type": item["feedback_type"],
                "channel": item["channel"],
                "summary": item["summary"],
                "classified_by": item["classified_by"],
            },
        }
        for item in classified
    ]


def run(feedback, campaign_themes=()):
    print(f"→ Agente 1: a classificar {len(feedback)} feedbacks...")
    classified = classify(feedback)
    clusters = build_clusters(classified, campaign_themes)

    by_llm = sum(1 for i in classified if i["classified_by"] == "llm")
    print(f"  {len(clusters)} clusters · {by_llm}/{len(classified)} pelo modelo")

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": llm.MODEL,
        "source_events": len(feedback),
        "taxonomy": taxonomy.THEMES,
        "coverage": {
            "total": len(classified),
            "by_llm": by_llm,
            "by_fallback": len(classified) - by_llm,
        },
        "degraded": by_llm < len(classified),
        "clusters": clusters,
        "items": [
            {k: v for k, v in item.items() if k != "text"} for item in classified
        ],
    }, classified
