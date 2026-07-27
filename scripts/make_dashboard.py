#!/usr/bin/env python3
"""
Cria o dashboard público no PostHog, por API.

Feito em código e não à mão na interface por uma razão simples: um dashboard
montado à mão não se consegue recriar, nem versionar, nem explicar. Este
ficheiro é a definição do que o dashboard mostra — se amanhã for preciso o
mesmo dashboard noutro projeto, corre-se o script.

    python scripts/make_dashboard.py            # cria (ou atualiza) e partilha
    python scripts/make_dashboard.py --dry-run  # mostra as queries, não escreve

Precisa de uma Personal API Key com permissões de escrita em insights,
dashboards e sharing.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com").rstrip("/")
PROJECT_ID = os.environ.get("POSTHOG_PROJECT_ID", "")
KEY = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")

DASHBOARD_NAME = "Feedback → Criativos → Resultados"
DASHBOARD_DESCRIPTION = (
    "O ciclo completo numa página: o que os clientes dizem, o que a campanha "
    "anterior deu, e a relação entre as duas coisas. Gerado por "
    "scripts/make_dashboard.py."
)

# ── Os insights ──────────────────────────────────────────────────────────────
# A ordem conta: quem abre o dashboard deve ler de cima para baixo a mesma
# história que o relatório conta — o que converteu, porquê, e o que falta cobrir.

INSIGHTS = [
    {
        "name": "1 · CVR por criativo (campanha anterior)",
        "description": "O quadro geral. cr_A destaca-se de forma que não é ruído.",
        "query": """
SELECT
  properties.creative_id AS criativo,
  any(properties.headline) AS headline,
  any(properties.angle_type) AS angulo,
  countIf(event = 'creative_view') AS impressoes,
  countIf(event = 'cta_click') AS cliques,
  round(100.0 * countIf(event = 'cta_click') / countIf(event = 'creative_view'), 2) AS cvr_pct
FROM events
WHERE event IN ('creative_view', 'cta_click')
  AND properties.utm_campaign = 'prev_campaign_q1'
GROUP BY criativo
ORDER BY cvr_pct DESC
""",
    },
    {
        "name": "2 · CVR por ângulo — resolver a dor vs. amplificar o elogio",
        "description": "A conclusão com maior consequência para a próxima ronda.",
        "query": """
SELECT
  properties.angle_type AS angulo,
  countIf(event = 'creative_view') AS impressoes,
  countIf(event = 'cta_click') AS cliques,
  round(100.0 * countIf(event = 'cta_click') / countIf(event = 'creative_view'), 2) AS cvr_pct
FROM events
WHERE event IN ('creative_view', 'cta_click')
  AND properties.utm_campaign = 'prev_campaign_q1'
GROUP BY angulo
ORDER BY cvr_pct DESC
""",
    },
    {
        "name": "3 · Dores e elogios por tema (classificado pelo agente)",
        "description": (
            "O tema não vem no feedback — é inferido pelo agente e devolvido ao "
            "PostHog como `feedback_classified`. É isto que torna as dores "
            "consultáveis ao lado dos resultados."
        ),
        # `uniqExact` sobre o feedback_ref e não `count()`: cada execução do
        # pipeline reclassifica os mesmos feedbacks, e contar eventos contaria
        # a mesma queixa uma vez por execução. O write-back já é idempotente
        # (uuid determinístico), mas a query não deve depender disso — os
        # eventos das execuções anteriores à correção continuam na base.
        "query": """
SELECT
  properties.theme_label AS tema,
  uniqExactIf(properties.feedback_ref, properties.sentiment = 'negative') AS queixas,
  uniqExactIf(properties.feedback_ref, properties.sentiment = 'positive') AS elogios,
  uniqExact(properties.feedback_ref) AS total,
  round(avg(toFloat(properties.urgency)), 2) AS urgencia_media
FROM events
WHERE event = 'feedback_classified'
GROUP BY tema
ORDER BY queixas DESC
""",
    },
    {
        "name": "4 · O padrão — volume de queixas vs. CVR do tema",
        "description": (
            "A tese do pipeline, num só quadro: a ordem dos temas por volume de "
            "feedback acompanha a ordem por CVR. Um tema sem linha de campanha é "
            "uma dor real que nunca foi anunciada."
        ),
        "query": """
SELECT
  tema,
  sum(queixas) AS queixas_no_feedback,
  sum(elogios) AS elogios_no_feedback,
  round(100.0 * sum(cliques) / nullIf(sum(impressoes), 0), 2) AS cvr_pct
