export type ConnectionStatus = "untested" | "testing" | "connected" | "error";

export type ModelProviderConfig = {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  modelNames: string[];
  connectionStatus: ConnectionStatus;
};

export type BuiltInModel = {
  id: string;
  name: string;
  provider: string;
  description: string;
  category: string;
  pricing: "free" | "paid";
  price: number;
  purchased: boolean;
  contextWindow: string;
  speed: string;
  rating: number;
  downloads: number;
};

export function createProviderConfig(): ModelProviderConfig {
  return {
    id: crypto.randomUUID(),
    name: "",
    baseUrl: "",
    apiKey: "",
    modelNames: [],
    connectionStatus: "untested"
  };
}

export function emptyProviderForm(): Omit<ModelProviderConfig, "id" | "connectionStatus"> {
  return {
    name: "",
    baseUrl: "",
    apiKey: "",
    modelNames: []
  };
}

export const builtInModels: BuiltInModel[] = [
  {
    id: "dromx-fast",
    name: "DromX Fast",
    provider: "DromX Labs",
    description: "Lightweight general-purpose model optimized for quick responses and low latency.",
    category: "Chat",
    pricing: "free",
    price: 0,
    purchased: true,
    contextWindow: "32K tokens",
    speed: "~180 t/s",
    rating: 4.6,
    downloads: 12400
  },
  {
    id: "dromx-pro",
    name: "DromX Pro",
    provider: "DromX Labs",
    description: "Advanced reasoning model with deep context understanding for complex analytical workflows.",
    category: "Chat",
    pricing: "paid",
    price: 9.99,
    purchased: false,
    contextWindow: "128K tokens",
    speed: "~85 t/s",
    rating: 4.9,
    downloads: 8930
  },
  {
    id: "dromx-code",
    name: "DromX Coder",
    provider: "DromX Labs",
    description: "Specialized code generation and refactoring model with multi-language support.",
    category: "Code",
    pricing: "paid",
    price: 14.99,
    purchased: false,
    contextWindow: "64K tokens",
    speed: "~95 t/s",
    rating: 4.7,
    downloads: 5640
  },
  {
    id: "dromx-embed",
    name: "DromX Embed v2",
    provider: "DromX Labs",
    description: "High-quality text embedding model for semantic search and retrieval-augmented generation.",
    category: "Embedding",
    pricing: "free",
    price: 0,
    purchased: true,
    contextWindow: "8K tokens",
    speed: "~500 t/s",
    rating: 4.4,
    downloads: 18200
  },
  {
    id: "dromx-vision",
    name: "DromX Vision",
    provider: "DromX Labs",
    description: "Multimodal model for image understanding, OCR, and visual reasoning.",
    category: "Vision",
    pricing: "paid",
    price: 19.99,
    purchased: false,
    contextWindow: "32K tokens + images",
    speed: "~60 t/s",
    rating: 4.5,
    downloads: 3210
  },
  {
    id: "dromx-reasoner",
    name: "DromX Reasoner",
    provider: "DromX Labs",
    description: "Chain-of-thought reasoning model for proofs, logic, and multi-step problem decomposition.",
    category: "Chat",
    pricing: "paid",
    price: 24.99,
    purchased: false,
    contextWindow: "64K tokens",
    speed: "~40 t/s",
    rating: 4.8,
    downloads: 2760
  }
];
