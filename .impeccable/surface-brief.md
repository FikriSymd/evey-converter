# Surface Brief — evey-converter

## Direction contract (code-led)

THESIS: PDF tool yang dibaca sebagai papan kerja dokumen — shell ink-on-paper yang tenang dan padat (header rail, job rail kiri, work area tengah, footer privacy). Menolak default kategori: hero centered + gradient + rounded card + emoji icon.

OWN-WORLD: Palet ink-on-paper — near-black ink `#16181d`, bone paper `#f4f1ea`, satu vermilion `#e2543c` (aksi primer + privacy), satu bottle-green `#2e6b4f` (sukses). Type: grotesk kerja (IBM Plex Sans) + mono companion (IBM Plex Mono) untuk nama file/ukuran/status. Density: 13-14px body, 11-12px mono label, grid 4px. Setiap border/divider/key line = 1 device pixel (hairline ruling).

STORY: Visitor yang buru-buru buka situs, langsung ngerti ini tool PDF yang privat: drop file, pilih tool, proses, download. Nggak ada marketing noise. Garis privacy di footer bilang file dihapus 1 jam.

FIRST VIEWPORT: Header rail (nama + nav: tools/about/lang toggle, no gradient). Kiri: job rail daftar tools (merge/split/compress/convert) sebagai keyed list, tool aktif di-mark. Tengah: drop zone bone-paper besar, dashed 1px border, placeholder mono; tombol primary vermilion kotak (no pill); di bawahnya job board: kartu job yang flip state plate (Uploaded → Processing → Done) dengan step 90ms dua-frame. Footer: hairline rule + privacy line vermilion.

FORM: depot work-board / instrument panel. Signature move: split-flap state plates pada job cards (state flip dengan 90ms two-frame step, hinged top edge, no easing curve). Satu-satunya elemen non-standar; kontrol lain standar web.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Scope

- First surface: halaman utama (home) evey-converter — drop zone + job board + privacy footer.
- Mode: operate (tool kerja, bukan landing page marketing).
- Bahasa: bilingual ID/EN (toggle).
- Build: code-led, static HTML/CSS/JS dulu (prototype visual), backend FastAPI menyusul.

## Constraints

- Bilingual ID/EN tanpa AI-slop copy.
- Nama produk: evey-converter.
- Privasi = fitur utama; auto-delete 1 jam di footer.
- Target: simple tapi keren; bukan template AI.
- Batas upload 50MB/file, 100MB/job (PRD).