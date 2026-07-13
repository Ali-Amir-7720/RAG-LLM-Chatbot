import { apiFetch, clearTokens, setTokens } from "./api-client";
import type { AuthResponse, User } from "./types";
export async function signup(input: {
  username: string;
  email: string;
  password: string;
}): Promise<User> {
  const res = await apiFetch<AuthResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
    auth: false,
  });
  setTokens(res.tokens);
  return res.user;
}
export async function login(input: {
  email: string;
  password: string;
  device?: string;
}): Promise<User> {
  const res = await apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ device: "web", ...input }),
    auth: false,
  });
  setTokens(res.tokens);
  return res.user;
}
export async function logout() {
  const refreshToken =
    typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
  if (!refreshToken) {
    clearTokens();
    return;
  }
  try {
    await apiFetch("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
      auth: false,
    });
  } finally {
    clearTokens();
  }
}
export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/users/me");
}