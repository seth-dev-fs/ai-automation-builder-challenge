# Decisões

Este é o texto que o enunciado pede. Está organizado pelas perguntas que fazem.

## O que construí

Um ciclo que fecha: a página recolhe feedback → o PostHog guarda-o → três
agentes correm no GitHub Actions (classificam, lêem os resultados da campanha
anterior, escrevem criativos novos) → os resultados voltam ao repositório e ao
PostHog → o dashboard mostra as duas metades lado a lado.

O que me interessou mais não foi ligar as peças, foi decidir **o que cada peça
tem o direito de decidir**.

## Ferramentas, e porquê

Mantive o caminho preparado — PostHog, GitHub Actions, GitHub Pages. Não por
inércia: cada peça faz uma coisa que eu precisava mesmo. O PostHog porque queria
escrever de volta, não só ler. O Actions porque o ponto do exercício é o pipeline
não viver na minha máquina, e porque é onde já existe um mecanismo de aprovação
humana que eu não tinha de inventar — o Pull Request. O Pages porque a página é
estática e não vale a pena mais nada.

**LLM: Gemini 2.5 Flash.** Precisava de output estruturado fiável e barato, e
faço 10 chamadas por execução. Custa cêntimos. É também o modelo que já corro em
produção noutro projeto meu, portanto conheço-lhe os defeitos — incluindo um que
custa uma tarde a descobrir: com `responseSchema`, é preciso pôr
`thinkingConfig.thinkingBudget = 0`, senão o raciocínio come o orçamento de
tokens e o JSON vem truncado a meio.

**Zero dependências.** O pipeline é só a biblioteca padrão do Python — `urllib`
para as três APIs. O `requirements.txt` está vazio de propósito. Um SDK a mais é
uma versão a partir no CI daqui a três meses, e não me dava nada que eu precise.

## Onde está o humano

Em dois sítios, e a distinção entre eles é a decisão de que mais gosto neste
trabalho:

| O que sai | Para onde vai | Porquê |
|---|---|---|
| `analysis/` | commit direto em `main` | São factos. Contagens, CVRs, valores-p, calculados em código e reproduzíveis. Não faz sentido pedir a alguém que aprove uma soma. |
| `creatives/` | **Pull Request** | É texto escrito por um modelo que vai aparecer em nome da empresa a pessoas reais. O merge é a assinatura. |

Todos os criativos nascem com `status: draft`. O PR traz uma checklist curta
(o copy diz a verdade? as citações sustentam mesmo o ângulo? nenhuma promessa
que não consigamos cumprir?) e, se a execução tiver sido degradada, sai com a
etiqueta `needs-human-review`.

Ao fazer merge, um segundo workflow envia `creative_approved` para o PostHog.
Não é decoração: passa a haver forma de responder, daqui a dois meses, a "de
tudo o que a automação propôs, quanto passou no crivo humano?". Se a taxa for
alta, alarga-se a autonomia do pipeline. Se for baixa, o problema está nos
prompts e a automação está a dar trabalho em vez de o poupar. Sem medir isso, é
opinião.

## Como lido com output mau do LLM

Parti do princípio de que o modelo vai falhar — não como hipótese remota, como
caso normal ao fim de umas centenas de chamadas. Quatro camadas:

**1. Restringir na origem.** `responseMimeType: application/json` +
`responseSchema` com enums fechados. O agente de análise não pode inventar um
tema: escolhe de uma lista de nove. Sem isso, ficava com 150 clusters de um
elemento e nada para cruzar.

**2. Validar à saída, com regras de negócio.** O schema garante a forma, não a
substância. As minhas validações apanham o resto: `urgency` fora de 1–5, headline
acima de 40 caracteres (o limite real das plataformas), copy com percentagens
inventadas ou "o melhor do mercado", placeholders por preencher. E a mais útil
de todas — **evidência verificável**: cada criativo tem de citar quais os
feedbacks concretos que sustentam o ângulo, por índice, e os índices são
conferidos contra a lista real. É a diferença entre um anúncio inspirado nos
dados e um anúncio que diz que foi.

**3. Retentar com o erro em mãos.** Quando a validação rejeita, o motivo concreto
volta ao modelo no retry: *"devolveste 24 itens, eram esperados 25"*. É bastante
mais eficaz do que repetir o mesmo pedido à espera de outro resultado.

**4. Degradar, nunca render.** Ao fim de três tentativas, o agente passa a um
classificador determinístico por palavras-chave. Pior qualidade, mas previsível e
auditável — e assinalado em toda a linha: `degraded: true` no `run_log.json`, os
criativos marcados `incomplete`, o PR etiquetado. A regra que segui foi: **um
mecanismo de segurança nunca se desliga sozinho.** A tentação é escrever
`if not resposta: return` e seguir em frente; nesse momento o pipeline passa a
entregar silêncio com ar de sucesso.

Há uma quinta coisa, que não é uma camada mas é o que mais reduz o risco:
**o modelo não faz aritmética.** Todos os números do relatório — CVR, intervalos
de Wilson, testes z, a correlação de postos — são calculados em `metrics.py` e
entregues já prontos. Ao modelo pede-se o que ele faz melhor do que uma fórmula:
dizer o que aquilo significa. Se inventar uma percentagem, ela contradiz a tabela
imediatamente acima, escrita por código.

## O que os dados dizem

O padrão que encontrei — e que o agente de leitura também encontra sozinho — é
que **a ordem dos temas por volume de feedback reproduz a ordem dos criativos por
taxa de conversão**. Dentro dos anúncios que resolvem uma dor, a correspondência
é perfeita: `agendamento` é a queixa nº1 e `cr_A` é o melhor criativo (8,42%);
`integrações` é a queixa menos frequente e `cr_F` é o pior (1,67%). Spearman
ρ = 1,0 dentro de `pain_resolution`, ρ = 0,83 no conjunto.

