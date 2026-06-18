# Revisão Crítica — Código gerado pelo Copilot (TASK-001)

## Problema 1 — score sem validação de range

**Arquivo:** src/schemas/query.schema.ts
**Linha:** SearchChunkSchema, campo score

**Gerado pelo Copilot:**
score: z.number()

**Problema:** aceita qualquer número, incluindo valores fora do 
range 0-1 de similaridade. A TASK-007 ordena chunks por score — 
valor inválido causaria ordenação silenciosamente errada.

**Correção:**
score: z.number().min(0).max(1)

---

## Problema 2 — effective_date sem validação de formato

**Arquivo:** src/schemas/query.schema.ts  
**Linha:** SearchChunkSchema, campo effective_date

**Gerado pelo Copilot:**
effective_date: z.string().optional()

**Problema:** aceita qualquer string. A TASK-006 usa esse campo 
para aplicar ADR-0003 (priorizar versão mais recente em documentos 
contraditórios). Formato inválido causa comparação incorreta de 
datas sem erro explícito.

**Correção:**
effective_date: z.string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 
    "effective_date must be ISO 8601 (YYYY-MM-DD)")
  .optional()

## Validação pós-correção

Suíte executada em 2026-06-18 17:48:04
13 testes — 13 passando, 0 falhando
Correções de score range e effective_date format validadas.  