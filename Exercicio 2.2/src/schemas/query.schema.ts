import { z } from "zod";

export const QueryRequestSchema = z.object({
  question: z.string().min(1).max(500),
});

export const SearchChunkSchema = z.object({
  content: z.string(),
  source_document: z.string(),
  score: z.number().min(0).max(1), // corrigido: range 0-1
  effective_date: z.string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 
      "effective_date must be ISO 8601 (YYYY-MM-DD)")
    .optional(), // corrigido: formato validado
});

export const QueryResponseSchema = z.object({
  answer: z.string(),
  source_document: z.string(),
  chunks_used: z.number(),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type SearchChunk = z.infer<typeof SearchChunkSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
