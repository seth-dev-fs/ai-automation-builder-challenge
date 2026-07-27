#!/usr/bin/env python3
"""
Agente 2 — geração de criativos.

Duas coisas que este agente NÃO faz, de propósito:

* **Não escolhe os temas.** A escolha é uma pontuação calculada em código
  (`prioritise`), a partir de volume de feedback, urgência, desempenho histórico
  do tema e cobertura. Fica auditável: qualquer pessoa vê porque é que um tema
  entrou e outro ficou de fora, e a fórmula discute-se. Se fosse o modelo a
  escolher, a resposta a "porquê este tema?" seria "porque sim".

* **Não publica.** Tudo o que sai daqui nasce com `status: draft` e entra no
  repositório por Pull Request. Um anúncio é uma coisa que vai aparecer em nome
  da empresa a pessoas reais — o merge do PR é a assinatura humana.

Validação: além do schema, há regras de negócio que o schema não apanha —
limites de caracteres das plataformas, claims proibidos (superlativos absolutos,
percentagens que não temos como sustentar) e, sobretudo, **evidência
verificável**: o modelo tem de citar quais os feedbacks concretos que sustentam
o ângulo, por índice, e os índices são conferidos contra a lista real. É a
diferença entre um criativo inspirado nos dados e um criativo que diz que foi.
"""

import json
import re
import time

import llm
import taxonomy

MAX_CREATIVES = 3
CAMPAIGN = "next_campaign_q3"

# Abaixo deste número de menções, um tema não entra sequer na priorização.
# Sem este limiar a urgência domina: três queixas graves batiam quinze
# moderadas, e acabávamos a comprar tráfego para uma dor que quase ninguém tem.
# Um tema urgente com pouco volume é um problema de suporte, não de anúncio.
MIN_SIGNAL = 5

CTA_OPTIONS = [
    "Experimentar grátis",
    "Ver como funciona",
    "Começar agora",
    "Marcar demonstração",
    "Saber mais",
]

# Claims que não passam: ou não temos como os sustentar com estes dados, ou são
# proibidos pelas políticas de anúncios das plataformas.
BANNED_PATTERNS = [
    (r"\d+\s*%", "percentagem inventada — não há dados que a sustentem"),
    (r"\bo melhor\b|\ba melhor\b|\bnúmero 1\b|\bnº ?1\b|\blíder de mercado\b",
     "superlativo absoluto não fundamentado"),
    (r"\bgarantid[oa]\b|\bsempre\b.{0,12}\bgrátis\b|\b100%\b", "promessa absoluta"),
    (r"\[|\]|\{|\}|lorem ipsum|xxx", "placeholder por preencher"),
]

SYSTEM = """És um copywriter de performance que escreve anúncios em português de
Portugal para um produto SaaS. Escreves curto, concreto e na linguagem do
cliente — usas as palavras que ele usou no feedback, não jargão de marketing.
Nunca prometes o que não podes provar."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "angle": {"type": "STRING"},
        "headline": {"type": "STRING"},
        "primary_text": {"type": "STRING"},
        "cta": {"type": "STRING", "enum": CTA_OPTIONS},
        "image_prompt": {"type": "STRING"},
        "why_this_works": {"type": "STRING"},
        "evidence_indices": {"type": "ARRAY", "items": {"type": "INTEGER"}},
    },
    "required": ["angle", "headline", "primary_text", "cta", "image_prompt",
                 "why_this_works", "evidence_indices"],
}


def prioritise(clusters, theme_performance):
    """Pontuação de prioridade — determinística e auditável.

    Quatro parcelas, num total de 100:
      volume   (0-40)  quanto se fala do tema
      urgência (0-25)  quão graves são as queixas (pesado pela fração de dor)
      histórico(0-25)  como se portou o tema na campanha anterior, face à média
      lacuna   (0-10)  bónus a temas com dor real que nunca foram anunciados
    """
    perf = {row["key"]: row["cvr"] for row in theme_performance}
    avg_cvr = (sum(perf.values()) / len(perf)) if perf else 0

    max_signal = max(
        (max(c["complaints"], c["praise"]) for c in clusters if c["theme"] != "outro"),
        default=1,
    ) or 1

    scored = []
    for cluster in clusters:
        if cluster["theme"] == "outro":
            continue

        is_pain = cluster["pain_ratio"] >= 0.5
        signal = cluster["complaints"] if is_pain else cluster["praise"]
        if signal < MIN_SIGNAL:
            continue

        volume_pts = 40 * signal / max_signal
        urgency_pts = 25 * (cluster["avg_pain_urgency"] / 5) * cluster["pain_ratio"] \
            if is_pain else 25 * 0.4
        historical = perf.get(cluster["theme"])
        history_pts = 25 * min(historical / avg_cvr, 2.0) / 2.0 if (historical and avg_cvr) \
            else 12.5
        gap_pts = 10 if historical is None else 0

        scored.append({
            **cluster,
            "angle_type": "pain_resolution" if is_pain else "praise_amplification",
            "feedback_signal": signal,
            "historical_cvr_pct": round(100 * historical, 2) if historical else None,
            "priority_score": round(volume_pts + urgency_pts + history_pts + gap_pts, 1),
            "priority_breakdown": {
                "volume": round(volume_pts, 1),
                "urgencia": round(urgency_pts, 1),
                "historico": round(history_pts, 1),
                "lacuna": gap_pts,
            },
        })

    return sorted(scored, key=lambda c: -c["priority_score"])


def _prompt(cluster, quotes, facts_summary):
    citacoes = "\n".join(f'{n}. "{q["text"]}"' for n, q in enumerate(quotes))
    intent = ("resolver uma dor" if cluster["angle_type"] == "pain_resolution"
              else "amplificar um elogio")
    return f"""Escreve UM anúncio para o tema **{cluster['label']}**.

