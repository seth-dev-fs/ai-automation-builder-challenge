#!/usr/bin/env python3
"""
Agente 3 — leitura dos resultados da campanha anterior.

A divisão de trabalho aqui é a peça central do desenho: **o código calcula, o
modelo interpreta.** Todas as tabelas, CVRs, intervalos de confiança, valores-p
e correlações são produzidos por `metrics.py` e escritos no relatório
diretamente pelo Python. O que o modelo recebe é o conjunto de factos já
calculados, e o que lhe é pedido é a única coisa que ele faz melhor do que uma
fórmula: dizer o que isto significa e o que fazer a seguir.

Consequência prática: se o modelo inventar uma percentagem no texto, ela vai
contradizer a tabela imediatamente acima, escrita por código. E se o modelo
estiver em baixo, o relatório sai na mesma — sem a secção interpretativa, com
um aviso — porque os factos não dependem dele.
"""

import time

import llm
import metrics
import taxonomy

SYSTEM = """És um analista de marketing de performance. Escreves para um
fundador que decide onde põe o orçamento na segunda-feira de manhã.
Não enfeitas, não repetes números que não te foram dados, e distingues sempre
um resultado significativo de uma flutuação. Escreves em português de Portugal."""


def compute(views, clicks, clusters):
    """Toda a estatística do relatório. Nenhum destes números passa pelo LLM."""
    by_creative = metrics.aggregate(views, clicks, "creative_id")
    by_angle = metrics.aggregate(views, clicks, "angle_type")
    by_theme = metrics.aggregate(views, clicks, "theme")
    by_source = metrics.aggregate(views, clicks, "utm_source")
    by_device = metrics.aggregate(views, clicks, "device_type")
    by_creative_device = metrics.aggregate(views, clicks, ("creative_id", "device_type"))

    headlines = {}
    angles = {}
    themes_of = {}
    for row in views:
        headlines[row["creative_id"]] = row.get("headline")
        angles[row["creative_id"]] = row.get("angle_type")
        themes_of[row["creative_id"]] = row.get("theme")
    for row in by_creative:
        row["headline"] = headlines.get(row["key"])
        row["angle_type"] = angles.get(row["key"])
        row["theme"] = themes_of.get(row["key"])

    total_views = sum(r["views"] for r in by_creative)
    total_clicks = sum(r["clicks"] for r in by_creative)

    def angle_row(name):
        return next((r for r in by_angle if r["key"] == name), {"clicks": 0, "views": 0})

    def device_row(name):
        return next((r for r in by_device if r["key"] == name), {"clicks": 0, "views": 0})

    pain, praise = angle_row("pain_resolution"), angle_row("praise_amplification")
    mobile, desktop = device_row("mobile"), device_row("desktop")

    tests = {
        "pain_vs_praise": metrics.two_proportion_z(
            pain["clicks"], pain["views"], praise["clicks"], praise["views"]
        ),
        "mobile_vs_desktop": metrics.two_proportion_z(
            mobile["clicks"], mobile["views"], desktop["clicks"], desktop["views"]
        ),
        "best_vs_rest": metrics.one_vs_rest(by_creative, by_creative[0]["key"]),
    }

    # ── A tese: o feedback prevê o CVR? ──────────────────────────────────────
    # Para cada criativo, o "sinal de feedback" é o volume de menções do seu
    # tema COM a carga correspondente ao ângulo: queixas para pain_resolution,
    # elogios para praise_amplification. Depois compara-se a ordenação dos
    # criativos por esse sinal com a ordenação por CVR.
    cluster_by_theme = {c["theme"]: c for c in clusters}
    signal = []
    for row in by_creative:
        cluster = cluster_by_theme.get(row["theme"])
        if not cluster:
            continue
        volume = (cluster["complaints"] if row["angle_type"] == "pain_resolution"
                  else cluster["praise"])
        signal.append({
            "creative_id": row["key"],
            "theme": row["theme"],
            "angle_type": row["angle_type"],
            "feedback_signal": volume,
            "avg_urgency": cluster["avg_pain_urgency"],
            "cvr_pct": row["cvr_pct"],
        })

    rank_by_signal = [s["creative_id"] for s in
                      sorted(signal, key=lambda s: -s["feedback_signal"])]
    rank_by_cvr = [s["creative_id"] for s in sorted(signal, key=lambda s: -s["cvr_pct"])]
    correlation = {"global": metrics.spearman(rank_by_signal, rank_by_cvr)}

    for angle in ("pain_resolution", "praise_amplification"):
        subset = [s for s in signal if s["angle_type"] == angle]
        correlation[angle] = metrics.spearman(
            [s["creative_id"] for s in sorted(subset, key=lambda s: -s["feedback_signal"])],
            [s["creative_id"] for s in sorted(subset, key=lambda s: -s["cvr_pct"])],
        )

    # ── Temas com dor real que a campanha anterior nunca cobriu ──────────────
    covered = {row["theme"] for row in by_creative}
    gaps = [
        {
            "theme": c["theme"],
            "label": c["label"],
            "complaints": c["complaints"],
            "avg_pain_urgency": c["avg_pain_urgency"],
            "quote": c["top_quotes"][0]["text"] if c["top_quotes"] else None,
        }
        for c in clusters
        if c["theme"] not in covered and c["theme"] != "outro" and c["complaints"] >= 3
    ]

    return {
        "totals": {
            "views": total_views,
            "clicks": total_clicks,
            "cvr_pct": round(100 * metrics.cvr(total_clicks, total_views), 2),
            "creatives": len(by_creative),
        },
        "by_creative": by_creative,
        "by_angle": by_angle,
        "by_theme": by_theme,
        "by_source": by_source,
        "by_device": by_device,
        "by_creative_device": by_creative_device,
        "tests": tests,
        "feedback_vs_cvr": {"rows": signal, "correlation": correlation},
        "coverage_gaps": gaps,
    }


