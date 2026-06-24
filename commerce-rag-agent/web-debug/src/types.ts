export type Role = "user" | "assistant" | "system";

export interface AuthConfig {
  baseUrl: string;
  userId: string;
  roles: string;
  token: string;
  opsApiKey: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  updatedAt: string;
}

export interface ProductCardData {
  product_id?: string;
  id?: string;
  title: string;
  category?: string;
  subcategory?: string;
  subtitle?: string;
  price?: number;
  image_url?: string;
  rating?: number;
  sales?: number;
  stock_status?: string;
  stock?: number;
  reasons?: string[];
  score?: number;
}

export interface VisionObjectCandidate {
  id?: string;
  label: string;
  category?: string;
  subcategory?: string;
  confidence?: number;
  bbox?: number[] | null;
  search_query?: string;
}

export interface ProductReviewSummary {
  product_id: string;
  title: string;
  total_reviews: number;
  avg_rating: number;
  rating_histogram: Record<string, number>;
  positive_tags: Array<{ tag: string; count: number }>;
  risk_tags: Array<{ tag: string; count: number }>;
  dimensions: Array<{ name: string; total: number; positive: number; negative: number; sentiment: string }>;
  representative_reviews: Array<{ id: string; rating: number; content: string; dimension_tags: string[]; created_at: string }>;
  insight?: Record<string, unknown>;
  source: string;
}

export interface ProductQuestions {
  product_id: string;
  pending_count: number;
  questions: Array<{
    id: string;
    question: string;
    answer: string;
    status: string;
    helpful_count: number;
    created_at: string;
    answered_at?: string;
  }>;
}

export interface UserProductCollectionItem {
  id: string;
  list_type: "favorite" | "compare" | "recent";
  view_count: number;
  updated_at: string;
  product: ProductCardData;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt?: string;
  productCards?: ProductCardData[];
  feedbackEnabled?: boolean;
  feedbackReasons?: Array<{ id: string; label: string }>;
}

export interface StreamStatus {
  stage: string;
  label: string;
  session_id?: string;
}

export interface CartItem {
  cart_item_id: string;
  product_id: string;
  sku_id?: string;
  title: string;
  category?: string;
  subcategory?: string;
  image_url?: string;
  quantity: number;
  unit_price: number;
  subtotal_amount: number;
  stock?: number;
  specs?: Record<string, unknown>;
}

export interface CartState {
  user_id?: string;
  items: CartItem[];
  total_quantity: number;
  subtotal_amount: number;
}

export interface CheckoutPreview {
  checkout_id: string;
  status: string;
  items: CartItem[];
  subtotal_amount: number;
  discount_amount: number;
  shipping_fee: number;
  payable_amount: number;
  address_id: string;
  confirm_token: string;
  expires_at: string;
  price_snapshot_ttl_seconds: number;
}

export interface OrderResult {
  order_id: string;
  checkout_id: string;
  status: string;
  payment_status: string;
  payable_amount: number;
  payment_url?: string;
  items: CartItem[];
}

export interface UploadResult {
  upload_id: string;
  local_path: string;
  preview_url: string;
}

export interface AsrResult {
  text: string;
  provider: string;
  model: string;
  language?: string;
  duration?: number | null;
  raw?: Record<string, unknown>;
}

export interface VoiceCapabilities {
  asr?: {
    provider?: string;
    configured?: boolean;
    model?: string;
    mode?: string;
    max_audio_mb?: number;
  };
  tts?: {
    provider?: string;
    configured?: boolean;
    model?: string;
    voice?: string;
    format?: string;
    mode?: string;
    max_text_chars?: number;
  };
  browser_fallback?: Record<string, boolean>;
}

export interface HealthPayload {
  status?: string;
  trace_id?: string;
  checks?: Record<string, unknown>;
  warnings?: string[];
  [key: string]: unknown;
}

export interface OpsMetrics {
  traffic?: Record<string, number>;
  retrieval?: Record<string, unknown>;
  recommendation?: Record<string, unknown>;
  commerce?: Record<string, unknown>;
  quality?: Record<string, unknown>;
  behavior?: Record<string, unknown>;
  alerts?: Record<string, number>;
}

export interface OpsDashboard {
  window?: Record<string, unknown>;
  kpis?: Record<string, number>;
  funnel?: Array<{ stage: string; count: number }>;
  retrieval?: Record<string, unknown>;
  image_search?: Record<string, unknown>;
  feedback?: Record<string, unknown>;
  products?: Record<string, unknown>;
  alerts?: Record<string, number>;
  raw_metrics?: OpsMetrics;
}

export interface StreamHandlers {
  onStatus?: (payload: StreamStatus) => void;
  onMessageStart?: (payload: Record<string, unknown>) => void;
  onMessageDelta?: (payload: Record<string, unknown>) => void;
  onMessage?: (payload: Record<string, unknown>) => void;
  onTrace?: (payload: unknown[]) => void;
  onProducts?: (payload: ProductCardData[]) => void;
  onCart?: (payload: CartState) => void;
  onVision?: (payload: Record<string, unknown>) => void;
  onComparison?: (payload: Record<string, unknown>) => void;
  onError?: (message: string) => void;
  onDone?: (payload: Record<string, unknown>) => void;
  onRaw?: (event: string, payload: unknown) => void;
}
