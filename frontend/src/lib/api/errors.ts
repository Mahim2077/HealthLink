type ApiErrorBody = {
  detail?: unknown;
  [key: string]: unknown;
};

function detailFromPayload(payload: unknown): string | null {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload
  ) {
    const detail = (payload as ApiErrorBody).detail;

    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }

    if (Array.isArray(detail)) {
      const firstMessage = detail.find(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "msg" in item &&
          typeof item.msg === "string",
      );

      if (
        typeof firstMessage === "object" &&
        firstMessage !== null &&
        "msg" in firstMessage &&
        typeof firstMessage.msg === "string"
      ) {
        return firstMessage.msg;
      }
    }
  }

  return null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(status: number, message: string, payload: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }

  static async fromResponse(response: Response): Promise<ApiError> {
    const contentType = response.headers.get("content-type") ?? "";
    let payload: unknown = null;

    if (contentType.includes("application/json")) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    }

    const fallbackMessage =
      response.statusText || "The HealthLink request could not be completed.";

    return new ApiError(
      response.status,
      detailFromPayload(payload) ?? fallbackMessage,
      payload,
    );
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