FROM (
  SELECT
    properties.theme AS tema,
    uniqExactIf(properties.feedback_ref, properties.sentiment = 'negative') AS queixas,
    uniqExactIf(properties.feedback_ref, properties.sentiment = 'positive') AS elogios,
    0 AS impressoes, 0 AS cliques
  FROM events WHERE event = 'feedback_classified' GROUP BY tema
  UNION ALL
  SELECT
    properties.theme AS tema,
    0 AS queixas, 0 AS elogios,
    countIf(event = 'creative_view') AS impressoes,
    countIf(event = 'cta_click') AS cliques
  FROM events
  WHERE event IN ('creative_view', 'cta_click')
    AND properties.utm_campaign = 'prev_campaign_q1'
  GROUP BY tema
)
GROUP BY tema
ORDER BY queixas_no_feedback DESC
""",
    },
    {
        "name": "5 · Urgência das queixas por tema",
        "description": "Volume não é gravidade. Um tema com poucas queixas mas urgentes merece atenção diferente.",
        "query": """
SELECT
  properties.theme_label AS tema,
  round(avg(toFloat(properties.urgency)), 2) AS urgencia_media,
  uniqExactIf(properties.feedback_ref, toFloat(properties.urgency) = 5) AS criticas,
  uniqExact(properties.feedback_ref) AS queixas
FROM events
WHERE event = 'feedback_classified' AND properties.sentiment = 'negative'
GROUP BY tema
ORDER BY urgencia_media DESC
""",
    },
    {
        "name": "6 · Feedback recebido ao longo do tempo",
        "description": "Volume por dia e por canal — para saber se a amostra está viva ou parada.",
        "query": """
SELECT
  toDate(timestamp) AS dia,
  countIf(properties.feedback_type = 'complaint') AS reclamacoes,
  countIf(properties.feedback_type = 'praise') AS elogios
FROM events
WHERE event = 'feedback_submitted'
GROUP BY dia
ORDER BY dia
""",
    },
    {
        "name": "7 · Automação vs. humano — propostos e aprovados",
        "description": (
            "Quantos criativos o pipeline propôs e quantos passaram no crivo "
            "humano (merge do Pull Request). Se a taxa for baixa, o problema "
            "está nos prompts."
        ),
        "query": """
SELECT
  properties.creative_id AS criativo,
  any(properties.theme) AS tema,
  any(properties.headline) AS headline,
  countIf(event = 'creative_generated') > 0 AS proposto,
  countIf(event = 'creative_approved') > 0 AS aprovado
FROM events
WHERE event IN ('creative_generated', 'creative_approved')
GROUP BY criativo
ORDER BY criativo
""",
    },
]


def api(path, payload=None, method="GET"):
    url = f"{HOST}/api/projects/{PROJECT_ID}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"{method} {path} → HTTP {exc.code}: {detail}") from exc


def find_dashboard():
    for item in api("/dashboards/?limit=100").get("results", []):
        if item.get("name") == DASHBOARD_NAME and not item.get("deleted"):
            return item
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        for insight in INSIGHTS:
            print(f"── {insight['name']}\n{insight['query'].strip()}\n")
        return

    if not PROJECT_ID or not KEY:
        sys.exit("Faltam POSTHOG_PROJECT_ID / POSTHOG_PERSONAL_API_KEY.")

    dashboard = find_dashboard()
    if dashboard:
        print(f"Dashboard já existe (id {dashboard['id']}) — a substituir os insights.")
        for tile in api(f"/dashboards/{dashboard['id']}/").get("tiles", []):
            insight = tile.get("insight")
            if insight:
                api(f"/insights/{insight['id']}/", {"deleted": True}, method="PATCH")
    else:
        dashboard = api("/dashboards/", {
            "name": DASHBOARD_NAME,
            "description": DASHBOARD_DESCRIPTION,
            "pinned": True,
        }, method="POST")
        print(f"Dashboard criado (id {dashboard['id']}).")

    for insight in INSIGHTS:
        created = api("/insights/", {
            "name": insight["name"],
            "description": insight["description"],
            "dashboards": [dashboard["id"]],
            "query": {
                "kind": "DataVisualizationNode",
                "source": {"kind": "HogQLQuery", "query": insight["query"].strip()},
            },
        }, method="POST")
        print(f"  ✓ {created['name']}")

    sharing = api(f"/dashboards/{dashboard['id']}/sharing/",
                  {"enabled": True}, method="PATCH")
    token = sharing.get("access_token")

    print("\n" + "=" * 62)
    if token:
        public = HOST.replace("://eu.i.", "://eu.").replace("://us.i.", "://us.")
        print(f"Dashboard público:\n  {public}/shared/{token}")
    else:
        print("Partilha não devolveu token — ativar à mão em Dashboard → Share.")
    print(f"Interno:\n  {HOST.replace('://eu.i.', '://eu.').replace('://us.i.', '://us.')}"
          f"/project/{PROJECT_ID}/dashboard/{dashboard['id']}")
    print("=" * 62)


if __name__ == "__main__":
    main()
