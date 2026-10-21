# PRD: Tools PDF Pribadi ([NAMA PRODUK])

Status: draft v1. Tanggal: 2026-10-11
Pemilik: user (pribadi), berpotensi production di kemudian hari.
Nama produk: **evey-converter** (diputuskan user, 2026-10-11). Bahasa UI: **bilingual ID/EN**. TTL file hasil: **1 jam, dihapus permanen**.

## 1. Overview

**Problem Statement**
User rutin butuh merge, compress, dan convert PDF untuk kerjaan pribadi dan pekerjaan atas nama teman/bisnis. Sekarang dia upload dokumen ke layanan pihak ketiga (iLovePDF dkk), artinya file sensitif (kontrak, laporan, data bisnis teman) mampir ke server orang lain. Ada batas ukuran file, kadang gagal proses, dan tidak ada jaminan file dihapus.

**Proposed Solution**
Web app yang di-host sendiri di VM user. Fitur inti: merge, split, compress, convert PDF ke gambar. File diproses di server sendiri, lalu dihapus otomatis. Privasi adalah alasan produk ini ada, bukan fitur pelengkap.

**Success Metrics**

| Slot | Metric | Baseline | Target |
|---|---|---|---|
| Adoption | Persentase kebutuhan PDF mingguan yang dikerjakan di tool sendiri | 0% (semua via pihak ketiga) | ≥80% dalam 30 hari |
| Outcome | Job selesai tanpa error | Kadang gagal di pihak ketiga (limit ukuran) | ≥95% job sukses |
| Cost | Biaya tambahan hosting | 0 (VM sudah jalan) | Tetap 0 |
| Guardrail | File input terhapus permanen dari server | Tidak ada jaminan di pihak ketiga | ≤1 jam setelah job selesai, tidak pernah tersisa di disk |

Catatan: karena ini produk pribadi, tidak ada metric bisnis. Metric di-review manual tiap minggu oleh user.

## 2. Context & Background

**Why Now**
Infra sudah ada: VM 2 vCPU/7.4GB RAM yang jalan 24/7, biaya tambahan hosting = 0. Kebutuhan PDF rutin, dan sebagian dokumen sifatnya sensitif. Momen ini tepat karena tinggal bangun aplikasinya, tidak perlu siapkan infrastruktur baru.

**Strategic Alignment**
Tidak ada alignment perusahaan. Ini tool pribadi yang suatu saat bisa dipromosikan ke teman/bisnis user. Desain harus sudah siap untuk itu: nama produk yang bisa dipakai publik, copy yang tidak memalukan kalau dilihat orang lain.

**User Research Summary**
Tidak ada riset formal. Observasi: user pernah kerjaan atas nama teman yang datanya menyusul, artinya alur kerja harus jalan dengan placeholder dan tidak nunggu data lengkap. Kebiasaan ini dipakai juga di produk: alur harus langsung bisa dipakai tanpa setup.

## 3. User Stories & Use Cases

**US1: Merge PDF**
As user, I want to gabung beberapa PDF jadi satu file, so that saya tidak perlu upload ke layanan pihak ketiga.
Acceptance Criteria:
- Bisa pilih 2+ file PDF sekaligus (drag & drop atau file picker)
- Urutan file bisa diatur ulang sebelum proses
- Hasil unduh sebagai satu PDF
- File input dihapus setelah job selesai

**US2: Split PDF**
As user, I want to pisah halaman tertentu dari PDF, so that saya bisa kirim sebagian dokumen saja.
Acceptance Criteria:
- Bisa pilih rentang halaman (misal 1-3, 5)
- Bisa ekstrak tiap halaman jadi file terpisah
- Hasil unduh sebagai zip (kalau banyak file) atau PDF tunggal

**US3: Compress PDF**
As user, I want to kecilkan ukuran PDF, so that lampiran email tidak ditolak karena batas ukuran.
Acceptance Criteria:
- Ada 3 level kompresi (kecil, sedang, tinggi) dengan estimasi hasil sebelum proses
- Ukuran hasil lebih kecil dari input (kalau tidak, kasih tahu dan tetap kasih hasil asli)
- Kualitas teks tetap terbaca

**US4: Convert PDF ke Gambar**
As user, I want to ubah PDF jadi JPG/PNG, so that saya bisa kirim preview atau pakai di dokumen lain.
Acceptance Criteria:
- Pilih format JPG atau PNG
- Bisa pilih halaman tertentu atau semua
- Hasil unduh sebagai zip

**US5: Protect / Unlock PDF (P1)**
As user, I want to kasih password ke PDF atau buka password PDF sendiri, so that file yang dikirim aman.
Acceptance Criteria:
- Protect: set password, hasil unduh butuh password saat dibuka
- Unlock: input PDF ber-password, proses berhasil kalau password benar

**US6: Rotate / Hapus Halaman (P1)**
As user, I want to putar atau buang halaman tertentu, so that hasil scan yang miring bisa dibereskan.
Acceptance Criteria:
- Preview thumbnail tiap halaman
- Rotate 90/180/270 per halaman
- Halaman yang ditandai hapus tidak ikut di hasil

## 4. Requirements

### Functional Requirements

**P0 (MVP, harus ada di rilis pertama)**
- Upload: drag & drop + file picker, multi-file, batas 50MB per file
- Merge (US1)
- Split (US2)
- Compress (US3)
- Download hasil
- Auto-delete file input + hasil setelah job selesai
- Tiga state wajib di semua layar: empty, loading, error (R-27)
- Responsive mobile

**P1 (rilis kedua)**
- Convert PDF ke JPG/PNG (US4)
- Protect / Unlock (US5)
- Rotate / hapus halaman (US6)
- Thumbnail preview halaman
- Progress bar upload + proses

