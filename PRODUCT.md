# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: FastAPI (Python) backend + React/Next.js frontend. Greenfield, diputuskan user via PRD. Deploy: self-hosted VM user (2 vCPU / 7.4GB RAM / Ubuntu 24.04).

## Users

Primary: user sendiri (pribadi), pekerja yang butuh tool PDF cepat. Situasi: lagi buru-buru, mau merge/split/compress PDF buat kirim lampiran. Kadang dokumen sensitif (kerjaan teman).

## Product Purpose

Web app self-hosted ala iLovePDF: merge, split, compress, convert PDF. Alasan produk ada: **privasi** — file diproses di server sendiri, bukan server pihak ketiga. File input & hasil dihapus otomatis (TTL 1 jam). Sukses = proses file cepat & akurat, tanpa bocor.

## Positioning

"PDF tools yang nggak nyimpen file lu." Produk ini = hosting sendiri + auto-delete file (1 jam). Posisi yang nggak bisa ditiru tool pihak ketiga: file nggak pernah meninggalkan server milik user.

## Operating Context

- User upload file → proses (PyMuPDF/pikepdf/Ghostscript) → download hasil → file dihapus.
- Batas upload: 50MB/file, 100MB/job (merge).
- Tanpa DB untuk MVP; storage file temp, TTL 1 jam.
- Bilingual UI: Indonesia/English.
- Deploy di VM user (bukan cloud pihak ketiga). HTTPS/SSL wajib di production.

## Capabilities and Constraints

- MVP: merge, split, compress. P1: PDF→JPG, protect/unlock, rotate/hapus halaman. P2: OCR, PDF→Word, API (re-entry).
- Tanpa GPU; 2 vCPU. OCR lambat → ditunda.
- Estimasi ukuran kompres: heuristik, bukan percobaan ganda.
- DPI default 150 untuk convert PDF→gambar.
- File hasil: TTL 1 jam, dihapus permanen. Input juga dihapus setelah proses.

## Brand Commitments

- Nama produk: **evey-converter** (diputuskan user, 2026-10-11).
- Bahasa UI: bilingual ID/EN.
- Domain: belum diputuskan (nanti pas deploy).
- Voice: casual Indonesia (slang ringan, "gua/lu"), tapi UI copy tetap profesional.

## Evidence on Hand

Belum ada aset nyata (belum ada file contoh, testimoni, atau benchmark). PRD di PRD.md adalah satu-satunya sumber. Jangan memalsukan testimoni, pricing, atau klaim deployment.

## Product Principles

1. Privasi = fitur utama; auto-delete adalah janji produk, bukan afterthought.
2. Cepat & akurat > banyak fitur; MVP kecil dulu, naik bertahap.
3. Bilingual ID/EN tanpa copy yang AI-slop.
4. Self-hosted, tanpa ketergantungan cloud pihak ketiga.
5. User pribadi dulu, production belakangan — jangan over-engineer.

## Accessibility & Inclusion

Belum ada kebutuhan khusus yang dikonfirmasi. Tetap ikut WCAG 2.1 AA untuk web.