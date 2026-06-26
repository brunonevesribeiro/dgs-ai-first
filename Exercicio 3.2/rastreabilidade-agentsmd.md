# Rastreabilidade — Correções vs. AGENTS.md

## Cada correção aplicada e sua regra de origem

| Problema | Correção aplicada | Regra AGENTS.md |
|---|---|---|
| console.log com PII | pino com redact de attendantEmail | "pino para logging, nunca console.log" + "nunca logar dados pessoais" |
| require dinâmico | import estático no topo | "imports estáticos no topo" |
| as any sem Zod | feedbackInputSchema com Zod | "Zod para validação de input" |
| process.env sem validação | getCosmosConnectionString() com fail-fast | "TypeScript strict mode" |
| Sem try/catch | try/catch com buildErrorResponse | "TypeScript strict mode" |

## Conexão com cenários anteriores

### Cenário 1 — ADR-0003 (documentos contraditórios)
O campo `rating` agora tem validação de intervalo (1-5) via Zod,
evitando dados corrompidos no Cosmos — mesma lógica de 
integridade de dados da ADR-0003.

### Cenário 2 — AGENTS.md
Todas as 5 correções derivam diretamente das regras definidas 
no AGENTS.md construído no cenário 2. O código reescrito passa 
em todas as regras do documento.

### Cenário 2 — Skill typescript-conventions
O código reescrito segue os padrões da skill:
- unknown em vez de any para dados externos
- Guard clause para env var obrigatória (getCosmosConnectionString)
- Async/await com try/catch em vez de .then/.catch
- Nenhum console.log
