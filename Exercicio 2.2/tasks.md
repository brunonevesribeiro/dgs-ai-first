# Tasks — POST /api/query

Repositório: db1/novatech-assistant  
Stack: TypeScript, Azure Functions v4, Zod, pino

---

## TASK-001 — Schemas Zod de entrada e saída

**Estimativa:** P (< 2h)  
**Dependências:** nenhuma  
**Arquivos:** `src/schemas/query.schema.ts`, `src/schemas/query.schema.test.ts`

### Descrição

Definir e exportar os schemas Zod que representam o contrato do endpoint. Nenhuma lógica de negócio — apenas tipos e validação de shape/formato.

Schemas a criar:
- `QueryRequestSchema` — `{ question: string (min 1, max 500) }`
- `SearchChunkSchema` — `{ content: string, source_document: string, score: number, effective_date?: string }`
- `QueryResponseSchema` — `{ answer: string, source_document: string, chunks_used: number }`
- Exportar os tipos inferidos: `QueryRequest`, `SearchChunk`, `QueryResponse`

### Critérios de aceite

- [ ] `QueryRequestSchema.parse({ question: "" })` lança `ZodError`
- [ ] `QueryRequestSchema.parse({ question: "a".repeat(501) })` lança `ZodError`
- [ ] `QueryRequestSchema.parse({ question: "Qual o prazo?" })` retorna objeto tipado sem erro
- [ ] `QueryResponseSchema.parse({})` lança `ZodError` (campos obrigatórios ausentes)
- [ ] Todos os tipos exportados são utilizáveis sem cast em TypeScript strict mode
- [ ] Cobertura de testes: ≥ 90% de branches do schema

---

## TASK-002 — Utilitário de retry com exponential backoff

**Estimativa:** P (< 2h)  
**Dependências:** nenhuma  
**Arquivos:** `src/utils/retry.ts`, `src/utils/retry.test.ts`

### Descrição

Função genérica `withRetry<T>(fn: () => Promise<T>, opts: RetryOptions): Promise<T>` com exponential backoff e jitter. Não acoplada a nenhum cliente Azure — recebe qualquer função assíncrona.

Interface:

```typescript
interface RetryOptions {
  maxAttempts: number;   // default 3
  baseDelayMs: number;   // default 200
  maxDelayMs: number;    // default 5000
  retryIf?: (err: unknown) => boolean; // default: sempre retry
}
```

Fórmula de delay: `min(baseDelay * 2^(attempt-1) + jitter, maxDelay)` onde jitter ∈ [0, 100ms].

### Critérios de aceite

- [ ] Função bem-sucedida na 1ª tentativa: chamada exatamente 1 vez, sem delay
- [ ] Função que falha 2x e sucede na 3ª: retorna valor correto, `fn` chamada 3 vezes
- [ ] Função que falha `maxAttempts` vezes: rejeita com o último erro lançado
- [ ] `retryIf` retornando `false` aborta imediatamente sem novas tentativas
- [ ] O delay entre tentativas cresce a cada retry (verificável via mock de timer)
- [ ] Delay nunca excede `maxDelayMs` (verificar com `maxAttempts = 10`)

---

## TASK-003 — Configuração do logger estruturado (pino)

**Estimativa:** P (< 2h)  
**Dependências:** nenhuma  
**Arquivos:** `src/utils/logger.ts`, `src/utils/logger.test.ts`

### Descrição

Exportar instância configurada do pino com serializers padrão e campos de contexto fixos. A instância deve ser singleton (importar e reutilizar, não instanciar por request).

Configuração:
- `level`: lido de `process.env.LOG_LEVEL` com fallback `"info"`
- Campos base: `{ service: "novatech-assistant", version: process.env.npm_package_version }`
- Serializer para `Error`: inclui `message`, `stack`, `name`
- Em `NODE_ENV === "test"`: usar `pino.destination('/dev/null')` ou equivalente para suprimir output

### Critérios de aceite

- [ ] `logger.info({ question: "x" }, "query received")` produz JSON válido com campo `service`
- [ ] `logger.error({ err: new Error("boom") }, "failed")` inclui `err.stack` na saída
- [ ] Quando `LOG_LEVEL=debug`, mensagens de nível `debug` aparecem; quando `LOG_LEVEL=warn`, não aparecem
- [ ] Sem output nos testes (não polui o terminal do CI)
- [ ] Importações múltiplas do módulo retornam a mesma instância (singleton)

---

## TASK-004 — Loader do system prompt versionado

**Estimativa:** P (< 2h)  
**Dependências:** nenhuma  
**Arquivos:** `src/prompts/loader.ts`, `src/prompts/loader.test.ts`

### Descrição

Função que lê `prompts/system-prompt.md` do filesystem, extrai o conteúdo e retorna junto com hash SHA-256 do conteúdo para rastreabilidade nos logs. Cache em memória após primeira leitura (o arquivo não muda em runtime).

Interface:

```typescript
interface SystemPrompt {
  content: string;
  contentHash: string; // SHA-256 hex dos primeiros 8 chars
}

function loadSystemPrompt(): Promise<SystemPrompt>
```

### Critérios de aceite

- [ ] Retorna `content` não-vazio quando o arquivo existe
- [ ] `contentHash` é string hexadecimal de 8 caracteres (prefixo do SHA-256)
- [ ] Segunda chamada retorna o mesmo objeto sem re-ler o disco (cache hit verificável via spy em `fs.readFile`)
- [ ] Quando o arquivo não existe: rejeita com `Error` contendo o caminho no message
- [ ] O caminho é resolvido relativo à raiz do projeto (não ao CWD do processo)

---

## TASK-005 — Cliente de embeddings (Azure OpenAI)

**Estimativa:** M (2–4h)  
**Dependências:** TASK-002, TASK-003  
**Arquivos:** `src/clients/embedding.client.ts`, `src/clients/embedding.client.test.ts`

### Descrição

Função `generateEmbedding(text: string): Promise<number[]>` que chama a API Azure OpenAI Embeddings. Usa `withRetry` internamente. Loga tentativas e latência via logger.

Configuração via env vars:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (ex: `text-embedding-3-small`)

### Critérios de aceite

- [ ] Retorna array de números com length > 0 em resposta simulada de sucesso
- [ ] Valida que `text` não está vazio antes de chamar a API (lança `Error` síncrono)
- [ ] Em caso de HTTP 429 da API: tenta até 3 vezes via `withRetry`, depois rejeita
- [ ] Em caso de HTTP 400: não retenta, rejeita imediatamente (`retryIf` retorna `false`)
- [ ] Loga `{ attempt, latencyMs }` a cada chamada à API (verificar via mock do logger)
- [ ] Lança `Error` com mensagem descritiva quando env vars obrigatórias estão ausentes (fail-fast no import)
- [ ] Testes usam mock HTTP (não chamam Azure real)

---

## TASK-006 — Cliente Azure AI Search

**Estimativa:** M (2–4h)  
**Dependências:** TASK-001, TASK-002, TASK-003  
**Arquivos:** `src/clients/search.client.ts`, `src/clients/search.client.test.ts`

### Descrição

Função `searchChunks(embedding: number[], topK: number): Promise<SearchChunk[]>` que executa vector search no Azure AI Search. Retorna resultados ordenados por `score` desc. Aplica regra de ADR-0003: quando múltiplos chunks têm o mesmo `source_document`, retorna apenas o de `effective_date` mais recente.

Configuração via env vars:
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

### Critérios de aceite

- [ ] Retorna array de `SearchChunk[]` tipado conforme TASK-001
- [ ] Com 2 chunks do mesmo `source_document` e `effective_date` diferentes: retorna apenas o mais recente
- [ ] Com `topK = 5` e índice retornando 3 resultados: retorna 3 (sem padding)
- [ ] Retry em HTTP 503 (serviço indisponível); sem retry em HTTP 400
- [ ] Loga `{ indexName, resultsCount, latencyMs }` a cada busca
- [ ] `embedding` vazio (`[]`) lança `Error` antes de chamar a API
- [ ] Testes usam mock HTTP

---

## TASK-007 — Assembler de contexto com context budget

**Estimativa:** M (2–4h)  
**Dependências:** TASK-001  
**Arquivos:** `src/utils/context-assembler.ts`, `src/utils/context-assembler.test.ts`

### Descrição

Função pura `assemblePrompt(systemPrompt: string, chunks: SearchChunk[], question: string): AssembledPrompt` que monta as mensagens para o GPT-4o respeitando o budget de tokens definido no ADR-0002.

Interface:

```typescript
interface AssembledPrompt {
  messages: Array<{ role: "system" | "user"; content: string }>;
  chunksIncluded: number;
  estimatedTokens: number;
}
```

Budget (ADR-0002):
- System prompt: até ~4K tokens
- Chunks: até ~8K tokens
- Estimativa: `tokens ≈ chars / 4` (aproximação conservadora)
- Se chunks excederem budget: incluir os de maior `score` primeiro, truncar o restante

### Critérios de aceite

- [ ] Com 5 chunks pequenos: inclui todos os 5, `chunksIncluded === 5`
- [ ] Com 1 chunk de 40K chars: `chunksIncluded === 0` e `messages[1].content` não contém o chunk (ultrapassa budget de 8K tokens)
- [ ] `messages[0].role === "system"` contém exatamente o `systemPrompt` recebido
- [ ] `messages[1].role === "user"` contém a `question` e os chunks selecionados
- [ ] Chunks são inseridos em ordem decrescente de `score`
- [ ] Função é pura: mesmos inputs → mesmo output, sem side effects
- [ ] `estimatedTokens` reflete a soma real do conteúdo incluído

---

## TASK-008 — Cliente de completion (GPT-4o)

