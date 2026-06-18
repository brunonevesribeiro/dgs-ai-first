# Exercício 2.2 — Item 1: Conversão de Plan em Tasks Atômicas (Spec Driven Development)

## Objetivo

Demonstrar o uso do Claude Code para converter um `plan.md` de alto nível em tasks atômicas e implementáveis, seguindo o modelo de **Spec Driven Development**.

---

## Contexto fornecido ao modelo

**Repositório:** db1/novatech-assistant  
**Stack:** TypeScript, Azure Functions v4, Zod, pino  
**Endpoint alvo:** `POST /api/query`

O plan.md descrevia uma Azure Function que:
1. Recebe pergunta via POST
2. Gera embedding via Azure OpenAI
3. Busca top-5 chunks no Azure AI Search
4. Monta prompt respeitando context budget (ADR-0002)
5. Envia ao GPT-4o e retorna resposta com `source_document`

---

## Prompt utilizado

```
Você é um desenvolvedor sênior convertendo um plan.md em tasks 
atômicas para o modelo Spec Driven Development.

[contexto do projeto + plan.md completo]

Para cada task, defina:
- ID (TASK-001, TASK-002, etc.)
- Título
- Descrição detalhada
- Critérios de aceite verificáveis (não vagos)
- Dependências (quais tasks precisam estar prontas antes)
- Estimativa: P (< 2h), M (2-4h), G (> 4h)
- Arquivo(s) que serão criados/modificados

Gere tasks verdadeiramente atômicas — cada uma deve poder ser 
implementada e testada sem depender de outra não concluída,
exceto dependências explícitas.
```

---

## Tasks geradas

O modelo produziu 10 tasks atômicas documentadas em [tasks.md](tasks.md):

| ID | Título | Estimativa | Dependências |
|----|--------|------------|--------------|
| TASK-001 | Schemas Zod de entrada e saída | P | — |
| TASK-002 | Retry com exponential backoff | P | — |
| TASK-003 | Logger estruturado (pino) | P | — |
| TASK-004 | Loader do system prompt | P | — |
| TASK-005 | Cliente de embeddings (Azure OpenAI) | M | 002, 003 |
| TASK-006 | Cliente Azure AI Search | M | 001, 002, 003 |
| TASK-007 | Assembler de contexto (context budget) | M | 001 |
| TASK-008 | Cliente de completion (GPT-4o) | M | 002, 003 |
| TASK-009 | Query handler (orquestrador) | M | 001, 003–008 |
| TASK-010 | Azure Function HTTP trigger | P | 001, 003, 009 |

---

## O que o modelo fez bem

### Decomposição por responsabilidade única
Cada task toca exatamente uma camada: schema, infraestrutura transversal (retry, logger), clientes externos, lógica de negócio (assembler), orquestração e wiring HTTP. Nenhuma task mistura duas dessas camadas.

### Critérios de aceite verificáveis
O modelo evitou critérios vagos como "deve funcionar corretamente" e gerou asserções precisas:
- valores de entrada e saída concretos (`question: "a".repeat(501)` lança `ZodError`)
- comportamento em cenários de erro (HTTP 429 → retry 3x; HTTP 400 → sem retry)
- verificações estruturais (campo `service` no JSON de log, `requestId` em todos os logs)

### Injetabilidade para testabilidade
A TASK-009 especifica que todos os clientes devem ser injetáveis via parâmetro, com defaults para os módulos reais — decisão que viabiliza testes unitários sem chamadas reais à Azure.

### Grafo de dependências explícito
O modelo identificou o **caminho crítico** (001 → 007 → 009 → 010) e o conjunto paralelizável (001–004 simultâneas), útil para planejamento de sprint.

---

## Decisões técnicas preservadas do plan.md

| Decisão | Origem | Como aparece nas tasks |
|---------|--------|------------------------|
| Context budget ~4K system + ~8K chunks | ADR-0002 | TASK-007: budget em tokens com fórmula `chars / 4` |
| Priorizar documento mais recente em conflito | ADR-0003 | TASK-006: dedup por `source_document` + `effective_date` |
| System prompt versionado em arquivo | plan.md | TASK-004: loader com hash SHA-256 para rastreabilidade |
| Retry com exponential backoff | plan.md | TASK-002: utilitário genérico; consumido por 005, 006, 008 |

---

## Aprendizados do exercício

**Atomicidade real exige separar infraestrutura de negócio.** O retry e o logger foram extraídos como tasks independentes (002 e 003) em vez de acoplados aos clientes, o que permite testá-los isoladamente e reutilizá-los em outras partes do projeto.

**Critérios de aceite são o artefato mais valioso.** A descrição pode ser vaga; os critérios de aceite é que tornam a task implementável sem ambiguidade. O modelo foi mais rigoroso neles do que em descrições narrativas.

**Injeção de dependência deve ser decidida na spec, não na implementação.** Definir na TASK-009 que os clientes são injetáveis evita refatoração posterior quando os testes unitários forem escritos.