Isto é a tese que justifica o pipeline existir: o feedback não serve só para
saber o que arranjar, prevê o que vai converter.

Por cima disso, resolver dores bate amplificar elogios (4,71% vs 2,96%, p = 0,04)
e há uma dor com queixas graves que a campanha anterior nunca abordou.

E há um resultado que **decidi não usar**: mobile converte melhor do que desktop
(4,17% vs 2,92%), mas com p = 0,21 aquilo é ruído. Pedi explicitamente ao agente
de leitura que apontasse uma diferença que parece padrão e não passa no teste —
e ele apanhou-a, com a recomendação de não agir sobre ela.
Distinguir as duas coisas é a diferença entre reafectar orçamento com fundamento
e reafectá-lo por acaso.

## Onde a IA me falhou

Três casos concretos, desta sessão:

**O primeiro teste que corri foi o de falha, e ainda bem.** Corri o pipeline sem
chave de LLM para ver a degradação funcionar. Ficou pendurado dois minutos: o
código tratava "a chave não existe" como erro transitório e fazia backoff
exponencial em cima de um erro que nunca ia resolver-se. Esperar 30 segundos não
faz aparecer uma chave. Se só tivesse testado o caminho feliz, isto aparecia em
produção, num dia em que o secret expirasse.

**A primeira fórmula de prioridade estava errada, e parecia bem.** Dava peso à
urgência sem exigir volume mínimo — e escolheu um tema com três queixas muito
graves à frente de um com quinze moderadas. A fórmula não tinha erro nenhum de
código; tinha um erro de juízo. Acrescentei um limiar de cinco menções, com o
raciocínio escrito no sítio: um tema urgente com pouco volume é um problema de
suporte, não é um anúncio.

**O modelo pequeno não sabe contar até quarenta.** Ao mudar para o
`gemini-2.5-flash-lite` — para fugir a limites de quota — os criativos começaram
a ser rejeitados pela minha própria validação: *"headline tem 45 caracteres, o
limite é 40"*, três vezes seguidas, até esgotar as tentativas. A validação
estava certa, o modelo é que conta caracteres mal. A correção não foi baixar a
guarda: passei a **pedir 35 e a validar a 40**. A folga é para ele errar sem que
o resultado deixe de servir. Na mesma execução, a validação apanhou também um
copy com uma promessa absoluta — e nessa o retry resolveu à primeira.

**Um secret vazio devolve verde.** A meio, uma chave foi para o GitHub como
string vazia (o comando que a extraía falhou em silêncio). O pipeline correu,
degradou os oito agentes para o caminho determinístico, commitou os resultados e
o Actions deu ✅. Ou seja: o mecanismo de degradação funcionou tão bem que
escondeu uma avaria de configuração. Acrescentei um passo no workflow que falha
se algum secret vier vazio — degradar é para quando o modelo falha, não para
quando falta configuração.

**Dirigir bem é sobretudo saber o que verificar.** A parte que eu não posso
delegar é decidir o que conta como estar feito. Por isso é que o caminho de falha
foi testado antes do caminho de sucesso, e é por isso que os números do relatório
não passam pelo modelo.

**E uma que só se vê nos dados.** Depois de algumas execuções, o dashboard
mostrava 754 classificações para 151 feedbacks — cada execução reclassificava
tudo e voltava a escrever. Pior: o mesmo feedback aparecia em dois temas
diferentes, porque o modelo nem sempre decide o mesmo. Corrigi nas duas pontas,
porque uma só não chegava: o write-back passou a usar um `uuid` determinístico
(o PostHog descarta reenvios), e as queries do dashboard passaram a tirar **uma
linha por feedback com a classificação mais recente**, para não dependerem de os
dados históricos estarem limpos. Nenhum teste apanharia isto — só olhar para o
número e achá-lo estranho.

## O que cortei

Não gerei as imagens dos criativos, só os prompts — o enunciado diz que é
opcional e o tempo era melhor gasto na validação. Não escrevi testes unitários;
o que fiz em vez disso foi o modo `--offline`, que corre o pipeline inteiro
contra o ficheiro semente em segundos, sem rede nem quota, e que usei em cada
alteração. Não é a mesma coisa que testes — é o que coube.

## Com mais tempo

1. **Fechar o ciclo até ao fim.** Neste momento os criativos novos param no
   repositório à espera de alguém os publicar. O passo seguinte é empurrá-los
   para a plataforma de anúncios com as UTMs já definidas, e a ronda seguinte
   passa a ler o resultado dos criativos que ela própria gerou. As propriedades
   já estão preparadas para isso: os criativos novos usam exatamente o mesmo
   esquema da campanha anterior, portanto o dashboard mede-os sem ser alterado.

2. **Testar a tese em vez de a assumir.** A correlação que encontrei tem n = 6.
   É forte mas é pequena. Com mais rondas, dava para reservar uma fatia do
   orçamento a um tema de baixo volume de propósito, para perceber se a relação
   se mantém ou se estou a confirmar uma coincidência.

3. **Avaliação automática dos prompts.** Um conjunto de feedbacks com
   classificação conhecida, a correr em cada alteração aos prompts, para saber se
   uma mudança melhorou ou piorou a classificação. Sem isso, mexer num prompt é
   um ato de fé.

4. **Custo por criativo aprovado.** Já registo os tokens de cada chamada no
   `run_log.json`. Falta ligá-los à taxa de aprovação humana, que é a única
   métrica que responde à pergunta que interessa: isto vale o que custa?
