# Estratégia de Skills — NovaTech Assistant

> Gerado por Claude Sonnet 4.6 em 2026-06-18 como resposta ao Exercício 2.3 do cenário NovaTech Assistant.

## Foundation — Convenções transversais

| Slug | Descrição (frase-ativação) | Cria | Consome | Freq. |
|---|---|---|---|---|
| `typescript-conventions` | "Gere código TypeScript seguindo os padrões strict do projeto (naming, imports, tipos, null safety)" | Tech Lead | Dev Pleno, Dev Sênior — Copilot + Claude Code | Alta |
| `error-handling` | "Implemente tratamento de erros usando os custom errors e padrões de propagação do projeto" | Tech Lead | Dev Pleno, Dev Sênior, QA — Copilot + Claude Code | Alta |
| `project-structure` | "Organize novos arquivos respeitando a estrutura de módulos, bounded contexts e convenções de pasta do repositório" | Tech Lead | Dev Pleno, Dev Sênior — Claude Code | Média |

---

## Domain — Padrões por tecnologia

| Slug | Descrição (frase-ativação) | Cria | Consome | Freq. |
|---|---|---|---|---|
| `azure-functions-endpoint` | "Crie um Azure Functions v4 HTTP trigger com validação Zod, middleware de auth e response builder padrão do projeto" | Dev Sênior | Dev Pleno, Dev Sênior — Copilot + Claude Code | Alta |
| `azure-ai-search-integration` | "Integre com Azure AI Search usando o padrão do projeto: vector search, 5 chunks, metadado de vigência e score mínimo" | Dev Sênior | Dev Pleno, Dev Sênior — Copilot + Claude Code | Alta |
| `azure-openai-completion` | "Chame Azure OpenAI seguindo o context budget do projeto (4K system + 8K chunks + histórico 3 turnos)" | Tech Lead | Dev Pleno, Dev Sênior — Copilot + Claude Code | Alta |
| `react-components` | "Crie componentes React tipados com as convenções de props, estado e Adaptive Cards do painel web" | Dev Sênior | Dev Pleno — Copilot + Claude Code | Média |
| `testing-patterns` | "Estruture testes Vitest separando unit/integration/e2e e usando os fixtures compartilhados do projeto" | QA + Tech Lead | Dev Pleno, Dev Sênior, QA — Copilot + Claude Code | Alta |

---

## Artifact — Receitas completas de geração

| Slug | Descrição (frase-ativação) | Cria | Consome | Freq. |
|---|---|---|---|---|
| `create-rag-endpoint` | "Gere um endpoint RAG completo: handler + validator + search service + completion service + testes de integração" | Tech Lead | Dev Pleno, Dev Sênior — Claude Code | Alta |
| `create-integration-test` | "Gere testes de integração para um endpoint usando msw para mock de APIs externas e fixtures do projeto" | QA + Tech Lead | Dev Pleno, QA — Copilot + Claude Code | Alta |
| `create-react-card` | "Gere um componente de card React com Adaptive Card correspondente para o painel web e bot do Teams" | Dev Sênior | Dev Pleno — Claude Code | Média |
| `create-endpoint-docs` | "Gere documentação técnica de endpoint no formato padrão do projeto (contrato, exemplos, erros, guardrails)" | Tech Lead | Dev Pleno, Product Specialist — Claude Code | Média |
| `create-sdd-spec` | "Gere os 3 artefatos SDD (requirements + plan + tasks) para um módulo novo a partir de um briefing de produto" | Tech Lead + PS | Product Specialist, Tech Lead, Dev Sênior — Claude Code | Baixa |

---

## Mapa de dependências

```
Foundation (base para tudo)
    └── typescript-conventions
    └── error-handling
    └── project-structure

Domain (combina foundations)
    └── azure-functions-endpoint   ← usa typescript-conventions + error-handling
    └── azure-ai-search-integration ← usa error-handling
    └── azure-openai-completion     ← usa error-handling
    └── testing-patterns            ← usa project-structure

Artifact (orquestra domain + foundation)
    └── create-rag-endpoint        ← azure-functions-endpoint + azure-ai-search + azure-openai
    └── create-integration-test    ← testing-patterns + azure-functions-endpoint
    └── create-react-card          ← react-components + typescript-conventions
```

---

## Prioridade de criação

**Sprint 0 (antes de escrever código):** `typescript-conventions`, `error-handling`, `project-structure`, `azure-functions-endpoint`, `testing-patterns`

**Sprint 1 (quando o primeiro endpoint for implementado):** `azure-ai-search-integration`, `azure-openai-completion`, `create-rag-endpoint`, `create-integration-test`

**Sprint 2+:** `react-components`, `create-react-card`, `create-endpoint-docs`, `create-sdd-spec`
