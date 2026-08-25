/**
 * Thin UCI client around the Stockfish WASM build served from
 * `public/stockfish/` (see `scripts/fetch-stockfish.mjs`).
 *
 * The engine runs in a Web Worker, so searches never block the UI thread. A
 * single instance is shared by the whole app: only one position is analyzed at
 * a time, and asking for a new one cancels the search in progress.
 */
import { parseInfoLine, toEngineLine } from "./uci";
import type { EngineAnalysis, EngineLine } from "./types";

const ENGINE_DIR = `${import.meta.env.BASE_URL}stockfish/`;

/** Multi-threaded builds need SharedArrayBuffer, i.e. a cross-origin isolated page. */
function canUseThreads(): boolean {
  return (
    typeof SharedArrayBuffer !== "undefined" &&
    typeof crossOriginIsolated !== "undefined" &&
    crossOriginIsolated === true
  );
}

function engineUrl(): string {
  const file = canUseThreads()
    ? "stockfish-18-lite.js"
    : "stockfish-18-lite-single.js";
  return `${ENGINE_DIR}${file}`;
}

export interface AnalyseOptions {
  /** Number of principal variations to report. */
  multiPv: number;
  /** Search stops once this depth is reached. */
  maxDepth: number;
}

export type AnalysisListener = (analysis: EngineAnalysis) => void;

interface Request {
  fen: string;
  options: AnalyseOptions;
  listener: AnalysisListener;
}

/** How long to wait for `uciok` / `readyok` before declaring the engine dead. */
const INIT_TIMEOUT_MS = 30_000;

export class StockfishEngine {
  private worker: Worker | null = null;
  private initPromise: Promise<void> | null = null;
  private lineHandlers = new Set<(line: string) => void>();

  /** The search currently running in the engine, if any. */
  private current: Request | null = null;
  /** Set while the engine has an unanswered `go`, i.e. no `bestmove` yet. */
  private searching = false;
  /** Latest requested position, started as soon as the engine goes idle. */
  private queued: Request | null = null;

  /** MultiPV value currently set on the engine, to avoid redundant setoptions. */
  private multiPv = 0;

  private lines = new Map<number, EngineLine>();
  private nps: number | null = null;

  /** True when the multi-threaded build could be used. */
  readonly threaded = canUseThreads();

  /** Boots the worker and completes the UCI handshake. Idempotent. */
  init(): Promise<void> {
    if (!this.initPromise) {
      this.initPromise = this.boot().catch((err) => {
        // Reset so a later retry can boot again (e.g. after `npm run engine:fetch`).
        this.initPromise = null;
        this.disposeWorker();
        throw err;
      });
    }
    return this.initPromise;
  }

  private async boot(): Promise<void> {
    const worker = new Worker(engineUrl());
    this.worker = worker;

    let onFatal: (err: Error) => void = () => {};
    const fatal = new Promise<never>((_, reject) => {
      onFatal = reject;
    });
    worker.onerror = (event) => {
      onFatal(
        new Error(
          event.message ||
            "Stockfish worker failed to load. Run `npm run engine:fetch`."
        )
      );
    };
    worker.onmessage = (event: MessageEvent) => {
      const line = typeof event.data === "string" ? event.data : String(event.data);
      for (const handler of this.lineHandlers) handler(line);
      this.handleLine(line);
    };

    const handshake = (async () => {
      this.send("uci");
      await this.waitFor((l) => l === "uciok");
      if (this.threaded) {
        const threads = Math.max(
          1,
          Math.min(4, (navigator.hardwareConcurrency || 2) - 1)
        );
        this.send(`setoption name Threads value ${threads}`);
      }
      this.send("setoption name Hash value 64");
      this.send("isready");
      await this.waitFor((l) => l === "readyok");
      this.send("ucinewgame");
    })();

    await Promise.race([handshake, fatal, this.timeout(INIT_TIMEOUT_MS)]);
    worker.onerror = null;
  }

  private timeout(ms: number): Promise<never> {
    return new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error("Stockfish did not answer in time.")),
        ms
      )
    );
  }

  private waitFor(predicate: (line: string) => boolean): Promise<string> {
    return new Promise((resolve) => {
      const handler = (line: string) => {
        if (predicate(line)) {
          this.lineHandlers.delete(handler);
          resolve(line);
        }
      };
      this.lineHandlers.add(handler);
    });
  }

  private send(command: string): void {
    this.worker?.postMessage(command);
  }

  /**
   * Analyzes `fen`, replacing any search in progress. `listener` is called
   * repeatedly as the search deepens, and one last time when it completes.
   */
  analyse(fen: string, options: AnalyseOptions, listener: AnalysisListener): void {
    const request: Request = { fen, options, listener };
    if (this.searching) {
      // Park the request; it starts when the running search acknowledges `stop`.
      this.queued = request;
      this.send("stop");
      return;
    }
    this.start(request);
  }

  private start(request: Request): void {
    this.current = request;
    this.queued = null;
    this.lines.clear();
    this.nps = null;

    if (this.multiPv !== request.options.multiPv) {
      this.multiPv = request.options.multiPv;
      this.send(`setoption name MultiPV value ${this.multiPv}`);
    }
    this.searching = true;
    this.send(`position fen ${request.fen}`);
    this.send(`go depth ${request.options.maxDepth}`);
    this.emit(false);
  }

  private handleLine(line: string): void {
    if (line.startsWith("bestmove")) {
      this.searching = false;
      if (this.queued) {
        this.start(this.queued);
      } else if (this.current) {
        this.emit(true);
      }
      return;
    }
    if (!this.current || this.queued) return;

    const info = parseInfoLine(line);
    if (!info) return;
    if (info.multipv > this.current.options.multiPv) return;

    this.lines.set(info.multipv, toEngineLine(this.current.fen, info));
    if (info.nps !== null) this.nps = info.nps;
    this.emit(false);
  }

  private emit(finished: boolean): void {
    const request = this.current;
    if (!request) return;
    const lines = [...this.lines.values()].sort((a, b) => a.multipv - b.multipv);
    request.listener({
      fen: request.fen,
      lines,
      depth: lines.length ? Math.max(...lines.map((l) => l.depth)) : 0,
      nps: this.nps,
      finished,
    });
  }

  /** Aborts the current search without tearing the engine down. */
  stop(): void {
    this.queued = null;
    this.current = null;
    if (this.searching) this.send("stop");
  }

  /** Terminates the worker. The instance can be re-`init()`ed afterwards. */
  destroy(): void {
    this.stop();
    this.disposeWorker();
    this.initPromise = null;
    this.multiPv = 0;
  }

  private disposeWorker(): void {
    if (!this.worker) return;
    this.worker.onmessage = null;
    this.worker.onerror = null;
    this.worker.terminate();
    this.worker = null;
    this.lineHandlers.clear();
    this.searching = false;
  }
}

let shared: StockfishEngine | null = null;

/**
 * Returns the process-wide engine instance, creating it on first use. Sharing
 * one worker avoids paying the ~7 MB WASM compile cost per component.
 */
export function getEngine(): StockfishEngine {
  if (!shared) shared = new StockfishEngine();
  return shared;
}
