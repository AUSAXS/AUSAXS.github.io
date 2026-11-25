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
//               {id, type: "done", error, figures}, with error null or a traceback, and figures data: URLs, of PNG images or
//               of animated GIFs.
//
// The first run downloads some 25 MB (Pyodide, numpy, matplotlib, pyAUSAXS), which can take a minute. Those files never
// change at their URL, so they are kept in the Cache Storage of the site (see cachedFetch) rather than left to the HTTP
// cache, which may drop large files. That shows whether Python has been set up before, and while it downloads, the
// status counts the megabytes so far.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v314.0.8/full/";
const WHEELS = "https://files.pythonhosted.org/"; // pyAUSAXS from PyPI; its index on pypi.org is not cached
const CACHE = `ausaxs-python ${PYODIDE}`; // a new Pyodide version starts a new cache, and the old one is deleted

// the structure and data files the examples read, written to the working directory. The helper and the data are
// fetched with the version of this script (see hooks/asset_version.py), so a new deploy is not mixed with old files.
const versioned = (path) => Object.assign(new URL(path, import.meta.url), { search: new URL(import.meta.url).search });
const FILES = ["2epe.pdb", "2epe.dat", "Ag_crystal.cif"];
const DATA = "../assets/examples/";
const HELPER = versioned("run_python.py");

let current = null; // id of the running block, which printed output belongs to
let quiet = false;   // drop the output of the setup, such as micropip's "Loaded numpy"
let runtime = null; // promise of {pyodide, run}
let queue = Promise.resolve();

const post = (id, type, fields) => self.postMessage({ id, type, ...fields });
const print = (type) => (text) => quiet || post(current, type, { text });

// The files of PYODIDE and WHEELS are served from the cache, or downloaded and cached. Pyodide and micropip both use the
// global fetch, so replacing it covers them. Without Cache Storage (an insecure context, some private windows) it is
// the plain fetch.
const network = self.fetch.bind(self);
let cache = null; // promise of the Cache, or of null without one
const wheelsUsed = new Set(); // the pyAUSAXS wheels this setup fetched; the others are older releases
let step = null; // the step of the setup in progress, {downloading, bytes}, whose downloads the status counts

const openCache = () => cache ??= (async () => {
    try {
        for (const name of await caches.keys()) if (name.startsWith("ausaxs-python ") && name !== CACHE) await caches.delete(name);
        return await caches.open(CACHE);
    } catch {
        return null;
    }
})();

async function cachedFetch(resource, options) {
    const url = String(resource instanceof Request ? resource.url : resource);
    const method = options?.method ?? (resource instanceof Request ? resource.method : "GET");
    if (method !== "GET" || !(url.startsWith(PYODIDE) || url.startsWith(WHEELS))) return network(resource, options);
    if (url.startsWith(WHEELS)) wheelsUsed.add(url);
    const store = await openCache();
    const hit = await store?.match(url).catch(() => undefined);
    if (hit) return hit;
    const response = await network(resource, options);
    if (store && response.ok) {
        store.put(url, response.clone()).catch(() => {});
        countDownload(response.clone());
    }
    return response;
}
self.fetch = cachedFetch;

async function countDownload(response) {
    const counting = step;
    const reader = response.body.getReader();
    try {
        for (let chunk; !(chunk = await reader.read()).done;) {
            if (!counting || step !== counting) continue;
            const before = (counting.bytes / 1e6).toFixed(1);
            counting.bytes += chunk.value.length;
            const after = (counting.bytes / 1e6).toFixed(1);
            if (after !== before) post(current, "status", { text: `${counting.downloading} (only the first time): ${after} MB…` });
        }
    } catch {
        // the download failed; whoever fetched it reports that
    }
}

// Report a step of the setup: text while it runs from the cache, downloading once it downloads.
function startStep(text, downloading) {
    step = { downloading, bytes: 0 };
    post(current, "status", { text });
}

async function start() {
    const store = await openCache();
    const cached = !store || !!(await store.match(`${PYODIDE}pyodide.asm.wasm`).catch(() => undefined));
    startStep(cached ? "Starting Python…" : "Downloading Python (only the first time)…", "Downloading Python");
    const { loadPyodide } = await import(`${PYODIDE}pyodide.mjs`); // after self.fetch is replaced
    const pyodide = await loadPyodide({ stdout: print("stdout"), stderr: print("stderr") });

    startStep("Loading pyAUSAXS…", "Downloading pyAUSAXS");
    quiet = true;
    await pyodide.loadPackage("micropip", { messageCallback: () => {} });
    await pyodide.runPythonAsync("import micropip\nawait micropip.install('pyausaxs')");
    // keep only the pyAUSAXS release just installed
    if (store) for (const request of await store.keys()) {
        if (request.url.startsWith(WHEELS) && !wheelsUsed.has(request.url)) await store.delete(request).catch(() => {});
    }

    const fetchBytes = async (url) => {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`could not fetch ${url}: ${response.status}`);
        return new Uint8Array(await response.arrayBuffer());
    };
    const home = pyodide.runPython("import os; os.getcwd()");
    for (const name of FILES) pyodide.FS.writeFile(`${home}/${name}`, await fetchBytes(versioned(DATA + name)));

    const helper = pyodide.globals.get("dict")();
    pyodide.runPython(new TextDecoder().decode(await fetchBytes(HELPER)), { globals: helper });
    quiet = false;
    step = null;
    return { pyodide, run: helper.get("run") };
}

async function handle({ id, code, page, chain, fresh, setup }) {
    current = id;
    try {
        runtime ??= start();
        const { pyodide, run } = await runtime.catch((e) => { runtime = null; quiet = false; throw e; });
        await pyodide.loadPackagesFromImports(`${setup}\n${code}`, {
            messageCallback: (text) => {
                if (!text.startsWith("Loading ")) return;
                const names = text.slice(8).split(", ");
                startStep(`${text}…`, `Downloading ${names.length > 3 ? `${names.length} packages` : names.join(", ")}`);
            },
        });
        step = null;
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
