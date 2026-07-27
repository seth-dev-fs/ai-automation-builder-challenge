#!/usr/bin/env python3
"""
Regista no PostHog os criativos que um humano aprovou.

Corre em `.github/workflows/publish.yml`, ao merge do Pull Request. Lê
`creatives/index.json`, envia um `creative_approved` por criativo e diz quem
carregou no botão.

O objetivo não é decorar o dashboard: é conseguir responder, daqui a dois meses,
a "de tudo o que a automação propôs, quanto é que passou no crivo humano?".
Se a taxa de aprovação for alta, pode-se alargar a autonomia do pipeline. Se for
baixa, o problema está nos prompts e a automação está a criar trabalho em vez de
o poupar. Sem esta medição, é opinião.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import posthog_io  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "creatives", "index.json")


def main():
    if not os.path.exists(INDEX):
        print("Sem creatives/index.json — nada a registar.")
        return

    with open(INDEX, encoding="utf-8") as handle:
        index = json.load(handle)

    approved_by = os.environ.get("APPROVED_BY", "desconhecido")
    events = [
        {
            "event": "creative_approved",
            "distinct_id": c["creative_id"],
            "properties": {
                "creative_id": c["creative_id"],
                "angle_type": c["angle_type"],
                "theme": c["theme"],
                "headline": c["headline"],
                "utm_campaign": c["utm_campaign"],
                "utm_content": c["creative_id"],
                "priority_score": c["priority_score"],
                "generated_by": c["generated_by"],
                "was_incomplete": c["incomplete"],
                "approved_by": approved_by,
            },
        }
        for c in index.get("creatives", [])
    ]

    sent = posthog_io.capture(events)
    print(f"{sent}/{len(events)} eventos creative_approved enviados "
          f"(aprovados por {approved_by}).")


if __name__ == "__main__":
    main()
