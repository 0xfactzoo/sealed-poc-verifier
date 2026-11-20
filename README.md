# Sealed PoC Verifier

Triase bug bounty privat: researcher kirim PoC exploit, PoC diverifikasi
(reproduksi atau tidak) **tanpa PoC-nya bocor** ke operator / publik
sebelum disclosure.

Company: Factzoo Labs — untuk SuperProtocol Startup Program.
Status: **MVP lokal, 100% gratis, tanpa modal. BELUM jalan di TEE asli,
BELUM ada customer, BELUM deploy, BELUM dipakai program bounty mana pun.**

## Masalah

Saat triase bug bounty hari ini, researcher harus mengirim PoC lengkap
ke program / platform triase. Siapa pun yang memegang PoC itu — operator
platform, reviewer, admin — bisa:

- memakai PoC itu sendiri sebelum researcher dibayar,
- membocorkannya (sengaja / tidak sengaja) sehingga kerentanan jadi
  publik sebelum ada fix,
- menolak laporan dengan alasan "tidak reproduksi" tanpa bukti yang
  bisa diverifikasi researcher.

Akibatnya researcher — terutama researcher independen tanpa nama besar —
dirugikan, dan program kehilangan trust. PoC adalah aset researcher
sampai disclosure disepakati.

## Solusi

PoC dijalankan di dalam lingkungan tersegel (TEE), bukan di mesin
operator. Yang keluar dari lingkungan itu hanya **evidence**:

```json
{
  "verdict": "REPRODUCED",
  "poc_sha256": "449a35…",
  "target_sha256": "0497d7…",
  "forge_exit_code": 0,
  "log_summary": "[PASS] testReentrancyReproduces() ..."
}
```

Tidak ada isi PoC, tidak ada source target, tidak ada detail exploit
di evidence. Researcher bisa membuktikan "PoC saya yang ini, dengan
hash ini, sudah diverifikasi reproduksi pada target dengan hash ini"
tanpa pernah memperlihatkan PoC-nya ke siapa pun.

## Apa yang dilihat operator vs apa yang tidak

| Pihak | Bisa lihat | Tidak bisa lihat |
|---|---|---|
| Operator / Super / GPU host (desain TEE asli) | hash PoC, hash target, verdict, log ringkas | isi PoC, source target, detail exploit |
| Program bounty | verdict + evidence (untuk bayar / tolak) | isi PoC sampai disclosure |
| Researcher | semuanya (PoC miliknya) | — |
| Publik | tidak ada, sampai disclosure | PoC |

**Kejujuran soal MVP ini:** tabel di atas adalah *desain target*.
Di MVP lokal ini, PoC dijalankan di mesin ini, di direktori temp yang
dihapus setelah jalan — operator mesin ini **bisa** melihat PoC selama
proses berjalan. Itu kebalikan dari TEE. MVP ini mensimulasikan
*interface* dan *bentuk evidence*-nya, bukan penyegelan hardware-nya.
Lihat "Rencana integrasi SuperProtocol" di bawah.

## Arsitektur

```
Researcher ── PoC + target ──> [Sealed runner]
                                    ├─ hash PoC + target (sha256)
                                    ├─ salin ke direktori temp terisolasi
                                    ├─ jalankan PoC (Foundry test)
                                    ├─ tentukan verdict dari hasil test
                                    ├─ hapus direktori temp
                                    └─> evidence.json (hash + verdict saja)
Program ── evidence.json ──> bayar / tolak / minta disclosure
```

Semantik verdict — PoC test **harus PASS saat kerentanan reproduksi**:

- `REPRODUCED` — `forge test` exit 0
- `NOT_REPRODUCED` — test jalan, tapi PoC test gagal
- `INCONCLUSIVE` — compile error, timeout, forge tidak ada, atau tidak
  ada hasil test

## Cara jalanin lokal

Syarat: Python 3 (stdlib saja), Foundry (`forge`, sudah ada di
`~/.foundry/bin`). Tanpa network, tanpa wallet, tanpa private key.

```bash
# Sekali saja setelah clone (butuh network untuk download forge-std)
forge install foundry-rs/forge-std

# Kedua contoh sekaligus
bash run-examples.sh

# Satu verifikasi manual
python3 src/verifier.py \
  --poc examples/vulnerable/ReentrancyPoC.t.sol \
  --target examples/vulnerable/VulnerableVault.sol \
  --out evidence.json
echo $?   # 0 = verdict ditentukan, 2 = INCONCLUSIVE
```

### Contoh 1 — rentan → REPRODUCED (terbukti jalan)

