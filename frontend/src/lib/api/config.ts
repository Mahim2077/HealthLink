const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export function normalizeApiBaseUrl(value: string): string {
  const trimmedValue = value.trim();

  if (trimmedValue.startsWith("/") && !trimmedValue.startsWith("//")) {
    return trimmedValue.replace(/\/+$/, "") || "/";
  }

  let url: URL;

  try {
    url = new URL(trimmedValue);
  } catch {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL must be an HTTP(S) URL or a root-relative path.",
    );
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS.");
  }

  return trimmedValue.replace(/\/+$/, "");
}

export function joinApiUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = normalizeApiBaseUrl(baseUrl);
  const normalizedPath = path.replace(/^\/+/, "");

  return normalizedPath.length > 0
    ? normalizedBaseUrl + "/" + normalizedPath
    : normalizedBaseUrl;
}

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL,
);

export function buildApiUrl(path: string): string {
  return joinApiUrl(API_BASE_URL, path);
}
