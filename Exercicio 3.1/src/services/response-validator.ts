import {
  assistantResponseSchema,
  type AssistantResponse,
} from "../schemas/assistant-response.schema";

const SAFE_FALLBACK_RESPONSE = Object.freeze<AssistantResponse>({
  answer:
    "Não foi possível processar sua consulta. Por favor, tente novamente ou escale ao supervisor.",
  source_document: "FALLBACK",
  confidence_score: 0,
});

function normalizeText(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function violatesDangerousLoadRule(answer: string): boolean {
  const normalizedAnswer = normalizeText(answer);
  const mentionsDangerousLoad = /\bcargas?\s+perigosas?\b/.test(normalizedAnswer);

  const allowsReturnPatterns = [
    /\bpode ser devolvida\b/,
    /\be possivel devolver\b/,
    /\bpermite devolucao\b/,
    /^(?![\s\S]*\bnao\s+pode\s+devolver\b)[\s\S]*\bpode\s+devolver\b/,
  ];
  const allowsReturn = allowsReturnPatterns.some((pattern) =>
    pattern.test(normalizedAnswer),
  );

  return mentionsDangerousLoad && allowsReturn;
}

export function validateResponse(raw: unknown): AssistantResponse {
  const parsed = assistantResponseSchema.safeParse(raw);

  if (!parsed.success) {
    console.error("Structured output validation failed:", parsed.error.issues);
    return SAFE_FALLBACK_RESPONSE;
  }

  if (violatesDangerousLoadRule(parsed.data.answer)) {
    console.error(
      "Guardrail blocked response: dangerous load return policy contradiction.",
    );
    return SAFE_FALLBACK_RESPONSE;
  }

  return parsed.data;
}