- Target: `examples/vulnerable/VulnerableVault.sol` — vault buatan
  sendiri, sengaja rentan reentrancy (`withdraw()` kirim ETH dulu,
  baru nol-kan balance).
- PoC: `examples/vulnerable/ReentrancyPoC.t.sol` — attacker deposit
  1 ether, reenter saat `withdraw()`, kuras 10 ether dana korban.
- Hasil (2026-11-20, `bash run-examples.sh`):
  `verdict: REPRODUCED`, `poc_sha256: 449a3527…`, forge exit 0,
  `[PASS] testReentrancyReproduces()`. Evidence:
  `examples/evidence-vulnerable.json`.

### Contoh 2 — target sudah di-fix → NOT_REPRODUCED (terbukti jalan)

- Target: `examples/fixed/FixedVault.sol` — interface sama, pakai
  checks-effects-interactions + reentrancy guard.
- PoC: sama persis (hash PoC identik: `449a3527…`).
- Hasil: `verdict: NOT_REPRODUCED`, forge exit 1,
  `[FAIL: vault not drained: 10000000000000000000 != 0]`.
  Evidence: `examples/evidence-fixed.json`.

### Frontend demo

```bash
cd frontend && python3 -m http.server 8000
# buka http://127.0.0.1:8000
```

Upload/paste PoC + target → tampil verdict simulasi + hash evidence
saja. PoC **tidak pernah ditampilkan kembali** dan dihapus dari
halaman setelah verifikasi. Verdict frontend hanya heuristik demo;
verdict sebenarnya dari `src/verifier.py` (Foundry).

## Rencana integrasi SuperProtocol asli

Yang MVP ini belum punya, dan baru bisa jalan setelah diterima
program Startup:

1. **PoC jalan di TEE** (Intel TDX / AMD SEV-SNP) lewat Super Swarm:
   image verifier + target di-deploy sebagai workload confidential.
2. **Confidential Router** untuk langkah triase yang butuh LLM
   (mis. klasifikasi severity dari log ringkas — tanpa mengirim PoC
   keluar TEE).
3. **Deployment Evidence + Gatekeeper**: researcher memverifikasi
   attestation endpoint *sebelum* mengirim PoC — bukti bahwa yang
   jalan adalah image verifier yang disetujui, dengan policy
   "tidak ada outbound network".
4. **Marketplace**: program bounty deploy verifier mereka sendiri ke
   confidential space mereka; researcher submit PoC terenkripsi ke
   endpoint itu.

Kredit $5.000 dipakai untuk: GPU-hours confidential (jalankan PoC
Foundry berat), Confidential Router tokens (triase LLM), dan
pengembangan image verifier.

## Struktur repo

```
sealed-poc-verifier/
├── src/verifier.py                  # CLI (Python stdlib, tanpa dependensi)
├── examples/
│   ├── vulnerable/                  # Vault rentan + PoC reentrancy
│   ├── fixed/                       # Vault yang sama, sudah di-fix
│   ├── evidence-vulnerable.json     # evidence contoh 1 (hash saja)
│   └── evidence-fixed.json          # evidence contoh 2 (hash saja)
├── frontend/index.html + app.js     # demo statis, tanpa network
├── lib/forge-std/                   # forge-std (MIT/Apache, untuk test lokal)
├── run-examples.sh                  # jalankan kedua contoh
├── README.md
└── SKILL.md
```

## Batasan & status jujur

- **BELUM jalan di TEE asli.** Semua yang di atas soal TEE adalah
  rencana. Yang jalan hari ini adalah simulasi lokal.
- **BELUM ada customer / program bounty.** Belum dipakai program
  mana pun. Jangan klaim sebaliknya.
- **Hanya PoC Foundry/Solidity** untuk sekarang. PoC web2 / bahasa
  lain belum didukung (runner-nya generik, tapi contohnya hanya
  Foundry).
- **Bukan pengganti audit.** Verdict "reproduksi" ≠ severity, dan
  "tidak reproduksi" bisa berarti PoC salah, bukan target aman.
- **BELUM diaudit.** Kode ini belum audit keamanan formal; jangan
  pakai untuk dana besar atau PoC terhadap program live tanpa
  memahami batasannya.
- **Tanpa modal:** tidak ada deploy on-chain, tidak ada transaksi,
  tidak ada private key, tidak ada layanan berbayar di repo ini.

## Keamanan repo

Tidak ada private key, seed, kredensial, atau PoC exploit nyata
terhadap program live di repo ini. Semua contoh rentan adalah buatan
sendiri dan diberi label jelas. Jangan menambahkan PoC nyata ke repo.
