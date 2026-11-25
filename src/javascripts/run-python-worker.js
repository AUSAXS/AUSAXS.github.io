// Runs the Python examples of run-python.js in Pyodide, off the main thread so the page stays responsive.
//
// pyAUSAXS is installed from PyPI with micropip, which picks the Pyodide wheel (platform tag pyemscripten_*_wasm32).
// The Pyodide version must match the ABI of that wheel: Pyodide 314.x is pyemscripten_2026_0. When pyAUSAXS moves to
// a new ABI (ABI in its .github/workflows/build-pyodide-wheel.yml), move the version here and in
// tests/examples/package.json with it. Until then, micropip keeps installing the newest wheel built for this ABI.
//
// Messages in:  {id, code, page, chain, fresh, setup}, run one block in the namespace of a chain of blocks of page, a
//               new one if fresh, which first runs the code setup (see run_python.py).
// Messages out: {id, type: "status", text}, {id, type: "stdout" | "stderr", text} for each line printed,
//               {id, type: "done", error, figures}, with error null or a traceback, and figures base64 PNGs.

import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.8/full/pyodide.mjs";

// the structure and data files the examples read, written to the working directory
const FILES = ["2epe.pdb", "2epe.dat", "Ag_crystal.cif"];
const DATA = new URL("../assets/examples/", import.meta.url);
const HELPER = new URL("run_python.py", import.meta.url);

let current = null; // id of the running block, which printed output belongs to
let quiet = false;   // drop the output of the setup, such as micropip's "Loaded numpy"
let runtime = null; // promise of {pyodide, run}
let queue = Promise.resolve();

const post = (id, type, fields) => self.postMessage({ id, type, ...fields });
const print = (type) => (text) => quiet || post(current, type, { text });

async function start() {
    post(current, "status", { text: "Starting Python…" });
    const pyodide = await loadPyodide({ stdout: print("stdout"), stderr: print("stderr") });

    post(current, "status", { text: "Loading pyAUSAXS…" });
    quiet = true;
    await pyodide.loadPackage("micropip", { messageCallback: () => {} });
    await pyodide.runPythonAsync("import micropip\nawait micropip.install('pyausaxs')");

    const fetchBytes = async (url) => {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`could not fetch ${url}: ${response.status}`);
        return new Uint8Array(await response.arrayBuffer());
    };
    const home = pyodide.runPython("import os; os.getcwd()");
    for (const name of FILES) pyodide.FS.writeFile(`${home}/${name}`, await fetchBytes(new URL(name, DATA)));

    const helper = pyodide.globals.get("dict")();
    pyodide.runPython(new TextDecoder().decode(await fetchBytes(HELPER)), { globals: helper });
    quiet = false;
    return { pyodide, run: helper.get("run") };
}

async function handle({ id, code, page, chain, fresh, setup }) {
    current = id;
    try {
        runtime ??= start();
        const { pyodide, run } = await runtime.catch((e) => { runtime = null; quiet = false; throw e; });
        await pyodide.loadPackagesFromImports(`${setup}\n${code}`, {
            messageCallback: (text) => text.startsWith("Loading ") && post(id, "status", { text: `${text}…` }),
        });
        post(id, "status", { text: "Running…" });
        const result = await run(code, page, chain, fresh, setup);
        const { error, figures } = result.toJs({ dict_converter: Object.fromEntries });
        result.destroy();
        post(id, "done", { error, figures });
    } catch (e) {
        post(id, "done", { error: String(e?.message ?? e), figures: [] });
    }
}

self.onmessage = ({ data }) => { queue = queue.then(() => handle(data)); };
