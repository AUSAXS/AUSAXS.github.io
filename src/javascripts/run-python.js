// Run buttons for the Python examples. A code block written as ```python {.run} gets a Run button, which runs it in the
// browser with Pyodide and pyAUSAXS (see run-python-worker.js); nothing is installed and no server is involved.
//
// A block stands on its own, and runs in a fresh namespace each time. A block written as ```python {.run .continue}
// instead continues from the blocks above it, like the cells of a notebook: it shares the namespace of the nearest
// standalone block above it and of the continuing blocks between them, its chain, and running it first runs the blocks
// of its chain above it that have not run yet. Such a block is marked as continuing from above. The code can be edited
// before it is run.
//
// A setup block, ```python {.run .setup}, has no Run button: it runs at the start of every fresh namespace of its page,
// before the block that starts it. It holds code the examples share but that is not their point, such as plotting
// helpers, and is shown collapsed (in a ??? admonition). tests/examples/run_examples.mjs runs every block the same way under Node.js.

(() => {
    // the worker is fetched with the version of this script (see hooks/asset_version.py), so a deploy is not mixed with old files
    const workerUrl = new URL("run-python-worker.js", document.currentScript.src);
    workerUrl.search = new URL(document.currentScript.src).search;
    let worker = null;
    let nextId = 0;
    let pages = 0; // each page gets its own namespace, also after instant navigation
    const handlers = new Map(); // id of a sent block -> function receiving its messages

    function send(code, page, chain, fresh, setup, onMessage) {
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
            worker.postMessage({ id, code, page, chain, fresh, setup });
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
        constructor(div, cell, chain) {
            this.cell = cell;
            this.chain = chain; // the blocks sharing a namespace, headed by a standalone block
            chain.blocks.push(this);
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

            // a block that continues from the blocks above it is marked by an icon beside the copy button. Material adds
            // that button's nav to the pre when it mounts the block, which may be before or after this runs.
            if (!this.standalone) {
                const icon = Object.assign(document.createElement("span"), { className: "md-code__button ausaxs-run__continues" });
                icon.title = "Continues from above: this example uses what the examples above it define. Running it also runs those that have not run yet.";
                icon.setAttribute("role", "img");
                icon.setAttribute("aria-label", "Continues from above");
                const pre = div.querySelector("pre");
                const place = () => {
                    const nav = pre.querySelector(":scope > .md-code__nav");
                    if (nav) nav.prepend(icon);
                    return !!nav;
                };
                if (!place()) new MutationObserver((_, observer) => { if (place()) observer.disconnect(); }).observe(pre, { childList: true });
            }
        }

        get standalone() { return this.chain.blocks[0] === this; }

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
            // a standalone block starts its chain over, in a fresh namespace, so the blocks after it have to run again
            if (this.standalone) for (const b of this.chain.blocks) b.ran = false;
            // textContent, since innerText is empty while the setup is collapsed; it is not editable, so they agree
            const setup = this.standalone ? this.cell.setup.map((code) => code.textContent).join("\n") : "";
            const ok = await send(this.code.innerText, this.cell.page, this.chain.index, this.standalone, setup, (message) => {
                if (message.type === "status") this.setStatus(message.text);
                else if (message.type === "stdout" || message.type === "stderr") this.print(message.text, message.type);
                else if (message.type === "done") {
                    if (message.error) {
                        const error = Object.assign(document.createElement("pre"), { className: "ausaxs-run__error", textContent: message.error });
                        this.output.append(error);
                    }
                    for (const src of message.figures) {
                        const alt = src.startsWith("data:image/gif") ? "Animation produced by the example" : "Figure produced by the example";
                        const img = Object.assign(document.createElement("img"), { src, alt });
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

    // The runnable blocks of one page, in chains. Runs are queued, so they always happen in the order they were asked for.
    class Notebook {
        constructor(divs) {
            this.page = ++pages;
            this.setup = divs.filter((div) => div.classList.contains("setup")).map((div) => div.querySelector("code"));
            const chains = [];
            for (const div of divs.filter((div) => !div.classList.contains("setup"))) {
                if (!div.classList.contains("continue") || !chains.length) chains.push({ index: chains.length, blocks: [] });
                new Block(div, this, chains.at(-1));
            }
            this.queue = Promise.resolve();
        }

        run(block) {
            // the blocks of its chain above it that have not run yet, and then the block itself
            const above = (b) => !block.standalone && b.chain.blocks.indexOf(b) < block.chain.blocks.indexOf(block);
            for (const b of block.chain.blocks) if (b === block || (above(b) && !b.ran)) b.setStatus("Waiting…");
            this.queue = this.queue.then(async () => {
                const todo = [...block.chain.blocks.filter((b) => above(b) && !b.ran), block];
                for (const [i, b] of todo.entries()) {
                    if (!(await b.execute()) && b !== block) {
                        for (const later of todo.slice(i + 1)) later.setStatus("");
                        block.setStatus("An example above failed");
                        return;
                    }
                }
            });
        }
    }

    document$.subscribe(({ body }) => {
        const divs = [...body.querySelectorAll("div.highlight.run")];
        if (divs.length) new Notebook(divs);
    });
})();
