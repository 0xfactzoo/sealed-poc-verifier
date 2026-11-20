# Sealed PoC Verifier — skill

Triase bug bounty privat: verifikasi PoC tanpa membocorkan isi PoC.
MVP lokal (simulasi) — BUKAN TEE asli. Lihat README.md untuk batasannya.

## Untuk researcher

1. Tulis PoC sebagai Foundry test yang **PASS saat kerentanan reproduksi**.
   Nama fungsi test default: `testReentrancyReproduces` (bisa diubah
   dengan `--test-name`).
2. Jalankan verifier terhadap target:
   ```bash
   python3 src/verifier.py --poc <poc.t.sol> --target <Target.sol> --out evidence.json
   ```
3. Kirim **hanya `evidence.json`** ke program (berisi hash + verdict,
   tanpa isi PoC). Simpan PoC-nya sampai disclosure disepakati.
4. Verdict: `REPRODUCED` / `NOT_REPRODUCED` / `INCONCLUSIVE`.
   Exit code 0 = verdict ditentukan, 2 = inconclusive.

## Untuk program bounty / triager

1. Minta `evidence.json` dulu, bukan PoC lengkap.
2. Cocokkan `target_sha256` dengan hash target yang sedang ditriase,
   dan `poc_sha256` dengan PoC yang nanti didisclose.
3. `REPRODUCED` → lanjut ke penilaian severity / pembayaran.
   `NOT_REPRODUCED` → tolak dengan evidence sebagai bukti.
   `INCONCLUSIVE` → minta PoC diperbaiki atau jalankan ulang, jangan
   putuskan berdasarkan ini.
4. Jangan minta PoC lengkap sebelum ada kesepakatan disclosure.

## Aturan

- Jangan masukkan PoC nyata terhadap program live ke repo ini.
- Jangan klaim verdict lokal ini sebagai bukti TEE — ini simulasi.
- Evidence tidak boleh berisi isi PoC; kalau ada, itu bug — laporkan.