# ── Tabelas escritas por código ──────────────────────────────────────────────

def _table(rows, header, formatter):
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    lines += ["| " + " | ".join(formatter(r)) + " |" for r in rows]
    return "\n".join(lines)


def render_facts(facts):
    t = facts["totals"]
    parts = [
        "## Os números\n",
        f"Campanha `prev_campaign_q1` — {t['views']} impressões, {t['clicks']} cliques, "
        f"CVR global **{t['cvr_pct']}%**, {t['creatives']} criativos.\n",
        "### Por criativo\n",
        _table(
            facts["by_creative"],
            ["Criativo", "Ângulo", "Tema", "Headline", "Vistas", "Cliques", "CVR", "IC 95%"],
            lambda r: [
                f"`{r['key']}`", r["angle_type"] or "—", r["theme"] or "—",
                f"_{r['headline']}_" if r["headline"] else "—",
                str(r["views"]), str(r["clicks"]), f"**{r['cvr_pct']}%**",
                f"{r['ci95_low_pct']}–{r['ci95_high_pct']}%",
            ],
        ),
        "\n### Por ângulo\n",
        _table(
            facts["by_angle"], ["Ângulo", "Vistas", "Cliques", "CVR", "IC 95%"],
            lambda r: [f"`{r['key']}`", str(r["views"]), str(r["clicks"]),
                       f"**{r['cvr_pct']}%**", f"{r['ci95_low_pct']}–{r['ci95_high_pct']}%"],
        ),
        "\n### Por dispositivo e por origem\n",
        _table(
            facts["by_device"] + facts["by_source"],
            ["Segmento", "Vistas", "Cliques", "CVR", "IC 95%"],
            lambda r: [f"`{r['key']}`", str(r["views"]), str(r["clicks"]),
                       f"{r['cvr_pct']}%", f"{r['ci95_low_pct']}–{r['ci95_high_pct']}%"],
        ),
    ]

    tests = facts["tests"]
    pain = tests["pain_vs_praise"]
    dev = tests["mobile_vs_desktop"]
    best = tests["best_vs_rest"]
    top = facts["by_creative"][0]
    parts += [
        "\n### Testes de significância\n",
        "| Comparação | Lift | z | p | Conclusão |",
        "|---|---|---|---|---|",
        f"| `pain_resolution` vs `praise_amplification` | {pain['lift']:+.0%} | {pain['z']} | "
        f"{pain['p_value']} | {'**significativo**' if pain['significant'] else 'não significativo'} |",
        f"| `{top['key']}` vs restantes | {best['lift']:+.0%} | {best['z']} | {best['p_value']} | "
        f"{'**significativo**' if best['significant'] else 'não significativo'} |",
        f"| `mobile` vs `desktop` | {dev['lift']:+.0%} | {dev['z']} | {dev['p_value']} | "
        f"{'**significativo**' if dev['significant'] else 'não significativo' } |",
    ]

    corr = facts["feedback_vs_cvr"]["correlation"]
    parts += [
        "\n### Sinal do feedback vs. desempenho do criativo\n",
        "Para cada criativo: quantas vezes o seu tema aparece no feedback, com a carga "
        "correspondente ao ângulo (queixas para `pain_resolution`, elogios para "
        "`praise_amplification`).\n",
        _table(
            sorted(facts["feedback_vs_cvr"]["rows"], key=lambda r: -r["cvr_pct"]),
            ["Criativo", "Tema", "Ângulo", "Menções no feedback", "CVR"],
            lambda r: [f"`{r['creative_id']}`", r["theme"], r["angle_type"],
                       str(r["feedback_signal"]), f"**{r['cvr_pct']}%**"],
        ),
        "",
        f"Correlação de postos (Spearman) entre volume de feedback e CVR: "
        f"**ρ = {corr['global']['rho']}** no conjunto dos {corr['global']['n']} criativos; "
        f"ρ = {corr['pain_resolution']['rho']} dentro de `pain_resolution` e "
        f"ρ = {corr['praise_amplification']['rho']} dentro de `praise_amplification`.",
    ]

    if facts["coverage_gaps"]:
        parts += [
            "\n### Dores sem criativo\n",
            "Temas com queixas registadas que a campanha anterior nunca abordou:\n",
            _table(
                facts["coverage_gaps"],
                ["Tema", "Queixas", "Urgência média", "Exemplo"],
                lambda r: [r["label"], str(r["complaints"]), str(r["avg_pain_urgency"]),
                           f'"{r["quote"]}"' if r["quote"] else "—"],
            ),
        ]

    return "\n".join(parts)


