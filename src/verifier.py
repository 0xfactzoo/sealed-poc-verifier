#!/usr/bin/env python3
"""
Sealed PoC Verifier — local simulation only.

Takes a PoC (a Foundry test file) + a target contract, runs the PoC in a
temporary isolated Foundry project, and emits an evidence JSON that contains
ONLY hashes of the inputs — never the PoC source itself.

Verdict semantics (the PoC test must PASS when the vulnerability reproduces):
  REPRODUCED      forge test exits 0
  NOT_REPRODUCED  forge test ran but the PoC test failed
  INCONCLUSIVE    compile error, timeout, forge missing, or no test result

HONEST LIMITATION: this runs on this machine, in a temp directory.
The operator of this machine CAN see the PoC while it runs.
That is the opposite of a real TEE. The real SuperProtocol design
(TEE Intel TDX / AMD SEV-SNP + Deployment Evidence + Gatekeeper) is
described in README.md — it is NOT what this local simulation does.
This tool simulates the *interface* and the *evidence shape*, not the
hardware sealing.

Usage:
  python3 src/verifier.py --poc examples/vulnerable/ReentrancyPoC.t.sol \
      --target examples/vulnerable/VulnerableVault.sol \
      --out evidence.json
Exit code: 0 when a verdict (REPRODUCED / NOT_REPRODUCED) was determined,
           2 when INCONCLUSIVE.
No network, no deploy, no private key, no wallet. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOL = "sealed-poc-verifier"
VERSION = "0.1.0-local-simulation"

FORGE_STD_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "lib" / "forge-std",
    Path.home() / "workspace" / "agentpay" / "lib" / "forge-std",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_forge() -> str | None:
    forge = shutil.which("forge")
    if forge:
        return forge
    for cand in (Path.home() / ".foundry" / "bin" / "forge",):
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    return None


def find_forge_std() -> Path | None:
    for cand in FORGE_STD_CANDIDATES:
        if (cand / "src" / "Test.sol").is_file():
            return cand
    return None


def summarise_log(text: str, max_chars: int = 4000) -> str:
    """Keep only verdict-relevant lines; never echo source code.

    Forge test output does not contain PoC source, but we still whitelist
    line shapes instead of dumping raw output, so a PoC can never leak
    into the evidence file through a log line.
    """
    keep_prefixes = ("[PASS]", "[FAIL]", "[SKIP]", "Suite result:", "Ran ",
                     "Compiler run", "Error:", "error[", "Failing tests:")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(keep_prefixes) or "testReentrancy" in s or "test" in s.lower() and ("passed" in s or "failed" in s):
            lines.append(s)
    # Always keep the last few lines for context (they are forge summaries).
    tail = [l.strip() for l in text.splitlines() if l.strip()][-6:]
    for line in tail:
        if line not in lines:
            lines.append(line)
    out = "\n".join(lines[-30:])
    return out[:max_chars]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sealed PoC Verifier (local simulation)")
    ap.add_argument("--poc", required=True, help="PoC file (Foundry test, .sol)")
    ap.add_argument("--target", required=True, help="Target contract file (.sol)")
    ap.add_argument("--test-name", default="testReentrancyReproduces",
                    help="PoC test function name (default: testReentrancyReproduces)")
    ap.add_argument("--timeout", type=int, default=120, help="forge timeout in seconds")
    ap.add_argument("--out", default="evidence.json", help="Evidence JSON output path")
    ap.add_argument("--keep-temp", action="store_true", help="Do not delete temp dir (debug only)")
    args = ap.parse_args()

    poc = Path(args.poc)
    target = Path(args.target)
    for p in (poc, target):
        if not p.is_file():
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2

    poc_hash = sha256_file(poc)
    target_hash = sha256_file(target)
    started = time.time()

    evidence = {
        "tool": TOOL,
        "version": VERSION,
        "verdict": "INCONCLUSIVE",
        "poc_sha256": poc_hash,
        "target_sha256": target_hash,
        "poc_filename": poc.name,
        "target_filename": target.name,
        "poc_bytes": poc.stat().st_size,
        "target_bytes": target.stat().st_size,
        "test_name": args.test_name,
        "forge_exit_code": None,
        "log_summary": "",
        "duration_ms": 0,
        # Honest sealing status — local simulation, NOT a real TEE.
        "sealed": {
            "mode": "local-simulation-only",
            "tee": "NOT_REAL_TEE",
            "operator_can_see_poc": True,
            "note": "Local run: the PoC is visible to this machine's operator while it runs. "
                    "In the real SuperProtocol design the PoC runs inside a hardware TEE "
                    "(Intel TDX / AMD SEV-SNP) and the operator sees only hashes + verdict. "
                    "See README.md.",
        },
        # Deliberately absent: poc_source, target_source, poc_content.
        # The evidence file must never contain the PoC.
    }

    forge = find_forge()
    forge_std = find_forge_std()
    if forge is None:
        evidence["log_summary"] = "forge not found (looked in PATH and ~/.foundry/bin)"
        return finish(evidence, args, started)
    if forge_std is None:
        evidence["log_summary"] = "forge-std not found (looked in ./lib/forge-std and ~/workspace/agentpay/lib/forge-std)"
        return finish(evidence, args, started)

    tmp = Path(tempfile.mkdtemp(prefix="sealed-poc-"))
    try:
        (tmp / "src").mkdir()
        (tmp / "test").mkdir()
        shutil.copyfile(target, tmp / "src" / "Vault.sol")
        shutil.copyfile(poc, tmp / "test" / "Poc.t.sol")
        shutil.copytree(forge_std, tmp / "lib" / "forge-std")
        (tmp / "foundry.toml").write_text(
            '[profile.default]\nsrc = "src"\nout = "out"\nlibs = ["lib"]\n',
            encoding="utf-8",
        )
        env = dict(os.environ)
        env["PATH"] = str(Path(forge).parent) + os.pathsep + env.get("PATH", "")
        try:
            proc = subprocess.run(
                [forge, "test", "--match-test", args.test_name],
                cwd=tmp, capture_output=True, text=True,
                timeout=args.timeout, env=env,
            )
            combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            evidence["forge_exit_code"] = proc.returncode
            evidence["log_summary"] = summarise_log(combined)
            if proc.returncode == 0:
                evidence["verdict"] = "REPRODUCED"
            elif "[FAIL]" in combined or "failed" in combined.lower() and "Suite result: ok" not in combined:
                # forge ran the suite and the PoC test failed -> not reproduced.
                # Guard: a compile failure also contains "failed" but no suite result.
                if "Suite result:" in combined or "Ran 1 test suite" in combined:
                    evidence["verdict"] = "NOT_REPRODUCED"
                else:
                    evidence["verdict"] = "INCONCLUSIVE"
            else:
                evidence["verdict"] = "INCONCLUSIVE"
        except subprocess.TimeoutExpired:
            evidence["log_summary"] = f"forge timed out after {args.timeout}s"
            evidence["verdict"] = "INCONCLUSIVE"
    finally:
        if args.keep_temp:
            print(f"temp dir kept: {tmp}", file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    return finish(evidence, args, started)


def finish(evidence: dict, args, started: float) -> int:
    evidence["duration_ms"] = int((time.time() - started) * 1000)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"verdict: {evidence['verdict']}")
    print(f"poc_sha256:    {evidence['poc_sha256']}")
    print(f"target_sha256: {evidence['target_sha256']}")
    print(f"evidence: {out}")
    # Exit 0 when a verdict was determined, 2 when inconclusive.
    return 0 if evidence["verdict"] in ("REPRODUCED", "NOT_REPRODUCED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
