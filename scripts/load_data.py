#!/usr/bin/env python3
"""
Injeta os dados semeados do desafio no TEU projeto PostHog.

Lê `data/seed_events.ndjson` (feedback de clientes + resultados de uma campanha
de anúncios anterior) e envia tudo para o PostHog via Capture API, preservando os
timestamps originais (os eventos ficam distribuídos pelos últimos ~30 dias).

Uso:
  export POSTHOG_PROJECT_KEY=phc_a_tua_project_key
  python3 scripts/load_data.py                       # EU cloud por defeito
  python3 scripts/load_data.py --host https://us.i.posthog.com
  python3 scripts/load_data.py --dry-run             # conta e valida, não envia

Só stdlib. Corre uma vez após criares o projeto. Correr duas vezes duplica os
eventos - se te enganares, cria um projeto novo (é mais limpo).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BATCH_SIZE = 100
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "seed_events.ndjson")


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def post_batch(host, api_key, batch):
    payload = json.dumps({"api_key": api_key, "batch": batch}).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/batch/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    p = argparse.ArgumentParser(description="Injeta os dados semeados no teu PostHog.")
    p.add_argument("--host", default=os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com"))
    p.add_argument("--api-key", default=os.environ.get("POSTHOG_PROJECT_KEY"),
                   help="Project API Key (phc_...). Ou define POSTHOG_PROJECT_KEY.")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    events = load_events(DATA_FILE)
    counts = {}
    for e in events:
        counts[e["event"]] = counts.get(e["event"], 0) + 1
    print("Eventos a injetar (%d no total):" % len(events))
    for name in sorted(counts):
        print("  %-20s %d" % (name, counts[name]))

    if args.dry_run:
        print("\nDry run - nada enviado.")
        return

    if not args.api_key:
        print("\nERRO: falta a Project API Key. Define POSTHOG_PROJECT_KEY ou usa --api-key.")
        sys.exit(2)

    print("\nA enviar para %s ..." % args.host)
    sent = 0
    for i in range(0, len(events), BATCH_SIZE):
        chunk = events[i:i + BATCH_SIZE]
        try:
            post_batch(args.host, args.api_key, chunk)
            sent += len(chunk)
            print("  %d/%d" % (sent, len(events)), end="\r", flush=True)
        except urllib.error.HTTPError as e:
            print("\nHTTP %d: %s" % (e.code, e.read().decode()[:300]))
            sys.exit(1)
        except urllib.error.URLError as e:
            print("\nErro de rede: %s" % e)
            sys.exit(1)
    print("  %d/%d enviados. Feito." % (sent, len(events)))
    print("\nConfirma no PostHog (Activity) que aparecem os eventos. Podem demorar "
          "1-2 min a serem processados.")


if __name__ == "__main__":
    main()
