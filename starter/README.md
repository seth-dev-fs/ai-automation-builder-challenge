# Starter — LP de captura de feedback

Ponto de partida para a captura (passo 1). Não és obrigado a usá-lo — se preferires
React/Vite ou outra coisa, à vontade.

## Configurar

Em [index.html](./index.html) substitui `__POSTHOG_PROJECT_KEY__` pela tua
*Project API Key* (`phc_...`). Se estiveres em US cloud, troca também o
`api_host` para `https://us.i.posthog.com`.

> A Project API Key (`phc_`) é de escrita e **pode** ficar exposta no cliente —
> é assim que o PostHog funciona no browser. Não confundas com a Personal API Key
> (`phx_`), essa **nunca** vai para o cliente.

## Correr localmente

```bash
cd starter && python3 -m http.server 8000
```

## Hospedar (GitHub Pages)

Já vem um workflow ([../.github/workflows/pages.yml](../.github/workflows/pages.yml))
que publica esta pasta. Ativa em *Settings → Pages → Source: GitHub Actions* e faz
push. A LP fica em `https://<user>.github.io/<repo>/`.

## O que decides tu

O formulário já dispara `feedback_submitted` com `feedback_type` e `text`. **Que
outras propriedades enviar é contigo** — pensa no que o teu agente de análise vai
precisar a jusante.
