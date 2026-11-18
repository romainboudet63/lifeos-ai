import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Adresse de l'API, par ordre de priorité :
//  1. EXPO_PUBLIC_API_URL (ex. "http://192.168.1.20:8000" pour tester sur un téléphone en dev) ;
//  2. sur le web : "" = même adresse que la page (le backend sert aussi l'app, cf. DEPLOY.md) ;
//  3. en natif : localhost (simulateur uniquement).
const envUrl = process.env.EXPO_PUBLIC_API_URL;
export const API_BASE_URL: string = envUrl
  ? envUrl.replace(/\/+$/, "")
  : Platform.OS === "web"
    ? ""
    : "http://localhost:8000";

const TOKEN_KEY = "lifeos_access_token";

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; formBody?: boolean } = {}
): Promise<T> {
  const { method = "GET", body, auth = true, formBody = false } = options;

  const headers: Record<string, string> = {};
  if (!formBody) headers["Content-Type"] = "application/json";
  else headers["Content-Type"] = "application/x-www-form-urlencoded";

  if (auth) {
    const token = await getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? (formBody ? (body as string) : JSON.stringify(body)) : undefined,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      // réponse non-JSON, on garde le statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, options?: { auth?: boolean; formBody?: boolean }) =>
    request<T>(path, { method: "POST", body, ...options }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export { ApiError };
