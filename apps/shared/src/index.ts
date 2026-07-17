/**
 * Shared types and utilities for Cyberfox dashboard ↔ gateway communication.
 */

// ── Connection state ──────────────────────────────────────────────────

export type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

// ── Gateway events ────────────────────────────────────────────────────

export interface GatewayEvent {
  type: string;
  session_id?: string;
  payload?: unknown;
}

export type GatewayEventName = string;

// ── WebSocket URL builder ─────────────────────────────────────────────

export interface BuildCyberfoxWebSocketUrlOpts {
  authParam: [string, string];
  basePath: string;
  path: string;
  params?: Record<string, string>;
}

/**
 * Build an absolute ``wss?://`` URL for a Cyberfox gateway WebSocket endpoint.
 *
 * The URL follows the pattern:
 *   wss://<host><basePath><path>?<authParamName>=<authParamValue>[&key=value...]
 */
export function buildCyberfoxWebSocketUrl(opts: BuildCyberfoxWebSocketUrlOpts): string {
  const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = typeof window !== "undefined" ? window.location.host : "localhost";

  const basePath = opts.basePath.replace(/\/+$/, "");
  const path = opts.path.startsWith("/") ? opts.path : `/${opts.path}`;

  const qs = new URLSearchParams();
  qs.set(opts.authParam[0], opts.authParam[1]);
  if (opts.params) {
    for (const [k, v] of Object.entries(opts.params)) {
      qs.set(k, v);
    }
  }

  return `${proto}//${host}${basePath}${path}?${qs.toString()}`;
}

// ── JSON-RPC Gateway Client ───────────────────────────────────────────

export interface JsonRpcGatewayClientOpts {
  closedErrorMessage: string;
  connectErrorMessage: string;
  notConnectedErrorMessage: string;
  requestIdPrefix: string;
}

interface JsonRpcRequest {
  id: string;
  method: string;
  params: unknown;
}

interface JsonRpcResponse {
  id: string;
  result?: unknown;
  error?: { code: number; message: string };
}

interface JsonRpcEvent {
  method: "event";
  params: { type: string; session_id?: string; payload?: unknown };
}

type Listener = (event: GatewayEvent) => void;
type StateListener = (state: ConnectionState) => void;

let _nextId = 0;
const nextId = (prefix: string) => `${prefix}${++_nextId}`;

/**
 * Minimal WebSocket JSON-RPC client matching the Cyberfox gateway protocol.
 *
 * Wire format: newline-delimited JSON-RPC 2.0 in both directions.
 */
export class JsonRpcGatewayClient {
  protected connectionState: ConnectionState = "idle";

  private opts: JsonRpcGatewayClientOpts;
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<Listener>> = new Map();
  private stateListeners: Set<StateListener> = new Set();
  private pending: Map<string, { resolve: (v: unknown) => void; reject: (e: Error) => void; timer: ReturnType<typeof setTimeout> }> = new Map();
  private requestTimeout = 120_000;

  constructor(opts: JsonRpcGatewayClientOpts) {
    this.opts = opts;
  }

  // ── Public API ────────────────────────────────────────────────────

  async connect(url: string): Promise<void> {
    if (this.connectionState === "open" || this.connectionState === "connecting") {
      return;
    }

    this.setState("connecting");

    return new Promise<void>((resolve, reject) => {
      try {
        const ws = new WebSocket(url);
        this.ws = ws;

        ws.onopen = () => {
          this.setState("open");
          resolve();
        };

        ws.onerror = () => {
          if (this.connectionState === "connecting") {
            this.setState("error");
            reject(new Error(this.opts.connectErrorMessage));
          }
        };

        ws.onclose = () => {
          const wasOpen = this.connectionState === "open";
          this.setState("closed");
          this.rejectAllPending(this.opts.closedErrorMessage);
          if (wasOpen) {
            for (const [, s] of this.listeners) {
              for (const fn of s) {
                fn({ type: "connection.closed" });
              }
            }
          }
        };

        ws.onmessage = (ev: MessageEvent) => {
          const raw = typeof ev.data === "string" ? ev.data : new TextDecoder().decode(ev.data);
          for (const line of raw.split("\n")) {
            if (!line.trim()) continue;
            try {
              const msg = JSON.parse(line) as JsonRpcResponse | JsonRpcEvent;
              if ("id" in msg && msg.id) {
                this.handleResponse(msg as JsonRpcResponse);
              } else if ("method" in msg && msg.method === "event") {
                this.handleEvent((msg as JsonRpcEvent).params);
              }
            } catch {
              // skip malformed lines
            }
          }
        };
      } catch (err) {
        this.setState("error");
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    });
  }

  close(): void {
    if (this.ws) {
      try { this.ws.close(); } catch { /* ignore */ }
      this.ws = null;
    }
    this.rejectAllPending("client closed");
    this.setState("closed");
  }

  async request<T = unknown>(method: string, params: unknown = {}): Promise<T> {
    if (this.connectionState !== "open" || !this.ws) {
      throw new Error(this.opts.notConnectedErrorMessage);
    }

    const id = nextId(this.opts.requestIdPrefix);
    const frame: JsonRpcRequest = { id, method, params };

    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`request ${method} timed out`));
      }, this.requestTimeout);

      this.pending.set(id, {
        resolve: resolve as (v: unknown) => void,
        reject,
        timer,
      });

      this.ws!.send(JSON.stringify(frame));
    });
  }

  on<T = GatewayEvent>(eventType: string, listener: (event: T) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    const wrapped = listener as Listener;
    this.listeners.get(eventType)!.add(wrapped);
    return () => {
      this.listeners.get(eventType)?.delete(wrapped);
    };
  }

  onState(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    // Emit current state immediately
    listener(this.connectionState);
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  // ── Internal ──────────────────────────────────────────────────────

  private setState(state: ConnectionState): void {
    if (this.connectionState === state) return;
    this.connectionState = state;
    for (const fn of this.stateListeners) {
      fn(state);
    }
  }

  private handleResponse(msg: JsonRpcResponse): void {
    const p = this.pending.get(msg.id);
    if (!p) return;
    this.pending.delete(msg.id);
    clearTimeout(p.timer);
    if (msg.error) {
      p.reject(new Error(`RPC error ${msg.error.code}: ${msg.error.message}`));
    } else {
      p.resolve(msg.result);
    }
  }

  private handleEvent(params: { type: string; session_id?: string; payload?: unknown }): void {
    const s = this.listeners.get(params.type);
    if (s) {
      for (const fn of s) {
        fn({ type: params.type, session_id: params.session_id, payload: params.payload });
      }
    }
    // Also emit to wildcard listeners
    const wild = this.listeners.get("*");
    if (wild) {
      for (const fn of wild) {
        fn({ type: params.type, session_id: params.session_id, payload: params.payload });
      }
    }
  }

  private rejectAllPending(msg: string): void {
    for (const [id, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(new Error(msg));
    }
    this.pending.clear();
  }
}
