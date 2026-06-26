import { app, HttpRequest, HttpResponseInit } from "@azure/functions";
import { CosmosClient } from "@azure/cosmos";
import pino from "pino";
import { z } from "zod";

type EnvMap = Record<string, string | undefined>;

function readEnv(name: string): string | undefined {
  const maybeGlobal = globalThis as { process?: { env?: EnvMap } };
  return maybeGlobal.process?.env?.[name];
}

const logger = pino({
  name: "novatech-feedback-handler",
  level: readEnv("LOG_LEVEL") ?? "info",
  redact: {
    paths: ["attendantEmail", "feedback.attendantEmail", "comment", "feedback.comment"],
    censor: "[REDACTED]",
  },
});

const feedbackInputSchema = z
  .object({
    queryId: z.string().trim().min(1).max(128),
    rating: z.number().int().min(1).max(5),
    comment: z.string().trim().max(2000).optional().default(""),
    attendantEmail: z.string().trim().email(),
  })
  .strict();

type FeedbackInput = z.infer<typeof feedbackInputSchema>;

type ApiErrorBody = {
  error: {
    code: string;
    message: string;
  };
};

function buildErrorResponse(
  status: number,
  code: string,
  message: string,
): HttpResponseInit {
  const body: ApiErrorBody = {
    error: {
      code,
      message,
    },
  };

  return {
    status,
    jsonBody: body,
  };
}

function getCosmosConnectionString(): string {
  const value = readEnv("COSMOS_CONNECTION_STRING");
  if (!value || value.trim().length === 0) {
    throw new Error("COSMOS_CONNECTION_STRING is missing or empty");
  }

  return value;
}

function formatUnknownError(error: unknown): Record<string, string> {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
    };
  }

  return {
    name: "UnknownError",
    message: "An unknown error occurred",
  };
}

function buildFeedbackDocument(input: FeedbackInput) {
  return {
    queryId: input.queryId,
    rating: input.rating,
    comment: input.comment,
    attendantEmail: input.attendantEmail,
    timestamp: new Date().toISOString(),
  };
}

export async function feedbackHandler(
  request: HttpRequest,
): Promise<HttpResponseInit> {
  try {
    const rawBody: unknown = await request.json();
    const parsedBody = feedbackInputSchema.safeParse(rawBody);

    if (!parsedBody.success) {
      const validationIssues = parsedBody.error.issues.map((issue: z.ZodIssue) => ({
        path: issue.path.join("."),
        code: issue.code,
        message: issue.message,
      }));

      logger.warn(
        {
          event: "feedback_validation_failed",
          issues: validationIssues,
        },
        "Feedback input validation failed",
      );

      return buildErrorResponse(
        400,
        "INVALID_INPUT",
        "Payload de feedback invalido.",
      );
    }

    const connectionString = getCosmosConnectionString();
    const client = new CosmosClient(connectionString);
    const database = client.database("novatech");
    const container = database.container("feedbacks");

    const feedbackDocument = buildFeedbackDocument(parsedBody.data);
    const createResult = await container.items.create(feedbackDocument);

    logger.info(
      {
        event: "feedback_created",
        queryId: feedbackDocument.queryId,
        rating: feedbackDocument.rating,
        itemId: createResult.resource?.id ?? null,
      },
      "Feedback persisted successfully",
    );

    return {
      status: 200,
      jsonBody: { status: "OK" },
    };
  } catch (error: unknown) {
    const errorInfo = formatUnknownError(error);

    logger.error(
      {
        event: "feedback_handler_failed",
        error: errorInfo,
      },
      "Feedback handler failed",
    );

    return buildErrorResponse(
      500,
      "INTERNAL_ERROR",
      "Nao foi possivel processar o feedback.",
    );
  }
}

app.http("feedback", {
  methods: ["POST"],
  handler: feedbackHandler,
});
