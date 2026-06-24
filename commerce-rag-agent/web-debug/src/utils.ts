import type { AuthConfig } from "./types";

export const TEST_USER_ID = import.meta.env.VITE_TEST_USER_ID || "test-user-001";
export const TEST_USER_ROLES = import.meta.env.VITE_TEST_USER_ROLES || "user,ops";

export const defaultAuth: AuthConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  userId: storedUserId(),
  roles: stored("debug:roles") || TEST_USER_ROLES,
  token: stored("debug:token") || import.meta.env.VITE_TEST_BEARER_TOKEN || "",
  opsApiKey: stored("debug:opsApiKey") || import.meta.env.VITE_TEST_OPS_API_KEY || "",
};

function stored(key: string): string {
  return (localStorage.getItem(key) || "").trim();
}

function storedUserId(): string {
  const value = stored("debug:userId");
  return value && value !== "dev-user" ? value : TEST_USER_ID;
}

export function cleanBaseUrl(value: string): string {
  return (value || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export function persistAuth(auth: AuthConfig) {
  localStorage.setItem("debug:userId", auth.userId);
  localStorage.setItem("debug:roles", auth.roles);
  localStorage.setItem("debug:token", auth.token);
  localStorage.setItem("debug:opsApiKey", auth.opsApiKey);
}

export function currency(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "¥--";
  return `¥${value.toLocaleString("zh-CN")}`;
}

export function shortId(value?: string): string {
  if (!value) return "--";
  if (value.length <= 14) return value;
  return `${value.slice(0, 6)}...${value.slice(-5)}`;
}

export function formatTime(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function productIdOf(card: { product_id?: string; id?: string }): string {
  return card.product_id || card.id || "";
}

export function absoluteUrl(baseUrl: string, value?: string): string {
  if (!value) return "";
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  return `${cleanBaseUrl(baseUrl)}${value.startsWith("/") ? "" : "/"}${value}`;
}

export function asErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error || "请求失败");
}

export function stringifyPretty(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
