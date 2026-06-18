import { describe, expect, expectTypeOf, it } from "vitest";
import { z, ZodError } from "zod";

import {
  QueryRequestSchema,
  QueryResponseSchema,
  SearchChunkSchema,
  type QueryRequest,
  type QueryResponse,
  type SearchChunk,
} from "./query.schema";

describe("QueryRequestSchema", () => {
  it("throws ZodError for empty question", () => {
    expect(() => QueryRequestSchema.parse({ question: "" })).toThrowError(ZodError);
  });

  it("throws ZodError for question longer than 500 chars", () => {
    expect(() => QueryRequestSchema.parse({ question: "a".repeat(501) })).toThrowError(
      ZodError,
    );
  });

  it("parses valid question and returns typed object", () => {
    const parsed = QueryRequestSchema.parse({ question: "Qual o prazo?" });
    const typed: QueryRequest = parsed;

    expect(typed).toEqual({ question: "Qual o prazo?" });
  });
});

describe("QueryResponseSchema", () => {
  it("throws ZodError when required fields are missing", () => {
    expect(() => QueryResponseSchema.parse({})).toThrowError(ZodError);
  });

  it("parses valid response", () => {
    const parsed = QueryResponseSchema.parse({
      answer: "Prazo de 5 dias uteis.",
      source_document: "SLA-2024-tabela-sla-clientes.md",
      chunks_used: 2,
    });
    const typed: QueryResponse = parsed;

    expect(typed.answer).toBe("Prazo de 5 dias uteis.");
    expect(typed.source_document).toBe("SLA-2024-tabela-sla-clientes.md");
    expect(typed.chunks_used).toBe(2);
  });
});

describe("SearchChunkSchema", () => {
  it("accepts chunk without optional effective_date", () => {
    const parsed = SearchChunkSchema.parse({
      content: "Trecho de contexto",
      source_document: "PROC-042-v2-frete-especial-revisado.md",
      score: 0.98,
    });
    const typed: SearchChunk = parsed;

    expect(typed.effective_date).toBeUndefined();
  });

  it("accepts chunk with effective_date", () => {
    const parsed = SearchChunkSchema.parse({
      content: "Trecho de contexto",
      source_document: "PROC-042-v2-frete-especial-revisado.md",
      score: 0.98,
      effective_date: "2024-10-01",
    });

    expect(parsed.effective_date).toBe("2024-10-01");
  });

  it("throws ZodError for invalid score type", () => {
    expect(() =>
      SearchChunkSchema.parse({
        content: "Trecho de contexto",
        source_document: "PROC-042-v2-frete-especial-revisado.md",
        score: "0.98",
      }),
    ).toThrowError(ZodError);
  });
});

describe("exported types", () => {
  it("are compatible with strict TypeScript inference without cast", () => {
    type InferredRequest = z.infer<typeof QueryRequestSchema>;
    type InferredChunk = z.infer<typeof SearchChunkSchema>;
    type InferredResponse = z.infer<typeof QueryResponseSchema>;

    expectTypeOf<QueryRequest>().toEqualTypeOf<InferredRequest>();
    expectTypeOf<SearchChunk>().toEqualTypeOf<InferredChunk>();
    expectTypeOf<QueryResponse>().toEqualTypeOf<InferredResponse>();
  });
});

describe("SearchChunkSchema — score validation", () => {
  it("throws ZodError for score above 1", () => {
    expect(() => SearchChunkSchema.parse({
      content: "x", source_document: "doc.md", score: 1.5
    })).toThrowError(ZodError);
  });

  it("throws ZodError for negative score", () => {
    expect(() => SearchChunkSchema.parse({
      content: "x", source_document: "doc.md", score: -0.1
    })).toThrowError(ZodError);
  });
});

describe("SearchChunkSchema — effective_date validation", () => {
  it("throws ZodError for invalid date format", () => {
    expect(() => SearchChunkSchema.parse({
      content: "x", source_document: "doc.md", 
      score: 0.9, effective_date: "banana"
    })).toThrowError(ZodError);
  });

  it("accepts valid ISO 8601 date", () => {
    const parsed = SearchChunkSchema.parse({
      content: "x", source_document: "doc.md",
      score: 0.9, effective_date: "2024-01-15"
    });
    expect(parsed.effective_date).toBe("2024-01-15");
  });
});
