import type {
  AuthConfig,
  AsrResult,
  CartState,
  CheckoutPreview,
  HealthPayload,
  OpsDashboard,
  OpsMetrics,
  OrderResult,
  ProductCardData,
  ProductQuestions,
  ProductReviewSummary,
  SessionSummary,
  StreamHandlers,
  UploadResult,
  UserProductCollectionItem,
  VoiceCapabilities,
} from "./types";
import { cleanBaseUrl, TEST_USER_ID, TEST_USER_ROLES } from "./utils";

export class ApiClient {
  constructor(private readonly auth: AuthConfig) {}

  async health(deep = false): Promise<HealthPayload> {
    return this.request<HealthPayload>(deep ? "/health/deep" : "/health", { skipAuth: true });
  }

  async sessions(): Promise<SessionSummary[]> {
    return this.request<SessionSummary[]>("/api/sessions");
  }

  async createSession(title = "导购会话"): Promise<SessionSummary> {
    return this.request<SessionSummary>("/api/sessions", {
      method: "POST",
      body: { title },
    });
  }

  async messages(sessionId: string) {
    return this.request(`/api/sessions/${encodeURIComponent(sessionId)}/messages`);
  }

  async deleteSession(sessionId: string) {
    return this.request(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  }

  async uploadImage(file: File): Promise<UploadResult> {
    const form = new FormData();
    form.append("file", file);
    return this.request<UploadResult>("/api/upload/image", {
      method: "POST",
      form,
    });
  }

  async voiceCapabilities(): Promise<VoiceCapabilities> {
    return this.request<VoiceCapabilities>("/api/voice/capabilities", { skipAuth: true });
  }

  async transcribeAudio(file: File, language = "zh"): Promise<AsrResult> {
    const form = new FormData();
    form.append("file", file);
    return this.request<AsrResult>(`/api/voice/asr?language=${encodeURIComponent(language)}`, {
      method: "POST",
      form,
    });
  }

  async streamChat(
    payload: { message: string; session_id?: string | null; upload_id?: string | null; memory?: Record<string, unknown> },
    handlers: StreamHandlers,
  ): Promise<void> {
    const response = await fetch(this.url("/api/chat/stream"), {
      method: "POST",
      headers: {
        ...this.headers(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok || !response.body) {
      throw new Error(await this.errorText(response));
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split(/\n\n/);
      buffer = chunks.pop() || "";
      for (const chunk of chunks) {
        await this.dispatchSse(chunk, handlers);
      }
    }
    if (buffer.trim()) await this.dispatchSse(buffer, handlers);
  }

  async getCart(): Promise<CartState> {
    return this.request<CartState>("/api/commerce/cart");
  }

  async addCartItem(productId: string, quantity = 1, query = "", skuId = "") {
    return this.request("/api/commerce/cart/items", {
      method: "POST",
      body: { product_id: productId, quantity, query, sku_id: skuId },
    });
  }

  async updateCartItem(cartItemId: string, quantity: number) {
    return this.request(`/api/commerce/cart/items/${encodeURIComponent(cartItemId)}`, {
      method: "PATCH",
      body: { quantity },
    });
  }

  async removeCartItem(cartItemId: string) {
    return this.request(`/api/commerce/cart/items/${encodeURIComponent(cartItemId)}`, { method: "DELETE" });
  }

  async previewCheckout(productItems?: Array<{ product_id: string; quantity: number; sku_id?: string }>): Promise<CheckoutPreview> {
    return this.request<CheckoutPreview>("/api/commerce/checkout/preview", {
      method: "POST",
      body: productItems?.length ? { product_items: productItems } : {},
    });
  }

  async confirmCheckout(checkout: CheckoutPreview): Promise<OrderResult> {
    return this.request<OrderResult>("/api/commerce/checkout/confirm", {
      method: "POST",
      body: {
        checkout_id: checkout.checkout_id,
        confirm_token: checkout.confirm_token,
        idempotency_key: `debug-${checkout.checkout_id}`,
      },
    });
  }

  async createPriceAlert(productId: string, targetPrice: number) {
    return this.request("/api/alerts/price", {
      method: "POST",
      body: { product_id: productId, target_price: targetPrice },
    });
  }

  async getProfile() {
    return this.request("/api/profile");
  }

  async savePreference(value: Record<string, unknown>) {
    return this.request("/api/profile/preferences", {
      method: "PUT",
      body: { scope: "global", key: "shopping_context", value, source: "web-debug" },
    });
  }

  async productDetail(productId: string) {
    return this.request(`/api/products/${encodeURIComponent(productId)}`);
  }

  async productIntelligence(productId: string) {
    return this.request(`/api/products/${encodeURIComponent(productId)}/intelligence`);
  }

  async productReviewSummary(productId: string): Promise<ProductReviewSummary> {
    return this.request<ProductReviewSummary>(`/api/products/${encodeURIComponent(productId)}/reviews/summary`);
  }

  async productQuestions(productId: string): Promise<ProductQuestions> {
    return this.request<ProductQuestions>(`/api/products/${encodeURIComponent(productId)}/questions`);
  }

  async createProductQuestion(productId: string, question: string) {
    return this.request(`/api/products/${encodeURIComponent(productId)}/questions`, {
      method: "POST",
      body: { question },
    });
  }

  async markProductView(productId: string) {
    return this.request(`/api/products/${encodeURIComponent(productId)}/view`, { method: "POST" });
  }

  async listUserProducts(listType: "favorite" | "compare" | "recent"): Promise<UserProductCollectionItem[]> {
    return this.request<UserProductCollectionItem[]>(`/api/behavior/products?list_type=${encodeURIComponent(listType)}&limit=12`);
  }

  async addUserProduct(listType: "favorite" | "compare" | "recent", productId: string) {
    return this.request(`/api/behavior/${encodeURIComponent(listType)}/${encodeURIComponent(productId)}`, {
      method: "PUT",
      body: { metadata: { source: "web-debug" } },
    });
  }

  async removeUserProduct(listType: "favorite" | "compare" | "recent", productId: string) {
    return this.request(`/api/behavior/${encodeURIComponent(listType)}/${encodeURIComponent(productId)}`, { method: "DELETE" });
  }

  async feedback(messageId: string, rating: 1 | -1, reason = "") {
    return this.request("/api/feedback", {
      method: "POST",
      body: { message_id: messageId, rating, reason },
    });
  }

  async opsMetrics(): Promise<OpsMetrics> {
    return this.request<OpsMetrics>("/api/ops/metrics", { ops: true });
  }

  async opsDashboard(): Promise<OpsDashboard> {
    return this.request<OpsDashboard>("/api/ops/dashboard", { ops: true });
  }

  async imageSearchText(query: string): Promise<{ product_cards: ProductCardData[]; trace: unknown[] }> {
    return this.request("/api/image-search/text", {
      method: "POST",
      body: { query, limit: 8 },
    });
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: HeadersInit = options.form
      ? this.headers(options)
      : {
          ...this.headers(options),
          "Content-Type": "application/json",
        };
    const response = await fetch(this.url(path), {
      method: options.method || "GET",
      headers,
      body: options.form || (options.body ? JSON.stringify(options.body) : undefined),
    });
    if (!response.ok) throw new Error(await this.errorText(response));
    return response.json() as Promise<T>;
  }

  private url(path: string): string {
    return `${cleanBaseUrl(this.auth.baseUrl)}${path}`;
  }

  private headers(options: Pick<RequestOptions, "skipAuth" | "ops"> = {}): HeadersInit {
    if (options.skipAuth) return {};
    const headers: Record<string, string> = {
      "X-User-ID": this.auth.userId || TEST_USER_ID,
      "X-User-Roles": this.auth.roles || TEST_USER_ROLES,
      "X-Request-ID": `web-${crypto.randomUUID()}`,
    };
    if (this.auth.token) headers.Authorization = `Bearer ${this.auth.token}`;
    if (options.ops && this.auth.opsApiKey) headers["X-Ops-API-Key"] = this.auth.opsApiKey;
    return headers;
  }

  private async dispatchSse(chunk: string, handlers: StreamHandlers) {
    const lines = chunk.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() || "message";
    const data = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("\n");
    let payload: unknown = data;
    try {
      payload = JSON.parse(data);
    } catch {
      payload = data;
    }

    handlers.onRaw?.(event, payload);
    if (event === "status") handlers.onStatus?.(payload as never);
    if (event === "message_start") handlers.onMessageStart?.(payload as never);
    if (event === "message_delta") handlers.onMessageDelta?.(payload as never);
    if (event === "message") handlers.onMessage?.(payload as never);
    if (event === "trace") handlers.onTrace?.(payload as never);
    if (event === "product_cards") handlers.onProducts?.(payload as never);
    if (event === "cart_state") handlers.onCart?.(payload as never);
    if (event === "vision_analysis") handlers.onVision?.(payload as never);
    if (event === "comparison") handlers.onComparison?.(payload as never);
    if (event === "error") {
      const message = typeof payload === "object" && payload && "message" in payload ? String(payload.message) : String(payload);
      handlers.onError?.(message);
    }
    if (event === "done") handlers.onDone?.(payload as never);
  }

  async imageSearchUpload(uploadId: string, query: string, memory: Record<string, unknown> = {}) {
    return this.request<{
      product_cards: ProductCardData[];
      trace: unknown[];
      vision_analysis: Record<string, unknown>;
      object_candidates: unknown[];
      needs_clarification: boolean;
    }>("/api/image-search/upload", {
      method: "POST",
      body: { upload_id: uploadId, query, memory, limit: 8 },
    });
  }

  private async errorText(response: Response): Promise<string> {
    let text = "";
    try {
      const payload = await response.json();
      text = typeof payload?.detail === "string" ? payload.detail : JSON.stringify(payload);
    } catch {
      text = await response.text();
    }
    return `${response.status} ${response.statusText}${text ? `: ${text}` : ""}`;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
  skipAuth?: boolean;
  ops?: boolean;
}
