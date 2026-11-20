// Sealed PoC Verifier — frontend demo, local only.
// No network requests. PoC lives only in browser memory, is hashed
// locally with WebCrypto, and is never displayed back.
// The verdict here is a HEURISTIC DEMO, not a real verification.
// The real verdict comes from src/verifier.py (Foundry run).

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function readFileInto(inputEl, textareaEl) {
  const f = inputEl.files && inputEl.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => { textareaEl.value = reader.result; };
  reader.readAsText(f);
}

document.getElementById("targetFile").addEventListener("change", e =>
  readFileInto(e.target, document.getElementById("targetText")));
document.getElementById("pocFile").addEventListener("change", e =>
  readFileInto(e.target, document.getElementById("pocText")));

document.getElementById("clearBtn").addEventListener("click", () => {
  document.getElementById("targetText").value = "";
  document.getElementById("pocText").value = "";
  document.getElementById("targetFile").value = "";
  document.getElementById("pocFile").value = "";
  document.getElementById("output").textContent =
    "Memori dibersihkan. PoC dan target sudah dihapus dari halaman ini.";
});

document.getElementById("verifyBtn").addEventListener("click", async () => {
  const target = document.getElementById("targetText").value;
  const poc = document.getElementById("pocText").value;
  const out = document.getElementById("output");
  if (!target.trim() || !poc.trim()) {
    out.textContent = "Isi target dan PoC dulu.";
    return;
  }
  // Heuristic demo only: vulnerable pattern = external call before state
  // update in the target, plus a reentrancy-style PoC. This is NOT proof.
  const targetLower = target.toLowerCase();
  const hasCallBeforeUpdate =
    targetLower.includes(".call{value") &&
    targetLower.indexOf(".call{value") < targetLower.lastIndexOf("balances[");
  const pocLooksReentrant =
    poc.toLowerCase().includes("withdraw") && poc.toLowerCase().includes("receive");
  const hasGuard =
    targetLower.includes("nonreentrant") || targetLower.includes("locked");
  let verdict;
  if (hasGuard) verdict = "SIMULATED-NOT_REPRODUCED (demo: target memakai guard)";
  else if (hasCallBeforeUpdate && pocLooksReentrant) verdict = "SIMULATED-REPRODUCED (demo heuristik)";
  else verdict = "SIMULATED-INCONCLUSIVE (demo: pola tidak dikenali)";

  const evidence = {
    tool: "sealed-poc-verifier-frontend-demo",
    version: "0.1.0-local-simulation",
    verdict,
    poc_sha256: await sha256Hex(poc),
    target_sha256: await sha256Hex(target),
    poc_bytes: new TextEncoder().encode(poc).length,
    target_bytes: new TextEncoder().encode(target).length,
    sealed: {
      mode: "local-simulation-only",
      tee: "NOT_REAL_TEE",
      note: "Demo heuristik di browser. Verdict sebenarnya: jalankan src/verifier.py (Foundry).",
    },
  };
  // Show evidence only. Then drop the PoC/target from the textareas.
  out.textContent = JSON.stringify(evidence, null, 2);
  document.getElementById("targetText").value = "";
  document.getElementById("pocText").value = "";
  document.getElementById("targetFile").value = "";
  document.getElementById("pocFile").value = "";
});