**P2 (masa depan, perlu re-entry)**
- OCR (butuh hardware lebih besar, tanpa GPU lambat)
- PDF → Word/Excel (butuh riset lisensi; iLovePDF pakai teknologi berlisensi untuk ini)
- API publik
- Multi-user / akun

### Non-Functional Requirements

- **Performance**: upload ≤50MB/file; job ≤50MB selesai ≤60 detik di hardware 2 vCPU (p95). Kalau lebih lama, tampilkan progress dan pesan antrian.
- **Security**: HTTPS wajib; job ID random (tidak bisa ditebak); tidak ada penyimpanan permanen; rate limit upload; file tidak pernah diserve ke user lain.
- **Privacy**: tanpa database user, tanpa tracking pihak ketiga, tanpa cookie iklan.
- **Accessibility**: WCAG AA (kontras 4.5:1 normal, 3:1 besar), keyboard navigable, focus visible (R-25, R-32).
- **Mobile**: layout reflow, tap target ≥44px, tidak ada horizontal overflow (R-03).
- **Reliability**: error state menyebutkan penyebab dan langkah berikutnya (R-27).

## 5. Design & UX

**Alur utama**: pilih tool → drop file → atur opsi → proses → download. Satu layar per tool (referensi flow iLovePDF) supaya fokus dan tidak bingung.

**Direction (sementara, akan disempurnakan saat fase UI)**
- Utility tool yang kalem: fokus ke fungsi, bukan hiasan
- Copy bahasa Indonesia, langsung ke poin
- Nama produk placeholder: [NAMA PRODUK], logo pakai teks, tidak dibuatkan asumsi (R-23)
- Tanpa statistik palsu, tanpa testimoni (R-17, R-18)

**Edge cases yang wajib ditangani**
- File corrupt → pesan jelas, file ditandai gagal
- File > 50MB → tolak di frontend dengan pesan
- Koneksi putus saat upload → state error + retry
- Compress tidak menghasilkan file lebih kecil → kasih tahu, tawarkan hasil asli
- Password salah saat unlock → pesan spesifik
- Job gagal di tengah → file input tetap dihapus, user bisa upload ulang

**States**
- Empty: dropzone dengan instruksi
- Loading: progress dengan teks (bukan spinner telanjang)
- Error: penyebab + langkah berikutnya
- Success: tombol download jelas

## 6. Technical Considerations

**Stack yang direkomendasikan**
- Backend: Python + FastAPI. Alasan: ekosistem PDF paling matang (PyMuPDF untuk baca/render, pikepdf untuk encrypt/split, Ghostscript untuk kompres).
- Frontend: React (Next.js) atau HTML+JS statis yang diserve backend. Keputusan final di fase implementasi; syaratnya harus tetap simple dan cepat.
- Storage: folder temp + cleanup otomatis. Tidak perlu database untuk MVP.
- Deploy: VM user, systemd + reverse proxy (Caddy/Nginx) + HTTPS Let's Encrypt.

**Risiko dan mitigasi**
- RAM 7.4GB tidak cukup kalau banyak job parallel → batasi 1-2 job parallel, queue sederhana
- File 50MB bisa makan memory saat proses → proses streaming, bukan load semua ke RAM
- OCR butuh hardware → masuk P2, tidak di MVP
- PDF → Word butuh teknologi berlisensi → masuk P2, tidak dijanjikan

**Dependensi**
- Ghostscript (system package) untuk kompres
- Python libs: fastapi, pymupdf, pikepdf
- Frontend build tooling

## 7. Implementation Plan

**Phase 1 (MVP)**: merge, split, compress + upload/download + auto-delete + 3 states + responsive mobile.
Alasan cut: tiga fitur ini paling sering dipakai, dan tidak butuh OCR atau teknologi berlisensi. Ini juga yang paling sering dipakai user untuk kerjaan teman.

**Phase 2**: PDF → JPG/PNG, protect/unlock, rotate/hapus halaman, thumbnail, progress bar.

**Phase 3 (re-entry, butuh keputusan ulang)**: batch processing, API publik, OCR, PDF → Word/Excel, multi-user.

## 8. Open Questions

**Keputusan yang sudah diselesaikan saat builder check (call pemilik PRD):**
- Estimasi ukuran kompres pakai heuristik berdasarkan level kompresi, bukan percobaan kompres ganda (beban CPU 2 vCPU terlalu besar untuk percobaan sungguhan per request).
- Batas upload: 50MB per file DAN 100MB total per job (disk temp aman di 7.4GB).
- Convert PDF ke gambar (P1): DPI default 150, user bisa pilih 72/150/300.
- Fitur unggulan di landing: merge (paling sering dipakai, jadi titik masuk utama).

**Pertanyaan yang masih butuh jawaban user:**

| # | Pertanyaan | Owner | Deadline | Cost kalau tidak dijawab |
|---|---|---|---|---|
| 1 | Nama produk apa? | user | sebelum fase UI | UI pakai placeholder [NAMA PRODUK] |
| 2 | Domain pakai apa? | user | sebelum deploy | deploy pakai IP + cert sementara |
| 3 | Bahasa UI: Indonesia saja atau bilingual? | user | sebelum fase UI | default: Indonesia saja |
| 4 | TTL file hasil: hapus 1 jam setelah job selesai (paling privat), atau disimpan sampai berhasil diunduh (lebih ramah, kurang privat)? | user | sebelum deploy | default: 1 jam + notifikasi jelas |

## 9. Appendix

**Referensi**
- iLovePDF (ilovepdf.com): referensi flow UX (satu tool satu layar)
- Sejda (sejda.com): referensi self-hosted/open-source PDF tools

**Kompetitor yang dipakai user saat ini**: iLovePDF, kemungkinan Smallpdf.