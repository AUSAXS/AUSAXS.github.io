// Run the runnable Python examples of the site (```python {.run} blocks) in Pyodide under Node.js, the way the Run
// buttons run them in the browser (src/javascripts/run-python-worker.js), and fail on the first error.
//
// Usage: node run_examples.mjs [--wheel <pyausaxs wheel>] [--figures <folder>] [page.md ...]
//   --wheel    install this pyAUSAXS wheel instead of the latest one on PyPI, to test a wheel before its release
//   --figures  save the figures of the blocks in this folder, as <page>-<block>-<figure>.png (.gif for
//              an animation), to look them over
//   pages    the pages to run; default every page in src/ with a runnable block
//
// The blocks of a page run in order. A standalone block (```python {.run}) starts a new namespace, and the continuing
// blocks after it (```python {.run .continue}) share it, as in the browser. A new namespace first runs the setup blocks
// of the page (```python {.run .setup}).

import { loadPyodide, version } from "pyodide";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const src = join(root, "src");
const scripts = join(src, "javascripts");

const args = process.argv.slice(2);
const wheelAt = args.indexOf("--wheel");
const wheel = wheelAt >= 0 ? args.splice(wheelAt, 2)[1] : null;
const figuresAt = args.indexOf("--figures");
const figureDir = figuresAt >= 0 ? resolve(args.splice(figuresAt, 2)[1]) : null;
if (figureDir) mkdirSync(figureDir, { recursive: true });
const pages = args.length ? args.map((p) => resolve(p)) : readdirSync(src, { recursive: true })
    .filter((p) => p.endsWith(".md")).map((p) => join(src, p)).sort();

// the browser loads Pyodide from the CDN at the version in the worker; test the same one
const worker = readFileSync(join(scripts, "run-python-worker.js"), "utf8");
const browserVersion = worker.match(/pyodide\/v([\d.]+)\//)[1];
if (browserVersion !== version) {
    console.error(`the worker uses Pyodide ${browserVersion}, but ${version} is installed here; update package.json`);
    process.exit(1);
}

// a block can be indented, e.g. in a content tab; its code is then dedented by the indent of its fence
const blocksOf = (page) => [...readFileSync(page, "utf8").matchAll(/^( *)```python \{\.run( \.continue| \.setup)?\}\n([\s\S]*?)^\1```$/gm)]
    .map(([, indent, kind, code]) => ({
        kind: kind?.trim().slice(1) ?? "standalone",
        code: code.split("\n").map((line) => line.slice(indent.length)).join("\n"),
    }));

const pyodide = await loadPyodide();
await pyodide.loadPackage("micropip");
if (wheel) pyodide.FS.writeFile(`/tmp/${basename(wheel)}`, readFileSync(wheel));
await pyodide.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheel ? `emfs:/tmp/${basename(wheel)}` : "pyausaxs")})`);

const files = join(src, "assets", "examples");
const home = pyodide.runPython("import os; os.getcwd()");
for (const name of readdirSync(files)) pyodide.FS.writeFile(`${home}/${name}`, readFileSync(join(files, name)));

const helper = pyodide.globals.get("dict")();
pyodide.runPython(readFileSync(join(scripts, "run_python.py"), "utf8"), { globals: helper });
const run = helper.get("run");
console.log(`Pyodide ${version}, pyAUSAXS ${pyodide.runPython("import pyausaxs; pyausaxs.__version__")}`);

let count = 0;
for (const page of pages) {
    const all = blocksOf(page);
    const setup = all.filter((b) => b.kind === "setup").map((b) => b.code).join("\n");
    const blocks = all.filter((b) => b.kind !== "setup");
    let chain = -1;
    for (const [i, { kind, code }] of blocks.entries()) {
        const name = `${relative(src, page)}, block ${i + 1} of ${blocks.length}`;
        const fresh = kind !== "continue" || chain < 0;
        if (fresh) chain++;
        await pyodide.loadPackagesFromImports(`${setup}\n${code}`, { messageCallback: () => {} });
        const start = performance.now();
        const result = (await run(code, page, chain, fresh, setup)).toJs({ dict_converter: Object.fromEntries });
        if (result.error) {
            console.error(`FAILED ${name}:\n${code}\n${result.error}`);
            process.exit(1);
        }
        if (figureDir) result.figures.forEach((url, j) => {
            const [, type, data] = url.match(/^data:image\/(\w+);base64,(.*)$/s);
            writeFileSync(join(figureDir, `${relative(src, page).replace(/[\/.]/g, "-")}-${i + 1}-${j + 1}.${type}`), Buffer.from(data, "base64"));
        });
        const figures = result.figures.length ? `, ${result.figures.length} figure(s)` : "";
        console.log(`passed ${name} (${((performance.now() - start) / 1000).toFixed(2)} s${figures})`);
        count++;
    }
}
console.log(`all ${count} blocks passed`);
