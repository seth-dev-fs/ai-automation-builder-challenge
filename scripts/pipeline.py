#!/usr/bin/env python3
"""
Pipeline dos 3 agentes — corre no GitHub Actions e escreve os resultados no repo.

Isto é um ESQUELETO. A ligação de leitura ao PostHog já está feita (função
`posthog_query`); a inteligência (classificar, agrupar, gerar criativos, tirar
conclusões) é contigo. Implementa os três TODO e faz o script escrever para:

  analysis/feedback_clusters.json   (Agente 1 — análise de feedback)
  analysis/results_report.md        (Agente 3 — leitura de resultados)
  creatives/<id>.md                 (Agente 2 — ângulo + copy + prompt de imagem)

O workflow `.github/workflows/generate.yml` corre este ficheiro e faz commit do
que mudar em analysis/ e creatives/.

Variáveis de ambiente (definidas como GitHub Secrets):
  POSTHOG_HOST, POSTHOG_PROJECT_ID, POSTHOG_PERSONAL_API_KEY
  + a(s) chave(s) de LLM que usares (ex: GEMINI_API_KEY, ANTHROPIC_API_KEY)
"""

import json
import os
import urllib.request

HOST = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")
PROJECT_ID = os.environ["POSTHOG_PROJECT_ID"]
PERSONAL_KEY = os.environ["POSTHOG_PERSONAL_API_KEY"]


def posthog_query(hogql: str):
    """Corre uma query HogQL e devolve as linhas de resultado."""
    req = urllib.request.Request(
        f"{HOST}/api/projects/{PROJECT_ID}/query/",
        data=json.dumps({"query": {"kind": "HogQLQuery", "query": hogql}}).encode("utf-8"),
        headers={"Authorization": f"Bearer {PERSONAL_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["results"]


def analyze_feedback():
    """Agente 1: lê feedback_submitted, classifica (tema/sentimento/urgência), agrupa."""
    rows = posthog_query(
        "SELECT properties.feedback_type, properties.text "
        "FROM events WHERE event = 'feedback_submitted' LIMIT 1000"
    )
    # TODO: passa `rows` pelo teu LLM com um contrato de output estrito.
    #       Valida o JSON antes de usar. Escreve analysis/feedback_clusters.json.
    raise NotImplementedError("Implementa o Agente de análise de feedback.")


def analyze_results():
    """Agente 3: lê resultados da campanha anterior e tira conclusões acionáveis."""
    # TODO: agrega creative_view/cta_click por creative_id -> CVR; pede ao LLM
    #       (ou calcula) conclusões priorizadas. Escreve analysis/results_report.md.
    raise NotImplementedError("Implementa o Agente de leitura de resultados.")


def generate_creatives():
    """Agente 2: a partir dos clusters, gera ângulos + copy + prompt de imagem."""
    # TODO: para os 2-3 temas mais relevantes, gera criativos rastreáveis por
    #       tag/UTM. Escreve creatives/<id>.md (e opcionalmente a imagem).
    raise NotImplementedError("Implementa o Agente de criativo.")


def main():
    analyze_feedback()
    analyze_results()
    generate_creatives()


if __name__ == "__main__":
    main()