ÂNGULO: {intent} (`{cluster['angle_type']}`).

O QUE OS CLIENTES DISSERAM SOBRE ESTE TEMA (usa as palavras deles):
{citacoes}

CONTEXTO DE DESEMPENHO:
{facts_summary}

REGRAS DE OUTPUT:
- `headline`: no máximo 40 caracteres. Concreta. Sem ponto final.
- `primary_text`: entre 80 e 280 caracteres. Fala do problema antes da solução.
- `cta`: exatamente um de {CTA_OPTIONS}.
- `image_prompt`: pelo menos 100 caracteres, em inglês, descrevendo a cena, o
  enquadramento e a luz. Sem texto dentro da imagem.
- `evidence_indices`: os números das citações acima que sustentam este anúncio.
  Pelo menos um. Só podes usar índices de 0 a {len(quotes) - 1}.
- `angle`: a tese do anúncio numa frase — o argumento que ele faz ao leitor.
  NÃO repitas aqui o rótulo `{cluster['angle_type']}`, isso já está registado
  noutro campo; escreve a ideia.
- `why_this_works`: uma frase, a ligar o anúncio ao que os dados mostram.

PROIBIDO: percentagens, "o melhor", "número 1", "garantido", promessas absolutas,
e qualquer número que não venhas a conseguir sustentar. Português de Portugal."""


def _validator(n_quotes):
    def validate(data):
        headline = (data.get("headline") or "").strip()
        primary = (data.get("primary_text") or "").strip()
        image = (data.get("image_prompt") or "").strip()
        indices = data.get("evidence_indices") or []

        if not 1 <= len(headline) <= 40:
            raise llm.ContractError(
                f"headline tem {len(headline)} caracteres, o limite é 40"
            )
        if not 80 <= len(primary) <= 300:
            raise llm.ContractError(
                f"primary_text tem {len(primary)} caracteres, tem de estar entre 80 e 300"
            )
        if len(image) < 100:
            raise llm.ContractError(
                f"image_prompt tem {len(image)} caracteres, o mínimo é 100"
            )
        if data.get("cta") not in CTA_OPTIONS:
            raise llm.ContractError(f"cta '{data.get('cta')}' não está na lista permitida")

        if not indices:
            raise llm.ContractError(
                "evidence_indices vazio — todo o anúncio tem de citar feedback real"
            )
        for idx in indices:
            if not isinstance(idx, int) or not 0 <= idx < n_quotes:
                raise llm.ContractError(
                    f"evidence_indices contém {idx!r}, que não é uma citação existente "
                    f"(intervalo válido: 0 a {n_quotes - 1})"
                )

        blob = taxonomy.strip_accents(f"{headline} {primary}")
        for pattern, reason in BANNED_PATTERNS:
            if re.search(pattern, blob, re.IGNORECASE):
                raise llm.ContractError(f"copy rejeitado: {reason}")

        return data
    return validate


def _fallback_creative(cluster, quotes):
    """Criativo determinístico de recurso — deliberadamente pobre e assinalado.

    Não tenta imitar o modelo. Monta um esqueleto a partir do feedback real e
    marca-se como incompleto, para que o humano perceba de imediato que aquilo
    precisa de ser escrito. O que não pode acontecer é o pipeline entregar
    silêncio ou uma frase inventada com ar de acabada.
    """
    quote = quotes[0]["text"] if quotes else cluster["label"]
    return {
        "angle": f"Responder à dor mais reportada em {cluster['label'].lower()}",
        "headline": cluster["label"][:40],
        "primary_text": (
            f'Os nossos clientes dizem: "{quote}" '
            "— ESBOÇO POR ESCREVER, gerado sem modelo."
        )[:300],
        "cta": "Saber mais",
        "image_prompt": "TODO: sem modelo disponível nesta execução.",
        "why_this_works": "Esboço determinístico — requer reescrita humana.",
        "evidence_indices": [0] if quotes else [],
        "_incomplete": True,
    }


def to_markdown(creative):
    """Ficheiro do criativo: metadados rastreáveis + copy + evidência."""
    meta = {k: v for k, v in creative.items() if k not in ("evidence", "body")}
    evidencia = "\n".join(
        f'> {e["text"]}  \n> <sub>`{e["ref"]}` · urgência {e["urgency"]}/5</sub>\n'
        for e in creative["evidence"]
    )
    aviso = ""
    if creative.get("incomplete"):
        aviso = ("\n> ⚠️ **Esboço incompleto** — gerado pelo caminho determinístico "
                 "porque o modelo não respondeu. Não publicar sem reescrever.\n")

    return f"""---
{json.dumps(meta, ensure_ascii=False, indent=2)}
---

