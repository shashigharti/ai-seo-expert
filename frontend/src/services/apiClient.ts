const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseErrorResponse(response: Response): Promise<never> {
  let body: ApiErrorBody | null = null;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // Response had no JSON body; fall through to the generic error below.
  }
  const code = body?.error?.code ?? "UNKNOWN_ERROR";
  const message = body?.error?.message ?? `Request failed with status ${response.status}`;
  throw new ApiError(response.status, code, message);
}

export async function getRequest<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
  try {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}${endpoint}${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url);
    if (!response.ok) {
      await parseErrorResponse(response);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Request Error:", error);
    throw error;
  }
}

export async function postRequest<T>(endpoint: string, data: unknown): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      await parseErrorResponse(response);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Request Error:", error);
    throw error;
  }
}
