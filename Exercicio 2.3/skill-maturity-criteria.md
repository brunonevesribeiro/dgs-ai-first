# Critérios de Maturidade de Skill

> Gerado por Claude Sonnet 4.6 em 2026-06-18 como resposta ao Exercício 2.3 do cenário NovaTech Assistant.

Como saber que uma skill está pronta para ser usada pelo Copilot e Claude Code em produção?

---

## Critérios mensuráveis

### 1. Taxa de aprovação em lint/typecheck sem ajuste manual
**Critério:** O código gerado passa em `tsc --strict` e no ESLint do projeto em **3 execuções consecutivas** com prompts distintos, sem que o desenvolvedor precise corrigir nenhum erro de ferramenta antes de commitar.

**Como medir:** Executar `tsc --noEmit && eslint src/` no código gerado. Zero erros = aprovado. Registrar as 3 tentativas.

---

### 2. Ausência dos anti-padrões documentados
**Critério:** O código gerado **não contém** nenhum dos anti-padrões listados na seção 4 da skill, verificável por grep ou regra de lint. Para `typescript-conventions`: nenhum `any` não justificado, nenhum `!` fora de testes, nenhum `console.log` em arquivo de `src/`.

**Como medir:** Grep automatizado nos arquivos gerados. Resultado binário: presente/ausente. Zero ocorrências = aprovado.

---

### 3. Cobertura de ativação — o agente aplica a skill nos cenários corretos
**Critério:** Dado um conjunto de **5 prompts** que correspondem às condições de ativação documentadas na skill (criação de handler, service, validator, etc.), o agente aplica os padrões da skill em **pelo menos 4 dos 5** sem que o desenvolvedor precise referenciar a skill explicitamente.

**Como medir:** Revisar o código gerado contra os critérios da skill. Contar quantos dos 5 prompts produziram código aderente sem reminder manual.

---

### 4. Tempo de revisão de código — zero comentários sobre o escopo da skill
**Critério:** Em **2 PRs consecutivos** onde a skill deveria ter sido aplicada, o code review não registra nenhum comentário sobre os tópicos cobertos pela skill (tipagem, imports, naming, null safety, env vars, logging).

**Como medir:** Contar comentários de review categorizados por tópico. Zero comentários no escopo da skill nos 2 PRs = aprovado.

---

### 5. Todos os exemplos DON'T são detectáveis por ferramenta automatizada
**Critério:** Cada exemplo "DON'T" da seção 3 da skill tem uma regra de ESLint ou check de `tsc` correspondente que **rejeita** aquele código. A skill só está madura se os erros que ela ensina a evitar podem ser capturados mecanicamente — não só por revisão humana.

**Como medir:** Para cada DON'T, colar o snippet no projeto e rodar `tsc --strict && eslint`. Se algum DON'T passa silenciosamente nas ferramentas, a skill precisa de regra nova ou o exemplo precisa ser revisado. 100% de cobertura = aprovado.

---

## Resumo

| # | Critério | Métrica | Limiar |
|---|---|---|---|
| 1 | Lint/typecheck sem ajuste | Erros após geração | 0 erros em 3 runs consecutivos |
| 2 | Anti-padrões ausentes | Grep nos arquivos gerados | 0 ocorrências dos padrões proibidos |
| 3 | Ativação correta | Prompts sem reminder explícito | ≥ 4/5 prompts aderentes |
| 4 | Revisão de código limpa | Comentários de PR no escopo | 0 comentários em 2 PRs seguidos |
| 5 | DON'Ts detectáveis por ferramenta | Snippets rejeitados por ESLint/tsc | 100% dos DON'Ts capturados |