**Estimativa:** M (2–4h)  
**Dependências:** TASK-002, TASK-003  
**Arquivos:** `src/clients/completion.client.ts`, `src/clients/completion.client.test.ts`

### Descrição

Função `generateCompletion(messages: ChatMessage[]): Promise<string>` que chama GPT-4o via Azure OpenAI Chat Completions. Usa `withRetry` e loga latência e tokens consumidos.

Configuração via env vars:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_CHAT_DEPLOYMENT` (ex: `gpt-4o`)

### Critérios de aceite

- [ ] Retorna `string` com o conteúdo de `choices[0].message.content`
- [ ] Lança `Error` se `choices` estiver vazio ou `finish_reason === "content_filter"`
- [ ] Retry em HTTP 429 e 503; sem retry em HTTP 400 e 401
- [ ] Loga `{ deployment, promptTokens, completionTokens, latencyMs }` após cada chamada
- [ ] `messages` vazio `[]` lança `Error` antes de chamar a API
- [ ] Testes usam mock HTTP

---

## TASK-009 — Query handler (orquestrador)

**Estimativa:** M (2–4h)  
**Dependências:** TASK-001, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008  
**Arquivos:** `src/handlers/query.handler.ts`, `src/handlers/query.handler.test.ts`

### Descrição

Função `handleQuery(request: QueryRequest): Promise<QueryResponse>` que orquestra o pipeline completo: embedding → search → assemble → completion. Loga cada etapa com `requestId` para rastreabilidade.

Pipeline:
1. `generateEmbedding(request.question)`
2. `searchChunks(embedding, 5)`
3. `loadSystemPrompt()` (cached)
4. `assemblePrompt(systemPrompt.content, chunks, request.question)`
5. `generateCompletion(assembled.messages)`
6. Retornar `QueryResponse` com `source_document` do chunk de maior score

Todos os clientes são injetáveis via parâmetro (para testabilidade), com defaults para os módulos reais.

### Critérios de aceite

- [ ] Retorno válido conforme `QueryResponseSchema` para input válido (mocks dos clientes)
- [ ] `source_document` no response é o `source_document` do chunk com maior `score`
- [ ] Quando `searchChunks` retorna array vazio: `answer` contém mensagem de fallback configurável, `source_document === ""`
- [ ] `requestId` (UUID v4) aparece em todos os logs da requisição (verificar via mock do logger)
- [ ] Erro em qualquer etapa propaga como `Error` com contexto da etapa falha no message
- [ ] Injeção de dependências funciona: testes passam mocks sem alterar módulos reais

---

## TASK-010 — Azure Function HTTP trigger POST /api/query

**Estimativa:** P (< 2h)  
**Dependências:** TASK-001, TASK-003, TASK-009  
**Arquivos:** `src/functions/query.function.ts`, `src/functions/query.function.test.ts`

### Descrição

Azure Function v4 HTTP trigger que expõe `POST /api/query`. Valida body com Zod, delega ao handler, mapeia erros para HTTP status codes corretos.

Mapeamento de status:
- `200` — sucesso
- `400` — `ZodError` (body inválido)
- `500` — qualquer outro erro

### Critérios de aceite

- [ ] `POST /api/query` com `{ "question": "Qual o prazo?" }` retorna `200` com body válido conforme `QueryResponseSchema`
- [ ] `POST /api/query` com body vazio retorna `400` com `{ error: "validation_error", details: [...] }`
- [ ] `POST /api/query` com `question` vazia (`""`) retorna `400`
- [ ] Erro interno no handler retorna `500` com `{ error: "internal_error" }` sem stack trace no body
- [ ] Response inclui header `Content-Type: application/json`
- [ ] `requestId` do handler aparece no log de cada request (verificar via mock)
- [ ] Função registrada como `app.http("query", { methods: ["POST"], ... })` conforme Azure Functions v4 API

---

## Grafo de dependências

```
TASK-001 (Schemas)        ──────────────────────┐
TASK-002 (Retry)          ──────────┐            │
TASK-003 (Logger)         ────────┐ │            │
TASK-004 (Prompt loader)  ──────┐ │ │            │
                                │ │ │            │
TASK-005 (Embedding)  ←─ 002,003 ─┘ │            │
TASK-006 (Search)     ←─ 001,002,003 ┘            │
TASK-007 (Assembler)  ←─ 001 ────────────────────┘
TASK-008 (Completion) ←─ 002,003
                                │
TASK-009 (Handler)    ←─ 001,003,004,005,006,007,008
                                │
TASK-010 (Function)   ←─ 001,003,009
```

**Caminho crítico:** TASK-001 → TASK-007 → TASK-009 → TASK-010

**Paralelizável na sprint:**
- TASK-001, TASK-002, TASK-003, TASK-004 podem iniciar simultaneamente
- TASK-005, TASK-006, TASK-008 podem iniciar após TASK-002 e TASK-003
- TASK-007 pode iniciar após TASK-001
