# Third-party software

## Stockfish

The position evaluation shown next to the board is computed by
[Stockfish](https://github.com/official-stockfish/Stockfish), compiled to
WebAssembly by [stockfish.js](https://github.com/nmrugg/stockfish.js)
(version 18.0.8, the "lite" builds).

- **Licence:** GNU General Public License v3.0 or later.
  The full text is served with the engine at `/stockfish/LICENSE.txt`, and is
  downloaded alongside the binaries by `frontend/scripts/fetch-stockfish.mjs`.
- **Copyright:** Stockfish is © T. Romstad, M. Costalba, J. Kiiski, G. Linscott
  and the Stockfish contributors. The WebAssembly build is © Chess.com, LLC.
  The neural network is by Linmiao Xu (linrock).
- **Corresponding source:**
  - Engine — <https://github.com/official-stockfish/Stockfish>
  - WebAssembly build — <https://github.com/nmrugg/stockfish.js>
  - Exact version distributed here — <https://www.npmjs.com/package/stockfish/v/18.0.8>

### Why this matters here

The GPL's obligations are triggered by *distribution*, and this application
distributes: the `.wasm` engine is downloaded and executed by every visitor's
browser. So the engine must reach them together with its copyright notices, its
licence, and a way to obtain its source — which is what the list above provides.

The engine files are served verbatim from `frontend/public/stockfish/`. They are
never bundled, rewritten or minified by Vite, so the GPL header at the top of
each build is delivered intact.

### Scope of the copyleft

Stockfish runs in its own Web Worker and exchanges only UCI text messages with
the application (see `frontend/src/engine/stockfish.ts`). The two are separate
programs communicating at arm's length rather than a single combined work, so
the application's own source is not placed under the GPL by this integration.

This reflects the common reading of the GPL for this kind of integration; it is
not legal advice. Have it reviewed if the stakes warrant it.
