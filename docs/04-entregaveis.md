# Entregáveis Esperados

Entregar um **documento técnico** (formato livre: PDF, Markdown, Notion, repositório GitHub com README bem estruturado, etc.) contendo as 6 seções abaixo.

---

## 1. Arquitetura da Solução

- Desenho ou descrição detalhada da arquitetura completa
- Camadas da aplicação (entrada de dados, processamento, LLM, banco de dados, canais de comunicação)
- Fluxo de dados entre os componentes
- Onde cada fase do funil (Captação, Enriquecimento, Engajamento, Follow-up) se encaixa

---

## 2. Stack Tecnológico Justificado

Liste e justifique cada tecnologia escolhida:

- Modelo de LLM e por quê
- Framework de agente (LangChain, CrewAI, Agno, SDK nativo, etc.)
- Banco de dados e modelo de dados
- Ferramenta de orquestração/workflow (se aplicável)
- Canal de comunicação e integração usada
- Infraestrutura de deploy

---

## 3. Réguas de Comunicação

- Descreva detalhadamente o fluxo de mensagens das duas réguas (pré e pós-evento)
- Inclua as regras de negócio definidas (gatilhos, condições, timing)
- Apresente ao menos **um exemplo de mensagem personalizada** para cada régua, demonstrando uso do enriquecimento de dados

---

## 4. Estratégia de Dados e Personalização

- Como os dados dos leads serão coletados, armazenados e utilizados?
- Como o enriquecimento funciona na prática? Quais fontes? Como o dado enriquecido é usado pelo agente?
- Como você garante conformidade com **LGPD** no tratamento dos dados dos participantes?

---

## 5. Decisões Estratégicas e Racional

- Quais foram as três principais decisões técnicas ou de produto tomadas?
- Quais alternativas foram consideradas e por que foram descartadas?
- Que referências de mercado, cases ou frameworks embasaram as escolhas?

---

## 6. Plano de Execução (Primeiros 5 dias)

- Assuma que você começa amanhã: descreva os primeiros passos técnicos
- O que você provisionaria/configuraria primeiro e por quê?
- Qual fase do funil você atacaria primeiro?
