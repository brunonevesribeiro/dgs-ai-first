# Code Review — `response-validator.ts`

**Exercício:** 3.1 — Structured output e verificações determinísticas (Desenvolvedor)  
**Arquivo revisado:** `src/services/response-validator.ts`  
**Revisor:** Claude (modelo: claude-sonnet-4-6)  
**Data:** 2026-06-26

---

## Contexto da revisão

O `response-validator.ts` é o harness determinístico do NovaTech Assistant. Ele deve:
1. Validar a resposta do modelo contra o schema Zod de structured output.
2. Aplicar dois guardrails de conteúdo: (a) `source_document` obrigatório; (b) bloquear afirmações de que carga perigosa pode ser devolvida.

A revisão foi feita sobre o código gerado pelo GitHub Copilot, conforme solicitado no exercício.

---

## Problemas identificados

### Problema 1 — Crítico: Falso positivo bloqueia respostas corretas

**Localização:** `violatesDangerousLoadRule`, linha 30–32

**O que está errado:**

A verificação de `allowsReturn` usa `.includes("pode devolver")`, que faz busca por substring. A string `"não pode devolver"` contém `"pode devolver"` como substring — e portanto o guardrail dispara mesmo quando a resposta afirma corretamente a proibição.

**Exemplo que falha:**
```
"Carga perigosa não pode devolver pelo processo padrão."
```
- `mentionsDangerousLoad` → `true` (contém "carga perigosa")
- `allowsReturn` → `true` ("nao pode devolver" inclui "pode devolver")
- Resultado: resposta **bloqueada** — mas era correta

**Por que é um problema:**

Um guardrail que bloqueia respostas corretas é pior do que não ter guardrail: degrada o assistente e gera fallback inútil exatamente quando o atendente recebeu a informação certa.

**Como corrigir:**

Usar regex com lookahead negativo para excluir negações antes das frases de retorno:

```typescript
const allowsReturnPatterns = [
  /(?<!n[aã]o\s)pode\s+ser\s+devolvida/,
  /(?<!n[aã]o\s)pode\s+devolver/,
  /(?<!n[aã]o\s)permite\s+devolucao/,
  /e\s+possivel\s+devolver/,
];

const allowsReturn = allowsReturnPatterns.some((re) => re.test(normalizedAnswer));
```

> Alternativa mais robusta: inverter a lógica e procurar especificamente pela frase proibida com contexto positivo, em vez de checar condições separadas que podem colidir.

---

### Problema 2 — Alto: `SAFE_FALLBACK_RESPONSE` viola o próprio schema Zod

**Localização:** `SAFE_FALLBACK_RESPONSE`, linha 6–11

**O que está errado:**

O schema define `source_document: z.string().min(1)` (string não vazia). O fallback usa `source_document: ""`, que tem zero caracteres.

O TypeScript **não detecta** isso porque `AssistantResponse` é `z.infer<typeof assistantResponseSchema>`, que expande apenas para `{ source_document: string }` — a constraint `.min(1)` existe apenas em runtime no Zod, não no tipo estático.

**Por que é um problema:**

Qualquer sistema downstream que re-valide com Zod (teste de contrato, outro serviço, BFF) vai falhar exatamente no fallback de segurança. O código dá garantia de tipo em tempo de compilação que não reflete a garantia real em runtime.

**Como corrigir:**

```typescript
const SAFE_FALLBACK_RESPONSE: AssistantResponse = {
  answer:
    "Não foi possível processar sua consulta. Por favor, tente novamente ou escale ao supervisor.",
  source_document: "FALLBACK",  // satisfaz min(1)
  confidence_score: 0,
};
```

Ou, se `""` for semanticamente necessário, relaxar o schema para o campo ser opcional quando `confidence_score === 0`:

```typescript
source_document: z.string().or(z.literal("")),
```

---

### Problema 3 — Médio: Objeto de fallback mutável retornado por referência

**Localização:** retornos das linhas 42 e 49

**O que está errado:**

`SAFE_FALLBACK_RESPONSE` é um objeto plano não congelado. A função retorna a **referência direta**, não uma cópia. Qualquer caller que faça `result.answer = "..."` corrompe silenciosamente o módulo para todas as chamadas seguintes.

```typescript
// caller malicioso ou descuidado:
const result = validateResponse(raw);
result.answer = "resposta modificada"; // corrompe SAFE_FALLBACK_RESPONSE global
```

**Por que é um problema:**

Em um harness determinístico, estado global mutável introduz não-determinismo. O bug seria difícil de rastrear em produção pois o fallback passaria a retornar um texto diferente do esperado após a primeira mutação.

**Como corrigir:**

Congelar o objeto na definição:

```typescript
const SAFE_FALLBACK_RESPONSE: AssistantResponse = Object.freeze({
  answer:
    "Não foi possível processar sua consulta. Por favor, tente novamente ou escale ao supervisor.",
  source_document: "FALLBACK",
  confidence_score: 0,
});
```

O `Object.freeze` lança erro em strict mode se alguém tentar mutar, em vez de falhar silenciosamente.

---

## Tabela de priorização

| # | Severidade | Problema | Impacto |
|---|-----------|----------|---------|
| 1 | Crítico | Falso positivo via substring em negação | Bloqueia respostas corretas sobre carga perigosa |
| 2 | Alto | `source_document: ""` viola `min(1)` do schema | Quebra validação downstream; tipo TypeScript dá falsa segurança |
| 3 | Médio | Objeto fallback mutável retornado por referência | Estado global corrompível silenciosamente |

---

## Distinção: determinístico vs. probabilístico

O exercício pede que fique clara a diferença entre as duas camadas:

| Camada | Mecanismo | Garantia |
|--------|-----------|----------|
| **Prompt** | Instrução ao modelo | Probabilística — o modelo geralmente segue, mas pode falhar |
| **Código (`response-validator.ts`)** | Schema Zod + funções puras | Determinística — bloqueia sempre, independente do modelo |

O `response-validator.ts` é correto no desenho: ele existe justamente porque o prompt não é suficiente. Os 3 problemas identificados enfraquecem a garantia determinística — o problema 1 especialmente, pois faz o guardrail determinístico se comportar de forma incorreta e consistente.
