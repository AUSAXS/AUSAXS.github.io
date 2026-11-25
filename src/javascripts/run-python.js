// Run buttons for the Python examples. A code block written as ```python {.run} gets a Run button, which runs it in the
// browser with Pyodide and pyAUSAXS (see run-python-worker.js); nothing is installed and no server is involved.
//
// The runnable blocks of a page share one namespace, like the cells of a notebook, so a block can use what the blocks
// above it defined: running a block first runs the blocks above it that have not run yet. The code can be edited
// before it is run. tests/examples/run_examples.mjs runs every block the same way under Node.js.

(() => {
    const workerUrl = new URL("run-python-worker.js", document.currentScript.src);
    let worker = null;
    let nextId = 0;
    let pages = 0; // each page gets its own namespace, also after instant navigation
    const handlers = new Map(); // id of a sent block -> function receiving its messages

    function send(code, page, onMessage) {
        if (!worker) {
            worker = new Worker(workerUrl, { type: "module" });
            worker.onmessage = ({ data }) => handlers.get(data.id)?.(data);
            worker.onerror = (e) => {
                // the worker failed to load, e.g. the CDN is blocked: fail everything sent, and start over next time
                for (const handle of handlers.values()) handle({ type: "done", error: `Could not start Python: ${e.message || "network error"}`, figures: [] });
                handlers.clear();
                worker = null;
            };
        }
        const id = nextId++;
        return new Promise((resolve) => {
            handlers.set(id, (message) => {
                onMessage(message);
                if (message.type === "done") {
                    handlers.delete(id);
                    resolve(!message.error);
                }
            });
            worker.postMessage({ id, code, page });
        });
    }

    // AUSAXS colours its log with ANSI escapes. Its log lines are shown muted and its warnings highlighted, which
    // keeps them apart from the example's own output.
    const ANSI = /\x1b\[([\d;]*)m/g;
    function ansiClass(codes, previous) {
        let cls = previous;
        for (const code of codes.split(";").map(Number)) {
            if (code === 0) cls = "";
            else if ([31, 33, 91, 93].includes(code)) cls = "ausaxs-run__warn";
            else if ((code >= 30 && code <= 37) || (code >= 90 && code <= 97)) cls = "ausaxs-run__log";
        }
        return cls;
    }

    class Block {
        constructor(div, cell) {
            this.cell = cell;
            this.code = div.querySelector("code");
            this.original = this.code.innerHTML;
            this.ran = false;

            this.code.contentEditable = "plaintext-only";
            this.code.spellcheck = false;
            this.code.setAttribute("aria-label", "Python code, editable");
            this.code.addEventListener("input", () => { this.reset.hidden = false; });

            const bar = document.createElement("div");
            bar.className = "ausaxs-run__bar";
            this.button = Object.assign(document.createElement("button"), { type: "button", className: "ausaxs-run__button", textContent: "Run" });
            this.button.title = "Run this example in your browser";
            this.button.addEventListener("click", () => cell.run(this));
            this.reset = Object.assign(document.createElement("button"), { type: "button", className: "ausaxs-run__reset", textContent: "Reset code", hidden: true });
            this.reset.addEventListener("click", () => {
                this.code.innerHTML = this.original;
                this.reset.hidden = true;
            });
            this.status = Object.assign(document.createElement("span"), { className: "ausaxs-run__status" });
            bar.append(this.button, this.reset, this.status);

            this.output = Object.assign(document.createElement("div"), { className: "ausaxs-run__output", hidden: true });
            this.output.setAttribute("aria-live", "polite");
            div.after(bar, this.output);
        }

        setStatus(text) { this.status.textContent = text; }

        print(text, stream) {
            if (!this.text) {
                this.text = document.createElement("pre");
                this.output.append(this.text);
                this.output.hidden = false;
            }
            const line = document.createDocumentFragment();
            let cls = stream === "stderr" ? "ausaxs-run__warn" : this.ansi;
            let at = 0;
            const append = (part) => {
                if (!part) return;
                const span = document.createElement("span");
                span.className = cls;
                span.textContent = part;
                line.append(span);
            };
            for (const match of text.matchAll(ANSI)) {
                append(text.slice(at, match.index));
                cls = ansiClass(match[1], cls);
                at = match.index + match[0].length;
            }
            append(text.slice(at) + "\n");
            if (stream !== "stderr") this.ansi = cls;
            this.text.append(line);
        }

        async execute() {
            this.output.replaceChildren();
            this.output.hidden = true;
            this.text = null;
            this.ansi = "";
            this.button.disabled = true;
            this.setStatus("Running…");
            const ok = await send(this.code.innerText, this.cell.page, (message) => {
                if (message.type === "status") this.setStatus(message.text);
                else if (message.type === "stdout" || message.type === "stderr") this.print(message.text, message.type);
                else if (message.type === "done") {
                    if (message.error) {
                        const error = Object.assign(document.createElement("pre"), { className: "ausaxs-run__error", textContent: message.error });
                        this.output.append(error);
                    }
                    for (const png of message.figures) {
                        const img = Object.assign(document.createElement("img"), { src: `data:image/png;base64,${png}`, alt: "Figure produced by the example" });
                        this.output.append(img);
                    }
                    this.output.hidden = !this.output.childElementCount;
                }
            });
            this.button.disabled = false;
            this.ran = ok;
            this.setStatus(ok ? "" : "Failed");
            return ok;
        }
    }

    // The runnable blocks of one page. Runs are queued, so they always happen in the order they were asked for.
    class Notebook {
        constructor(divs) {
            this.page = ++pages;
            this.blocks = divs.map((div) => new Block(div, this));
            this.queue = Promise.resolve();
        }

        run(block) {
            const upTo = this.blocks.indexOf(block);
            for (const b of this.blocks.slice(0, upTo + 1)) if (!b.ran || b === block) b.setStatus("Waiting…");
            this.queue = this.queue.then(async () => {
                for (const b of this.blocks.slice(0, upTo)) {
                    if (b.ran) continue;
                    if (!(await b.execute())) {
                        for (const later of this.blocks.slice(this.blocks.indexOf(b) + 1, upTo + 1)) later.setStatus("");
                        block.setStatus("An example above failed");
                        return;
                    }
                }
                await block.execute();
            });
        }
    }

    document$.subscribe(({ body }) => {
        const divs = [...body.querySelectorAll("div.highlight.run")];
        if (divs.length) new Notebook(divs);
    });
})();
