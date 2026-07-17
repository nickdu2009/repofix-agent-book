const PYODIDE_VERSION = "314.0.2";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MAX_SOURCE_LENGTH = 8_000;
const EXECUTION_TIMEOUT_MS = 30_000;

const WORKER_SOURCE = `
const PYODIDE_BASE = ${JSON.stringify(PYODIDE_BASE)};

self.onmessage = async (event) => {
  const code = event.data.code;
  const stdout = [];
  const stderr = [];
  try {
    const { loadPyodide } = await import(PYODIDE_BASE + "pyodide.mjs");
    const pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
    pyodide.setStdout({ batched: (text) => stdout.push(text) });
    pyodide.setStderr({ batched: (text) => stderr.push(text) });
    const value = await pyodide.runPythonAsync(code);
    let expression = "";
    if (value !== undefined && value !== null) {
      expression = String(value);
      if (typeof value.destroy === "function") value.destroy();
    }
    self.postMessage({ type: "result", stdout, stderr, expression });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  }
};
`;

function mountRunner(root) {
  if (root.dataset.runnerMounted === "true") return;
  const editor = root.querySelector("[data-runner-code]");
  const button = root.querySelector("[data-runner-run]");
  const status = root.querySelector("[data-runner-status]");
  const output = root.querySelector("[data-runner-output]");
  if (!editor || !button || !status || !output) return;
  root.dataset.runnerMounted = "true";

  button.addEventListener("click", () => {
    const code = editor.value;
    if (code.length > MAX_SOURCE_LENGTH) {
      output.textContent = `源码超过 ${MAX_SOURCE_LENGTH} 字符限制。`;
      return;
    }

    const workerURL = URL.createObjectURL(
      new Blob([WORKER_SOURCE], { type: "text/javascript" }),
    );
    const worker = new Worker(workerURL, { type: "module" });
    button.disabled = true;
    root.setAttribute("aria-busy", "true");
    status.textContent = `正在加载 Pyodide ${PYODIDE_VERSION}…`;
    output.textContent = "";

    let settled = false;
    const finish = (message, isError = false) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      worker.terminate();
      URL.revokeObjectURL(workerURL);
      button.disabled = false;
      root.removeAttribute("aria-busy");
      status.textContent = isError ? "运行失败" : "运行完成";
      output.textContent = message || "（无输出）";
    };

    const timer = setTimeout(() => {
      finish("执行超过 30 秒，Worker 已终止。", true);
    }, EXECUTION_TIMEOUT_MS);

    worker.onmessage = (event) => {
      if (event.data.type === "error") {
        finish(event.data.message, true);
        return;
      }
      const lines = [
        ...event.data.stdout,
        ...event.data.stderr.map((line) => `stderr: ${line}`),
      ];
      if (event.data.expression) lines.push(event.data.expression);
      finish(lines.join("\n"));
    };
    worker.onerror = (event) => {
      finish(event.message || "无法加载浏览器 Python 运行时。", true);
    };
    worker.postMessage({ code });
  });
}

function mountAllRunners() {
  document.querySelectorAll(".repofix-python-runner").forEach(mountRunner);
}

if (
  typeof document$ !== "undefined" &&
  document$ &&
  typeof document$.subscribe === "function"
) {
  document$.subscribe(mountAllRunners);
} else if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountAllRunners, { once: true });
} else {
  mountAllRunners();
}
