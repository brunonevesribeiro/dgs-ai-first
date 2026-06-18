# Skill: typescript-conventions

## 1. CONTEXTO

Esta skill se aplica sempre que houver geracao, refatoracao ou revisao de codigo TypeScript no projeto NovaTech Assistant.

Use esta skill quando a tarefa envolver:
- criacao de handlers, services, repositories, validators ou testes em TypeScript;
- mudanca de contratos entre camadas (DTOs, interfaces, tipos de retorno);
- integracao com SDKs externos (Azure, HTTP clients, bancos, mensageria);
- qualquer codigo que rode com TypeScript strict mode habilitado.

Objetivo: garantir codigo previsivel, tipado, seguro contra null/undefined, legivel e pronto para manutencao em producao.

---

## 2. REGRAS PRESCRITIVAS (DEVE / NAO DEVE)

### 2.1 Strict mode e tipagem

DEVE:
- Compilar sem erros com strict mode ativo.
- Declarar tipo explicito em fronteiras de modulo: parametros publicos, retornos de funcoes exportadas, DTOs e contratos.
- Preferir unknown em vez de any para dados externos.
- Fazer narrowing explicito antes de usar valores unknown.
- Usar discriminated unions para estados/fluxos com multiplos casos.

NAO DEVE:
- Introduzir any sem justificativa tecnica formal.
- Usar as Type para forcar cast sem validacao previa.
- Retornar tipos amplos demais quando um tipo mais restrito e conhecido.

### 2.2 Imports e organizacao de dependencias

DEVE:
- Ordenar imports em 3 blocos: externos, internos (alias/caminho absoluto), relativos.
- Importar apenas o que e usado.
- Preferir import type para tipos quando aplicavel.
- Manter o mesmo estilo de import em todo o arquivo.

NAO DEVE:
- Misturar require com import no mesmo modulo (salvo compatibilidade legada explicitada).
- Criar imports circulares entre modulos.
- Deixar imports mortos.

### 2.3 Naming

DEVE:
- Usar camelCase para variaveis e funcoes.
- Usar PascalCase para tipos, interfaces, classes e enums.
- Usar UPPER_SNAKE_CASE para constantes globais e chaves de configuracao.
- Dar nomes orientados ao dominio (ex.: customerId, freightPolicyVersion).

NAO DEVE:
- Usar nomes genericos sem semantica (data, value, temp, obj).
- Abreviar nomes de dominio sem padrao reconhecido.
- Reaproveitar o mesmo nome para conceitos diferentes no mesmo contexto.

### 2.4 Null safety

DEVE:
- Tratar null/undefined na borda de entrada (request, env, payload externo).
- Usar guard clauses para falhar cedo quando dado obrigatorio estiver ausente.
- Usar optional chaining e nullish coalescing de forma intencional.
- Modelar opcionalidade no tipo (campo?: string) em vez de esconder com cast.

NAO DEVE:
- Usar non-null assertion (!) como solucao padrao.
- Assumir que dados externos sempre estao completos.
- Mascarar ausencia de dado com fallback silencioso inadequado.

### 2.5 Async/await e fluxo assincrono

DEVE:
- Usar async/await em vez de encadear .then/.catch em codigo novo.
- Envolver chamadas I/O em try/catch quando houver tratamento local.
- Propagar erro enriquecido quando a camada atual nao puder resolver.
- Usar Promise.all apenas quando as operacoes forem independentes.

NAO DEVE:
- Fazer await dentro de loops quando houver paralelizacao segura.
- Ignorar promises (floating promises) sem tratamento.
- Engolir erro com catch vazio.

### 2.6 Logging

DEVE:
- Logar eventos relevantes de operacao: inicio/fim de fluxo, erro, degradacao e fallback.
- Incluir contexto minimo: operation, correlationId, entidade e resultado.
- Usar nivel adequado (debug/info/warn/error).
- Sanitizar dados sensiveis antes de logar.

NAO DEVE:
- Logar segredo, token, senha, payload com PII bruto.
- Usar console.log em codigo de producao (exceto bootstrap local controlado).
- Duplicar log do mesmo erro em todas as camadas sem criterio.

### 2.7 Variaveis de ambiente

DEVE:
- Ler env vars via modulo centralizado de configuracao.
- Validar env vars obrigatorias no startup.
- Converter tipos explicitamente (number, boolean) com validacao.
- Definir defaults apenas para campos realmente opcionais.

NAO DEVE:
- Ler process.env espalhado por varios modulos de dominio.
- Assumir que process.env.PORT ja e number.
- Manter comportamento silencioso quando variavel obrigatoria estiver ausente.

---

## 3. EXEMPLOS CONCRETOS (DO / DON'T)

### Exemplo A: Dados externos e strict typing

