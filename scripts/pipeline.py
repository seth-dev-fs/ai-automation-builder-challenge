#!/usr/bin/env python3
"""
Orquestrador do ciclo. Corre no GitHub Actions (`.github/workflows/generate.yml`).

    PostHog ──▶ Agente 1 (análise)  ──▶ analysis/feedback_clusters.json
                     │                   └─▶ PostHog: feedback_classified
                     ▼
                Agente 3 (resultados) ──▶ analysis/results_report.md
                     │
                     ▼
                Agente 2 (criativo)   ──▶ creatives/*.md  (draft, via Pull Request)
                                          └─▶ PostHog: creative_generated

Modos:
    python scripts/pipeline.py                  # completo, contra o PostHog
    python scripts/pipeline.py --offline        # lê data/seed_events.ndjson, sem rede
    python scripts/pipeline.py --no-writeback   # não escreve eventos no PostHog

O modo `--offline` existe para se poder iterar no pipeline sem gastar quota de
API nem depender de a rede estar boa — corre em segundos e usa exatamente os
mesmos dados. Só o transporte muda.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llm                                  # noqa: E402
import posthog_io                           # noqa: E402
from agents import creative_writer, feedback_analyst, results_reader  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS = os.path.join(ROOT, "analysis")
CREATIVES = os.path.join(ROOT, "creatives")
SEED = os.path.join(ROOT, "data", "seed_events.ndjson")


def load_offline():
    """Mesma forma de dados que o PostHog devolveria, a partir do ficheiro semente."""
    feedback, views, clicks = [], [], []
    with open(SEED, encoding="utf-8") as handle:
        for n, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            props = event["properties"]
            if event["event"] == "feedback_submitted":
                feedback.append({
                    "ref": f"offline-{n:05d}",
                    "feedback_type": props.get("feedback_type"),
                    "text": props.get("text"),
                    "channel": props.get("channel"),
                    "timestamp": event.get("timestamp"),
                })
            elif event["event"] in ("creative_view", "cta_click"):
                row = {k: props.get(k) for k in
                       ("creative_id", "angle_type", "theme", "headline",
                        "utm_source", "device_type", "utm_campaign")}
                (views if event["event"] == "creative_view" else clicks).append(row)
    return feedback, views, clicks


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    print(f"  escrito {os.path.relpath(path, ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline dos três agentes.")
    parser.add_argument("--offline", action="store_true",
                        help="usar data/seed_events.ndjson em vez do PostHog")
    parser.add_argument("--no-writeback", action="store_true",
                        help="não escrever eventos de volta no PostHog")
    args = parser.parse_args()

    started = time.time()
    print(f"Pipeline · modelo {llm.MODEL} · "
          f"fonte {'ficheiro semente' if args.offline else 'PostHog'}\n")

    # ── Leitura ──────────────────────────────────────────────────────────────
    if args.offline:
        feedback, views, clicks = load_offline()
    else:
        feedback = posthog_io.fetch_feedback()
        views, clicks = posthog_io.fetch_campaign()
    print(f"Lidos {len(feedback)} feedbacks, {len(views)} impressões, "
          f"{len(clicks)} cliques.\n")

    if not feedback:
        sys.exit("Sem feedback para analisar — o pipeline não tem input. Aborta.")
    if not views:
        sys.exit("Sem eventos de campanha — não há resultados para ler. Aborta.")

    campaign_themes = {row.get("theme") for row in views}

    # ── Agente 1 ─────────────────────────────────────────────────────────────
    clusters_doc, classified = feedback_analyst.run(feedback, campaign_themes)
    write(os.path.join(ANALYSIS, "feedback_clusters.json"),
          json.dumps(clusters_doc, ensure_ascii=False, indent=2) + "\n")

    written_back = 0
    if not args.no_writeback and not args.offline:
        written_back += posthog_io.capture(
            feedback_analyst.to_posthog_events(classified)
        )
        print(f"  write-back: {written_back} eventos feedback_classified")

    # ── Agente 3 ─────────────────────────────────────────────────────────────
    report, facts = results_reader.run(views, clicks, clusters_doc["clusters"])
    write(os.path.join(ANALYSIS, "results_report.md"), report)
    write(os.path.join(ANALYSIS, "campaign_facts.json"),
          json.dumps(facts, ensure_ascii=False, indent=2) + "\n")

    # ── Agente 2 ─────────────────────────────────────────────────────────────
    top = facts["by_creative"][0]
    facts_summary = (
        f"Na campanha anterior, o ângulo pain_resolution converteu a "
        f"{facts['by_angle'][0]['cvr_pct']}% e o praise_amplification a "
        f"{facts['by_angle'][-1]['cvr_pct']}%. O melhor criativo foi {top['key']} "
        f"(\"{top['headline']}\", tema {top['theme']}), com {top['cvr_pct']}%."
    )
    creatives, ranked = creative_writer.run(
        clusters_doc["clusters"], facts["by_theme"], facts_summary
    )

    for creative in creatives:
        write(os.path.join(CREATIVES, f"{creative['creative_id']}.md"),
              creative_writer.to_markdown(creative))

    write(os.path.join(CREATIVES, "index.json"), json.dumps({
        "campaign": creative_writer.CAMPAIGN,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "draft — pendente de aprovação humana no Pull Request",
        "priority_ranking": [
            {
                "theme": c["theme"],
                "angle_type": c["angle_type"],
                "priority_score": c["priority_score"],
                "breakdown": c["priority_breakdown"],
                "feedback_signal": c["feedback_signal"],
                "historical_cvr_pct": c["historical_cvr_pct"],
            }
            for c in ranked
        ],
        "creatives": [
            {k: v for k, v in c.items() if k != "evidence"} for c in creatives
        ],
    }, ensure_ascii=False, indent=2) + "\n")

    if not args.no_writeback and not args.offline:
        written_back += posthog_io.capture(
            creative_writer.to_posthog_events(creatives)
        )

    # ── Registo da execução ──────────────────────────────────────────────────
    run_log = {
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - started, 1),
        "mode": "offline" if args.offline else "posthog",
        "model": llm.MODEL,
        "inputs": {"feedback": len(feedback), "views": len(views), "clicks": len(clicks)},
        "outputs": {
            "clusters": len(clusters_doc["clusters"]),
            "creatives": len(creatives),
            "posthog_events_written": written_back,
        },
        "llm": {
            "attempts": llm.TRACE["attempts"],
            "schema_rejections": llm.TRACE["schema_rejections"],
            "transport_errors": llm.TRACE["transport_errors"],
            "calls": llm.TRACE["calls"],
        },
        "degraded": llm.is_degraded(),
        "degradations": llm.TRACE["degradations"],
    }
    write(os.path.join(ANALYSIS, "run_log.json"),
          json.dumps(run_log, ensure_ascii=False, indent=2) + "\n")

    print(f"\nConcluído em {run_log['duration_seconds']}s · "
          f"{llm.TRACE['attempts']} chamadas ao modelo · "
          f"{llm.TRACE['schema_rejections']} rejeições de contrato")

    if llm.is_degraded():
        print("\n⚠️  Execução DEGRADADA — parte do output veio do caminho "
              "determinístico. Ver analysis/run_log.json.")
        # Sai a 0 de propósito: os resultados degradados são úteis e devem ser
        # commitados. O aviso vai no Pull Request, para o humano decidir.

    # Ficheiro de sinalização lido pelo workflow para etiquetar o Pull Request.
    with open(os.path.join(ROOT, ".pipeline_status"), "w", encoding="utf-8") as handle:
        handle.write("degraded" if llm.is_degraded() else "ok")


if __name__ == "__main__":
    main()