def _prompt(facts, clusters):
    corr = facts["feedback_vs_cvr"]["correlation"]
    top = facts["by_creative"][0]
    worst = facts["by_creative"][-1]
    dores = "\n".join(
        f"- {c['label']}: {c['complaints']} queixas, {c['praise']} elogios, "
        f"urgência média das queixas {c['avg_pain_urgency']}/5"
        for c in clusters[:8]
    )
    gaps = "\n".join(
        f"- {g['label']}: {g['complaints']} queixas, urgência {g['avg_pain_urgency']}/5, "
        f'exemplo: "{g["quote"]}"'
        for g in facts["coverage_gaps"]
    ) or "- (nenhum)"

    return f"""Escreve a leitura de uma campanha de anúncios já terminada.

FACTOS APURADOS (calculados em código — usa estes números e mais nenhum):

Campanha: {facts['totals']['views']} impressões, {facts['totals']['clicks']} cliques,
CVR global {facts['totals']['cvr_pct']}%.

Melhor criativo: {top['key']} ("{top['headline']}"), ângulo {top['angle_type']},
tema {top['theme']}, CVR {top['cvr_pct']}% (IC 95%: {top['ci95_low_pct']}–{top['ci95_high_pct']}%).
Pior criativo: {worst['key']} ("{worst['headline']}"), tema {worst['theme']},
CVR {worst['cvr_pct']}%.

Ângulos: pain_resolution {facts['by_angle'][0]['cvr_pct']}% vs
praise_amplification {facts['by_angle'][-1]['cvr_pct']}% →
lift {facts['tests']['pain_vs_praise']['lift']:+.0%}, p={facts['tests']['pain_vs_praise']['p_value']}
({'significativo' if facts['tests']['pain_vs_praise']['significant'] else 'NÃO significativo'}).

Dispositivo: mobile {facts['by_device'][0]['cvr_pct']}% vs desktop {facts['by_device'][-1]['cvr_pct']}%,
p={facts['tests']['mobile_vs_desktop']['p_value']}
({'significativo' if facts['tests']['mobile_vs_desktop']['significant'] else 'NÃO significativo — a diferença aparente pode ser ruído'}).

Correlação entre volume de menções no feedback e CVR do criativo desse tema:
Spearman ρ = {corr['global']['rho']} (n={corr['global']['n']}),
ρ = {corr['pain_resolution']['rho']} dentro de pain_resolution,
ρ = {corr['praise_amplification']['rho']} dentro de praise_amplification.

Volume de feedback por tema:
{dores}

Dores com queixas mas sem nenhum criativo na campanha anterior:
{gaps}

ESCREVE em markdown, com esta estrutura exata:

## Conclusões
Três a quatro pontos. O primeiro tem de ser o padrão principal que estes dados
revelam sobre a relação entre o feedback e o desempenho dos anúncios, e o que
isso implica para a forma de escolher criativos. Um dos pontos tem de identificar
explicitamente uma diferença que PARECE um padrão mas não passa no teste de
significância, e dizer que não se deve agir sobre ela ainda.

## O que fazer a seguir
Três recomendações numeradas e concretas, por ordem de prioridade, cada uma com
a justificação em números. Diz o que amplificar, o que cortar e o que testar de
novo.

## Limites desta leitura
Dois a três pontos honestos sobre o que estes dados não permitem concluir
(por exemplo: as impressões não foram distribuídas por igual pelos criativos;
não há dados de custo, portanto CVR não é ROI; a correlação observada tem n=6).

REGRAS: não inventes números. Não uses percentagens que não estejam acima.
Não escrevas introdução nem conclusão fora desta estrutura. Português de Portugal."""


def run(views, clicks, clusters):
    print(f"→ Agente 3: a ler {len(views)} impressões e {len(clicks)} cliques...")
    facts = compute(views, clicks, clusters)

    header = (
        "# Leitura dos resultados — `prev_campaign_q1`\n\n"
        f"_Gerado automaticamente em {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} "
        f"pelo pipeline (`scripts/pipeline.py`). Os números são calculados em Python "
        f"(`scripts/metrics.py`); a interpretação é do modelo `{llm.MODEL}` e foi revista "
        "por um humano antes de qualquer decisão de orçamento._\n"
    )

    try:
        narrative = llm.call_text(
            "results_reader", _prompt(facts, clusters), SYSTEM,
            temperature=0.3, min_chars=600,
        )
    except llm.LLMUnavailable as exc:
        llm.note_degradation("results_reader", exc)
        narrative = (
            "## Conclusões\n\n"
            "> ⚠️ **O modelo não respondeu nesta execução.** A secção interpretativa "
            "não foi gerada. Os factos abaixo são calculados em código e mantêm-se "
            "válidos — a leitura tem de ser feita por um humano.\n"
        )

    return f"{header}\n{narrative}\n\n---\n\n{render_facts(facts)}\n", facts
