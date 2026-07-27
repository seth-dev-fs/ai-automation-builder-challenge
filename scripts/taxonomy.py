#!/usr/bin/env python3
"""
Taxonomia fechada de temas + classificador determinístico de recurso.

Duas responsabilidades, ambas deliberadas:

1. `THEMES` é um enum fechado. O agente de análise NÃO pode inventar temas —
   se pudesse, teríamos 150 clusters de 1 elemento e nada para cruzar. Os seis
   primeiros slugs são exatamente os que a campanha anterior usou na propriedade
   `theme`, o que permite juntar feedback e resultados pela mesma chave.
   Os últimos três são temas que aparecem no feedback e que a campanha anterior
   nunca cobriu — é aí que costumam estar as oportunidades.

2. `classify_fallback()` é o degrade path. Quando o LLM falha (indisponível,
   quota, JSON irrecuperável), o pipeline não devolve vazio nem pede ao modelo
   que tente outra vez à sorte: passa a este classificador por palavra-chave,
   marca o resultado como degradado e segue. Pior qualidade, mas determinístico
   e auditável — e o humano é avisado no PR.
"""

import re
import unicodedata

# Alinhados com `properties.theme` da campanha anterior (prev_campaign_q1) ─────
THEMES_FROM_PREVIOUS_CAMPAIGN = [
    "agendamento",
    "suporte_lento",
    "poupanca_tempo",
    "facilidade",
    "relatorios",
    "integracoes",
]

# Temas presentes no feedback que a campanha anterior nunca abordou ───────────
THEMES_UNCOVERED = [
    "faturacao",
    "estabilidade",
]

THEMES = THEMES_FROM_PREVIOUS_CAMPAIGN + THEMES_UNCOVERED + ["outro"]

SENTIMENTS = ["negative", "positive", "neutral"]

THEME_LABELS = {
    "agendamento": "Agendamento e marcações",
    "suporte_lento": "Suporte e tempo de resposta",
    "poupanca_tempo": "Poupança de tempo",
    "facilidade": "Facilidade de uso",
    "relatorios": "Relatórios e métricas",
    "integracoes": "Integrações",
    "faturacao": "Faturação e subscrição",
    "estabilidade": "Estabilidade e desempenho",
    "outro": "Outro",
}

# Ordem importa: o primeiro tema com match ganha. Os mais específicos primeiro.
_KEYWORDS = [
    ("faturacao", ["fatur", "cobrad", "cobranc", "pagar", "preco", "plano que",
                   "subscric", "reembols", "cancelar a"]),
    ("estabilidade", ["crash", "bug", "travam", "trava", "lento", "falha",
                      "perdi trabalho", "rebenta", "erro"]),
    ("agendamento", ["marcac", "marcar", "marquei", "calendario", "agenda",
                     "sessao", "remarc", "reserva", "horario"]),
    ("suporte_lento", ["suporte", "apoio ao cliente", "responder", "resposta",
                       "ticket", "atendimento", "ninguem"]),
    ("integracoes", ["integra", "api", "sincroniz", "webhook", "exportar para"]),
    ("relatorios", ["relatorio", "dashboard", "metrica", "grafic", "resultados aos"]),
    ("poupanca_tempo", ["poupo", "poupa", "minutos", "produtividade", "trabalho manual",
                        "demorava", "menos tempo", "rapid"]),
    ("facilidade", ["facil", "intuitiv", "simples", "manual", "percebe-se",
                    "aprend", "sozinho"]),
]


def strip_accents(text):
    """'faturação' -> 'faturacao'. Os dados semeados vêm sem acentos, a LP não."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def classify_fallback(text, feedback_type=None):
    """Classificação determinística de recurso. Devolve o mesmo contrato do LLM."""
    norm = strip_accents(text)
    theme = "outro"
    for candidate, words in _KEYWORDS:
        if any(w in norm for w in words):
            theme = candidate
            break

    if feedback_type == "complaint":
        sentiment = "negative"
    elif feedback_type == "praise":
        sentiment = "positive"
    else:
        sentiment = "negative" if theme in THEMES_UNCOVERED else "neutral"

    # Urgência: base pelo sentimento, agravada por sinais explícitos de perda.
    urgency = 3 if sentiment == "negative" else 1
    if sentiment == "negative":
        if re.search(r"perd|crash|cobrad|duas vezes|nao consigo|impossivel", norm):
            urgency = 5
        elif theme in ("agendamento", "faturacao", "estabilidade"):
            urgency = 4

    summary = (text or "").strip()
    if len(summary) > 120:
        summary = summary[:117].rstrip() + "..."

    return {
        "theme": theme,
        "sentiment": sentiment,
        "urgency": urgency,
        "summary": summary,
    }
