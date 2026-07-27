#!/usr/bin/env python3
"""
Estatística da campanha — determinística, em Python, NUNCA no LLM.

Regra do pipeline: um LLM não faz aritmética, faz narrativa. Todos os números
que aparecem no relatório (CVR, lift, intervalos de confiança, valores-p) são
calculados aqui e entregues ao modelo já prontos. O modelo prioriza e escreve;
se inventasse uma percentagem, a validação apanhava-a por não constar da tabela.

Só stdlib — `math.erfc` chega para a normal acumulada a esta escala.
"""

import math
from collections import defaultdict


def cvr(clicks, views):
    return (clicks / views) if views else 0.0


def wilson_ci(clicks, views, z=1.96):
    """Intervalo de confiança de 95% para uma proporção (Wilson).

    Preferido ao intervalo normal porque aqui há células com poucos cliques
    (cr_E em desktop tem 0/75) — onde o intervalo normal simplesmente colapsa.
    """
    if not views:
        return (0.0, 0.0)
    p = clicks / views
    denom = 1 + z ** 2 / views
    centre = p + z ** 2 / (2 * views)
    margin = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * views)) / views)
    return ((centre - margin) / denom, (centre + margin) / denom)


def two_proportion_z(clicks_a, views_a, clicks_b, views_b):
    """Teste z de duas proporções. Devolve z, valor-p (bilateral) e lift relativo."""
    if not views_a or not views_b:
        return {"z": 0.0, "p_value": 1.0, "lift": 0.0, "significant": False}

    p_a, p_b = clicks_a / views_a, clicks_b / views_b
    pooled = (clicks_a + clicks_b) / (views_a + views_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / views_a + 1 / views_b))
    if se == 0:
        return {"z": 0.0, "p_value": 1.0, "lift": 0.0, "significant": False}

    z = (p_a - p_b) / se
    p_value = math.erfc(abs(z) / math.sqrt(2))  # bilateral
    return {
        "z": round(z, 3),
        # Sem arredondar a poucas casas: um p de 2,7e-07 arredondado a cinco
        # casas vira "0.0", que se lê como impossível em vez de muito improvável.
        "p_value": float(f"{p_value:.3g}"),
        "lift": round((p_a / p_b - 1), 4) if p_b else 0.0,
        "significant": p_value < 0.05,
    }


def aggregate(views, clicks, key):
    """Agrega vistas e cliques por uma propriedade e devolve CVR ordenado.

    `views`/`clicks` são listas de dicionários de propriedades. `key` pode ser
    uma string (uma propriedade) ou um tuplo (cruzamento de duas).
    """
    def bucket(row):
        if isinstance(key, tuple):
            return tuple(row.get(k) for k in key)
        return row.get(key)

    v, c = defaultdict(int), defaultdict(int)
    for row in views:
        v[bucket(row)] += 1
    for row in clicks:
        c[bucket(row)] += 1

    out = []
    for name in v:
        low, high = wilson_ci(c[name], v[name])
        out.append({
            "key": name,
            "views": v[name],
            "clicks": c[name],
            "cvr": round(cvr(c[name], v[name]), 5),
            "cvr_pct": round(100 * cvr(c[name], v[name]), 2),
            "ci95_low_pct": round(100 * low, 2),
            "ci95_high_pct": round(100 * high, 2),
        })
    return sorted(out, key=lambda r: -r["cvr"])


def one_vs_rest(rows, target_key):
    """Compara uma linha agregada contra a soma de todas as outras."""
    target = next((r for r in rows if r["key"] == target_key), None)
    if not target:
        return None
    rest_c = sum(r["clicks"] for r in rows if r["key"] != target_key)
    rest_v = sum(r["views"] for r in rows if r["key"] != target_key)
    result = two_proportion_z(target["clicks"], target["views"], rest_c, rest_v)
    result["baseline_cvr_pct"] = round(100 * cvr(rest_c, rest_v), 2)
    return result


def spearman(rank_a, rank_b):
    """Correlação de postos entre duas ordenações dos mesmos itens.

    É isto que testa a tese central: a ordem dos temas por volume de feedback
    corresponde à ordem dos criativos por CVR?
    """
    common = [k for k in rank_a if k in rank_b]
    n = len(common)
    if n < 3:
        return {"rho": None, "n": n}
    pos_a = {k: i for i, k in enumerate(rank_a) if k in common}
    pos_b = {k: i for i, k in enumerate(rank_b) if k in common}
    d2 = sum((pos_a[k] - pos_b[k]) ** 2 for k in common)
    rho = 1 - (6 * d2) / (n * (n ** 2 - 1))
    return {"rho": round(rho, 3), "n": n}
