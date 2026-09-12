const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type QueryRequest = {
  question: string;
};

export type QueryResponse = {
  answer: string;
};

export async function apiFetch<TResponse>(
  path: string,
  options: RequestInit = {},
): Promise<TResponse> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<TResponse>;
}

export function submitQuery(question: string): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({ question } satisfies QueryRequest),
  });
}