# {creative['headline']}
{aviso}
**Ângulo.** {creative['angle']}

**Copy.**

{creative['primary_text']}

**CTA.** {creative['cta']}

**Prompt de imagem.**

```
{creative['image_prompt']}
```

**Porque deve funcionar.** {creative['why_this_works']}

## Evidência

Este criativo foi gerado a partir de feedback real de clientes. As citações
abaixo são as que o agente identificou como suporte do ângulo — cada `ref` é o
UUID do evento `feedback_submitted` no PostHog, portanto o percurso do anúncio
até à frase que o originou é verificável.

{evidencia}

## Medição

Ao publicar, marcar com `utm_campaign={creative['utm_campaign']}` e
`utm_content={creative['creative_id']}`. As propriedades `angle_type` e `theme`
seguem o mesmo esquema da campanha anterior, por isso os insights do dashboard
medem esta ronda sem precisarem de ser alterados.
"""


def run(clusters, theme_performance, facts_summary):
    print("→ Agente 2: a gerar criativos...")
    ranked = prioritise(clusters, theme_performance)[:MAX_CREATIVES]
    creatives = []

    for n, cluster in enumerate(ranked, start=1):
        quotes = cluster["top_quotes"]
        label = f"creative_writer[{cluster['theme']}]"
        incomplete = False
        try:
            data = llm.call_json(
                label, _prompt(cluster, quotes, facts_summary), SCHEMA,
                _validator(len(quotes)), SYSTEM, temperature=0.7,
            )
        except llm.LLMUnavailable as exc:
            llm.note_degradation(label, exc)
            data = _fallback_creative(cluster, quotes)
            incomplete = True

        creative_id = f"cr_q3_{cluster['theme']}_{n:02d}"
        creatives.append({
            "creative_id": creative_id,
            "status": "draft",
            "theme": cluster["theme"],
            "theme_label": cluster["label"],
            "angle_type": cluster["angle_type"],
            "utm_campaign": CAMPAIGN,
            "utm_content": creative_id,
            "utm_medium": "paid_social",
            "priority_score": cluster["priority_score"],
            "priority_breakdown": cluster["priority_breakdown"],
            "feedback_signal": cluster["feedback_signal"],
            "avg_urgency": cluster["avg_pain_urgency"],
            "historical_cvr_pct": cluster["historical_cvr_pct"],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generated_by": "fallback" if incomplete else llm.MODEL,
            "incomplete": incomplete,
            "angle": data["angle"],
            "headline": data["headline"],
            "primary_text": data["primary_text"],
            "cta": data["cta"],
            "image_prompt": data["image_prompt"],
            "why_this_works": data["why_this_works"],
            "evidence": [quotes[i] for i in data["evidence_indices"] if i < len(quotes)],
        })
        print(f"  {creative_id} · prioridade {cluster['priority_score']} · "
              f"{'ESBOÇO' if incomplete else data['headline']}")

    return creatives, ranked


def to_posthog_events(creatives):
    """Regista no PostHog que estes criativos existem e estão à espera de revisão."""
    return [
        {
            "event": "creative_generated",
            "distinct_id": c["creative_id"],
            "properties": {
                "creative_id": c["creative_id"],
                "angle_type": c["angle_type"],
                "theme": c["theme"],
                "headline": c["headline"],
                "utm_campaign": c["utm_campaign"],
                "utm_content": c["creative_id"],
                "status": c["status"],
                "priority_score": c["priority_score"],
                "generated_by": c["generated_by"],
                "incomplete": c["incomplete"],
            },
        }
        for c in creatives
    ]