DO:
```ts
interface SearchChunk {
  id: string;
  content: string;
  score: number;
}

function parseChunk(input: unknown): SearchChunk {
  if (typeof input !== "object" || input === null) {
    throw new Error("Chunk invalido: objeto esperado");
  }

  const maybe = input as { id?: unknown; content?: unknown; score?: unknown };

  if (typeof maybe.id !== "string") throw new Error("id invalido");
  if (typeof maybe.content !== "string") throw new Error("content invalido");
  if (typeof maybe.score !== "number") throw new Error("score invalido");

  return { id: maybe.id, content: maybe.content, score: maybe.score };
}
```

DON'T:
```ts
function parseChunk(input: any) {
  return {
    id: input.id,
    content: input.content,
    score: input.score,
  };
}
```

### Exemplo B: Async/await + tratamento de erro

DO:
```ts
type UserProfile = { id: string; email: string };

async function getUserProfile(userId: string): Promise<UserProfile> {
  try {
    const response = await fetch(`https://api.example.com/users/${userId}`);

    if (!response.ok) {
      throw new Error(`Falha ao consultar usuario: status ${response.status}`);
    }

    const json = (await response.json()) as unknown;
    if (typeof json !== "object" || json === null) {
      throw new Error("Resposta invalida da API de usuario");
    }

    const data = json as { id?: unknown; email?: unknown };
    if (typeof data.id !== "string" || typeof data.email !== "string") {
      throw new Error("Campos obrigatorios ausentes na resposta de usuario");
    }

    return { id: data.id, email: data.email };
  } catch (error) {
    throw new Error(`getUserProfile: erro para userId=${userId}`, { cause: error as Error });
  }
}
```

DON'T:
```ts
function getUserProfile(userId: string) {
  return fetch("https://api.example.com/users/" + userId)
    .then((r) => r.json())
    .catch(() => null);
}
```

### Exemplo C: Env vars centralizadas e validadas

DO:
```ts
interface AppConfig {
  nodeEnv: "development" | "test" | "production";
  openAiEndpoint: string;
  openAiApiKey: string;
  requestTimeoutMs: number;
}

function getRequiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Env var obrigatoria ausente: ${name}`);
  }
  return value;
}

export function loadConfig(): AppConfig {
  const timeoutRaw = process.env.REQUEST_TIMEOUT_MS ?? "5000";
  const requestTimeoutMs = Number(timeoutRaw);

  if (!Number.isFinite(requestTimeoutMs) || requestTimeoutMs <= 0) {
    throw new Error("REQUEST_TIMEOUT_MS invalida");
  }

  const nodeEnvRaw = getRequiredEnv("NODE_ENV");
  if (nodeEnvRaw !== "development" && nodeEnvRaw !== "test" && nodeEnvRaw !== "production") {
    throw new Error("NODE_ENV invalido");
  }

  return {
    nodeEnv: nodeEnvRaw,
    openAiEndpoint: getRequiredEnv("AZURE_OPENAI_ENDPOINT"),
    openAiApiKey: getRequiredEnv("AZURE_OPENAI_API_KEY"),
    requestTimeoutMs,
  };
}
```

DON'T:
```ts
export const config = {
  endpoint: process.env.AZURE_OPENAI_ENDPOINT,
  key: process.env.AZURE_OPENAI_API_KEY,
  timeout: process.env.REQUEST_TIMEOUT_MS || 5000,
};
```

### Exemplo D: Logging com contexto e sem segredo

DO:
```ts
type LogLevel = "info" | "warn" | "error";

function log(level: LogLevel, message: string, context: Record<string, unknown>): void {
  const safeContext = { ...context, apiKey: "[REDACTED]" };
  console[level](JSON.stringify({ level, message, ...safeContext }));
}

log("info", "RAG query iniciada", {
  operation: "searchAndComplete",
  correlationId: "req-123",
  customerId: "c-001",
});
```

DON'T:
```ts
console.log("endpoint", process.env.AZURE_OPENAI_ENDPOINT);
console.log("apiKey", process.env.AZURE_OPENAI_API_KEY);
console.log("query", request.body);
```

---

## 4. ANTI-PADROES (ERROS COMUNS DE LLM SEM ESTE GUIDANCE)

1. Tipagem frouxa em cadeia:
   uso de any em payload, retorno e camadas intermediarias, eliminando beneficios do strict mode.

2. Tratamento inseguro de dados opcionais:
   abuso de non-null assertion (!) e casts cegos em vez de guard clauses e narrowing.

3. Configuracao e logs inseguros:
   leitura direta de process.env em varios arquivos e exposicao de segredo/token em logs.

---

## 5. DEPENDENCIAS (LEITURA PREVIA)

- Nenhuma obrigatoria. Esta skill e fundacional e deve ser aplicada primeiro.
- Leitura recomendada em seguida:
  - error-handling (para padronizar erros de dominio e propagacao)
  - project-structure (para posicionar arquivos e modulos corretamente)

---

## 6. EVIDENCIA DE GERACAO COM COPILOT

- Registro de prompt, iteracoes e saida verificavel:
  - Exercicio 2.3/copilot-evidencia-typescript-conventions.md
