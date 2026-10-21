/* ============================================================
   evey-converter - app.js
   Prototype logic: tool catalog (data-driven), bilingual ID/EN,
   drop zone, job list, split-flap state machine, fake pipeline.
   Backend FastAPI will replace the fake processing later.
   Catalog = tools that can actually run (PyMuPDF / pikepdf /
   Ghostscript / LibreOffice / Tesseract).
   ============================================================ */

(() => {
  "use strict";

  const MAX_FILE_MB = 50;
  const MAX_JOB_MB = 100;

  /* ---------- Accepted file kinds ---------- */
  const ACCEPT = {
    pdf:   { attr: "application/pdf,.pdf", test: (f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name), kind: "pdf" },
    docx:  { attr: ".docx", test: (f) => /\.docx$/i.test(f.name), kind: "docx" },
    xlsx:  { attr: ".xlsx", test: (f) => /\.xlsx$/i.test(f.name), kind: "xlsx" },
    pptx:  { attr: ".pptx", test: (f) => /\.pptx$/i.test(f.name), kind: "pptx" },
    image: { attr: "image/*", test: (f) => /^image\//.test(f.type), kind: "image" },
    html:  { attr: ".html,.htm", test: (f) => /\.html?$/i.test(f.name), kind: "html" },
  };

  /* ---------- Tool catalog (only tools that actually run) ---------- */
  const TOOLS = [
    // ORGANIZE
    { id: "merge",        group: "organize", accept: "pdf",   multiple: true },
    { id: "split",        group: "organize", accept: "pdf",   multiple: false, opts: [
        { type: "choice", key: "mode", values: ["pages", "range"], def: "range" },
        { type: "text",   key: "range", def: "1-3", dependsOn: { key: "mode", value: "range" } },
    ]},
    { id: "organize",     group: "organize", accept: "pdf",   multiple: false, opts: [
        { type: "text", key: "order", def: "3,1,2" },
    ]},
    { id: "rotate",       group: "organize", accept: "pdf",   multiple: false, opts: [
        { type: "choice", key: "angle", values: ["90", "180", "270"], def: "90" },
        { type: "choice", key: "scope", values: ["all", "range"], def: "all" },
        { type: "text",   key: "range", def: "1-3", dependsOn: { key: "scope", value: "range" } },
    ]},
    { id: "remove_pages", group: "organize", accept: "pdf",   multiple: false, opts: [
        { type: "text", key: "range", def: "2,4-5" },
    ]},
    { id: "extract_pages",group: "organize", accept: "pdf",   multiple: false, opts: [
        { type: "text", key: "range", def: "1-3" },
    ]},

    // OPTIMIZE
    { id: "compress",     group: "optimize", accept: "pdf",   multiple: true, opts: [
        { type: "choice", key: "level", values: ["low", "rec", "strong"], def: "rec" },
    ]},
    { id: "repair",       group: "optimize", accept: "pdf",   multiple: true },
    { id: "pdfa",         group: "optimize", accept: "pdf",   multiple: true },

    // CONVERT
    { id: "pdf_word",     group: "convert",  accept: "pdf",   multiple: true },
    { id: "pdf_excel",    group: "convert",  accept: "pdf",   multiple: true },
    { id: "pdf_ppt",      group: "convert",  accept: "pdf",   multiple: true },
    { id: "word_pdf",     group: "convert",  accept: "docx",  multiple: true },
    { id: "excel_pdf",    group: "convert",  accept: "xlsx",  multiple: true },
    { id: "ppt_pdf",      group: "convert",  accept: "pptx",  multiple: true },
    { id: "pdf_jpg",      group: "convert",  accept: "pdf",   multiple: true, opts: [
        { type: "choice", key: "imgfmt", values: ["jpg", "png"], def: "jpg" },
        { type: "choice", key: "dpi", values: ["96", "150", "300"], def: "150" },
    ]},
    { id: "jpg_pdf",      group: "convert",  accept: "image", multiple: true },
    { id: "html_pdf",     group: "convert",  accept: "html",  multiple: false },
    { id: "ocr",          group: "convert",  accept: "pdf",   multiple: true, opts: [
        { type: "choice", key: "lang", values: ["ind", "eng", "ind+eng"], def: "ind" },
    ]},

    // SECURITY
    { id: "protect",      group: "security", accept: "pdf",   multiple: true, opts: [
        { type: "text", key: "password", inputType: "password" },
    ]},
    { id: "unlock",       group: "security", accept: "pdf",   multiple: true, opts: [
        { type: "text", key: "password", inputType: "password" },
    ]},
    { id: "watermark",    group: "security", accept: "pdf",   multiple: true, opts: [
        { type: "text",   key: "text", def: "" },
        { type: "choice", key: "pos", values: ["diagonal", "center"], def: "diagonal" },
        { type: "choice", key: "opacity", values: ["20", "40", "60"], def: "40" },
    ]},
  ];

  const GROUPS = ["organize", "optimize", "convert", "security"];
  const TOOL_BY_ID = Object.fromEntries(TOOLS.map((t) => [t.id, t]));

  /* ---------- i18n ---------- */
  const I18N = {
    id: {
      nav_tools: "Tools", nav_privacy: "Privasi", nav_about: "Tentang",
      rail_tools: "TOOLS", rail_status: "STATUS", rail_idle: "idle",
      group_organize: "ATUR", group_optimize: "OPTIMALKAN", group_convert: "KONVERSI", group_security: "KEAMANAN",
      drop_or: "atau", drop_browse: "pilih file", drop_limit: "maks 50MB per file",
      board_jobs: "PEKERJAAN", board_clear: "Bersihkan",
      state_uploaded: "UPLOADED", state_processing: "PROCESSING", state_done: "DONE", state_error: "ERROR",
      process_btn: "Proses", process_hint: "File dihapus otomatis setelah diproses.",
      privacy_text: "File lu diproses di server sendiri dan dihapus otomatis 1 jam setelah diproses. Nggak ada yang nyimpen.",
      about_title: "Kenapa evey-converter?",
      about_body: "Tool PDF online biasanya nyimpen file lu di server mereka. evey-converter jalan di server milik lu sendiri: file nggak pernah keluar dari kendali lu, dan dihapus permanen setelah 1 jam.",
      about_ver: "VERSI",
      footer_copy: "evey-converter", footer_privacy: "file dihapus 1 jam setelah diproses",
      lang_title: "Switch to English",
      // tool names
      tool_merge: "Gabung PDF", tool_split: "Pisah PDF", tool_organize: "Urutkan halaman",
      tool_rotate: "Putar halaman", tool_remove_pages: "Hapus halaman", tool_extract_pages: "Ekstrak halaman",
      tool_compress: "Kompres PDF", tool_repair: "Perbaiki PDF", tool_pdfa: "PDF ke PDF/A",
      tool_pdf_word: "PDF ke Word", tool_pdf_excel: "PDF ke Excel", tool_pdf_ppt: "PDF ke PowerPoint",
      tool_word_pdf: "Word ke PDF", tool_excel_pdf: "Excel ke PDF", tool_ppt_pdf: "PowerPoint ke PDF",
      tool_pdf_jpg: "PDF ke gambar", tool_jpg_pdf: "Gambar ke PDF", tool_html_pdf: "Web ke PDF",
      tool_ocr: "OCR PDF",
      tool_protect: "Kunci PDF", tool_unlock: "Buka kunci PDF", tool_watermark: "Watermark",
      // titles + subs
      title_merge: "Gabung file PDF", sub_merge: "Drop beberapa PDF, urutkan, lalu gabung jadi satu file.",
      title_split: "Pisah file PDF", sub_split: "Pecah satu PDF jadi beberapa file, per halaman atau per rentang.",
      title_organize: "Urutkan halaman", sub_organize: "Susun ulang urutan halaman dengan menulis urutan barunya.",
      title_rotate: "Putar halaman", sub_rotate: "Putar semua halaman atau rentang tertentu sebesar 90, 180, atau 270 derajat.",
      title_remove_pages: "Hapus halaman", sub_remove_pages: "Buang halaman tertentu dari PDF dan sisakan yang lain.",
      title_extract_pages: "Ekstrak halaman", sub_extract_pages: "Ambil halaman tertentu jadi PDF baru.",
      title_compress: "Kompres file PDF", sub_compress: "Kecilkan ukuran PDF tanpa ngubah isi. Estimasi hasil muncul setelah pilih file.",
      title_repair: "Perbaiki PDF", sub_repair: "Coba pulihkan PDF yang rusak atau nggak bisa dibuka.",
      title_pdfa: "PDF ke PDF/A", sub_pdfa: "Ubah PDF jadi PDF/A buat arsip jangka panjang.",
      title_pdf_word: "PDF ke Word", sub_pdf_word: "Ubah PDF jadi dokumen Word (.docx) yang bisa diedit.",
      title_pdf_excel: "PDF ke Excel", sub_pdf_excel: "Tarik tabel dari PDF jadi spreadsheet Excel (.xlsx).",
      title_pdf_ppt: "PDF ke PowerPoint", sub_pdf_ppt: "Ubah PDF jadi presentasi PowerPoint (.pptx).",
      title_word_pdf: "Word ke PDF", sub_word_pdf: "Ubah dokumen Word jadi PDF yang rapi.",
      title_excel_pdf: "Excel ke PDF", sub_excel_pdf: "Ubah spreadsheet Excel jadi PDF.",
      title_ppt_pdf: "PowerPoint ke PDF", sub_ppt_pdf: "Ubah presentasi PowerPoint jadi PDF.",
      title_pdf_jpg: "PDF ke gambar", sub_pdf_jpg: "Ubah halaman PDF jadi JPG atau PNG.",
      title_jpg_pdf: "Gambar ke PDF", sub_jpg_pdf: "Gabung beberapa gambar jadi satu PDF.",
      title_html_pdf: "Web ke PDF", sub_html_pdf: "Ubah file HTML jadi PDF.",
      title_ocr: "OCR PDF", sub_ocr: "Bikin PDF hasil scan bisa dicari dan dikopi teksnya.",
      title_protect: "Kunci PDF", sub_protect: "Kasih password biar PDF cuma bisa dibuka yang tahu sandinya.",
      title_unlock: "Buka kunci PDF", sub_unlock: "Hapus password dari PDF yang lu punya sendiri.",
      title_watermark: "Watermark", sub_watermark: "Cap teks watermark ke tiap halaman PDF.",
      // drop labels by kind
      drop_pdf: "Drop PDF di sini", drop_docx: "Drop dokumen Word di sini", drop_xlsx: "Drop file Excel di sini",
      drop_pptx: "Drop file PowerPoint di sini", drop_image: "Drop gambar di sini", drop_html: "Drop file HTML di sini",
      // option labels
      opt_mode: "MODE", optval_mode_pages: "Setiap halaman", optval_mode_range: "Rentang halaman",
      opt_range: "RENTANG HALAMAN", ph_range: "contoh: 1-3, 5",
      opt_order: "URUTAN HALAMAN", ph_order: "contoh: 3,1,2",
      opt_angle: "SUDUT", optval_angle_90: "90°", optval_angle_180: "180°", optval_angle_270: "270°",
      opt_scope: "TERAPKAN KE", optval_scope_all: "Semua halaman", optval_scope_range: "Rentang",
      opt_level: "TINGKAT KOMPRESI", optval_level_low: "Ringan", optval_level_rec: "Disarankan", optval_level_strong: "Kuat",
      opt_imgfmt: "FORMAT GAMBAR", optval_imgfmt_jpg: "JPG", optval_imgfmt_png: "PNG",
      opt_dpi: "RESOLUSI", optval_dpi_96: "96 DPI (kecil)", optval_dpi_150: "150 DPI (sedang)", optval_dpi_300: "300 DPI (tajam)",
      opt_lang: "BAHASA DOKUMEN", optval_lang_ind: "Indonesia", optval_lang_eng: "Inggris", optval_lang_indeng: "Indonesia + Inggris",
      opt_password: "PASSWORD", ph_password: "Masukkan password",
      opt_text: "TEKS WATERMARK", ph_text: "contoh: RAHASIA",
      opt_pos: "POSISI", optval_pos_diagonal: "Diagonal", optval_pos_center: "Tengah",
      opt_opacity: "KEPEKATAN", optval_opacity_20: "20%", optval_opacity_40: "40%", optval_opacity_60: "60%",
      // toasts
      toast_added: (n) => `${n} file ditambahkan.`,
      toast_single: "Tool ini cuma buat 1 file. File sebelumnya diganti.",
      toast_too_large: (name) => `${name} kegedean (maks 50MB).`,
      toast_wrong_type: (kind) => `Tipe file nggak cocok. Tool ini butuh ${kind}.`,
      toast_job_over: "Total file melebihi 100MB. Hapus beberapa dulu.",
      toast_no_files: "Belum ada file. Drop atau pilih file dulu.",
      toast_removed: "File dihapus dari antrean.",
      toast_cleared: "Antrean dibersihkan.",
      toast_processing: "Lagi diproses...",
      toast_done: "Selesai. File hasil dihapus otomatis 1 jam lagi.",
      toast_error: "Proses gagal. Coba lagi.",
      toast_timeout: "Proses kelamaan. Coba file yang lebih kecil.",
      job_download: "Unduh hasil",
      rail_toggle: "Pilih tool",
      stage_prep: "Menyiapkan",
      stage_scan: "Memindai isi",
      stage_ocr: "Membaca teks",
      stage_optimize: "Mengoptimalkan",
      stage_finalize: "Menyelesaikan",
      stage_working: "Memproses",
    },
    en: {
      nav_tools: "Tools", nav_privacy: "Privacy", nav_about: "About",
      rail_tools: "TOOLS", rail_status: "STATUS", rail_idle: "idle",
      group_organize: "ORGANIZE", group_optimize: "OPTIMIZE", group_convert: "CONVERT", group_security: "SECURITY",
      drop_or: "or", drop_browse: "browse files", drop_limit: "max 50MB per file",
      board_jobs: "JOBS", board_clear: "Clear",
      state_uploaded: "UPLOADED", state_processing: "PROCESSING", state_done: "DONE", state_error: "ERROR",
      process_btn: "Process", process_hint: "Files are deleted automatically after processing.",
      privacy_text: "Your files are processed on your own server and deleted automatically 1 hour after processing. Nothing is stored.",
      about_title: "Why evey-converter?",
      about_body: "Online PDF tools usually store your files on their servers. evey-converter runs on your own server: files never leave your control, and they are permanently deleted after 1 hour.",
      about_ver: "VERSION",
      footer_copy: "evey-converter", footer_privacy: "files are deleted 1 hour after processing",
      lang_title: "Ganti ke Bahasa Indonesia",
      tool_merge: "Merge PDF", tool_split: "Split PDF", tool_organize: "Organize pages",
      tool_rotate: "Rotate pages", tool_remove_pages: "Remove pages", tool_extract_pages: "Extract pages",
      tool_compress: "Compress PDF", tool_repair: "Repair PDF", tool_pdfa: "PDF to PDF/A",
      tool_pdf_word: "PDF to Word", tool_pdf_excel: "PDF to Excel", tool_pdf_ppt: "PDF to PowerPoint",
      tool_word_pdf: "Word to PDF", tool_excel_pdf: "Excel to PDF", tool_ppt_pdf: "PowerPoint to PDF",
      tool_pdf_jpg: "PDF to image", tool_jpg_pdf: "Image to PDF", tool_html_pdf: "Web to PDF",
      tool_ocr: "OCR PDF",
      tool_protect: "Protect PDF", tool_unlock: "Unlock PDF", tool_watermark: "Watermark",
      title_merge: "Merge PDF files", sub_merge: "Drop several PDFs, reorder them, and merge into one file.",
      title_split: "Split PDF file", sub_split: "Break one PDF into several files, per page or by page range.",
      title_organize: "Organize pages", sub_organize: "Rearrange page order by typing the new order.",
      title_rotate: "Rotate pages", sub_rotate: "Rotate all pages or a range by 90, 180, or 270 degrees.",
      title_remove_pages: "Remove pages", sub_remove_pages: "Drop specific pages from a PDF and keep the rest.",
      title_extract_pages: "Extract pages", sub_extract_pages: "Pull specific pages out into a new PDF.",
      title_compress: "Compress PDF file", sub_compress: "Shrink a PDF without changing the content. Estimated size appears after you pick a file.",
      title_repair: "Repair PDF", sub_repair: "Try to recover a broken PDF that won't open.",
      title_pdfa: "PDF to PDF/A", sub_pdfa: "Convert a PDF to PDF/A for long-term archiving.",
      title_pdf_word: "PDF to Word", sub_pdf_word: "Turn a PDF into an editable Word document (.docx).",
      title_pdf_excel: "PDF to Excel", sub_pdf_excel: "Pull tables out of a PDF into an Excel spreadsheet (.xlsx).",
      title_pdf_ppt: "PDF to PowerPoint", sub_pdf_ppt: "Turn a PDF into a PowerPoint presentation (.pptx).",
      title_word_pdf: "Word to PDF", sub_word_pdf: "Turn a Word document into a clean PDF.",
      title_excel_pdf: "Excel to PDF", sub_excel_pdf: "Turn an Excel spreadsheet into a PDF.",
      title_ppt_pdf: "PowerPoint to PDF", sub_ppt_pdf: "Turn a PowerPoint presentation into a PDF.",
      title_pdf_jpg: "PDF to image", sub_pdf_jpg: "Turn PDF pages into JPG or PNG.",
      title_jpg_pdf: "Image to PDF", sub_jpg_pdf: "Merge several images into one PDF.",
      title_html_pdf: "Web to PDF", sub_html_pdf: "Turn an HTML file into a PDF.",
      title_ocr: "OCR PDF", sub_ocr: "Make a scanned PDF searchable and copyable.",
      title_protect: "Protect PDF", sub_protect: "Add a password so only people who know it can open the PDF.",
      title_unlock: "Unlock PDF", sub_unlock: "Remove the password from a PDF you own.",
      title_watermark: "Watermark", sub_watermark: "Stamp a text watermark onto every PDF page.",
      drop_pdf: "Drop PDF here", drop_docx: "Drop a Word document here", drop_xlsx: "Drop an Excel file here",
      drop_pptx: "Drop a PowerPoint file here", drop_image: "Drop images here", drop_html: "Drop an HTML file here",
      opt_mode: "MODE", optval_mode_pages: "Every page", optval_mode_range: "Page range",
      opt_range: "PAGE RANGE", ph_range: "e.g. 1-3, 5",
      opt_order: "PAGE ORDER", ph_order: "e.g. 3,1,2",
      opt_angle: "ANGLE", optval_angle_90: "90°", optval_angle_180: "180°", optval_angle_270: "270°",
      opt_scope: "APPLY TO", optval_scope_all: "All pages", optval_scope_range: "Range",
      opt_level: "COMPRESSION LEVEL", optval_level_low: "Low", optval_level_rec: "Recommended", optval_level_strong: "Strong",
      opt_imgfmt: "IMAGE FORMAT", optval_imgfmt_jpg: "JPG", optval_imgfmt_png: "PNG",
      opt_dpi: "RESOLUTION", optval_dpi_96: "96 DPI (small)", optval_dpi_150: "150 DPI (medium)", optval_dpi_300: "300 DPI (sharp)",
      opt_lang: "DOCUMENT LANGUAGE", optval_lang_ind: "Indonesian", optval_lang_eng: "English", optval_lang_indeng: "Indonesian + English",
      opt_password: "PASSWORD", ph_password: "Enter password",
      opt_text: "WATERMARK TEXT", ph_text: "e.g. CONFIDENTIAL",
      opt_pos: "POSITION", optval_pos_diagonal: "Diagonal", optval_pos_center: "Center",
      opt_opacity: "OPACITY", optval_opacity_20: "20%", optval_opacity_40: "40%", optval_opacity_60: "60%",
      toast_added: (n) => `${n} file(s) added.`,
      toast_single: "This tool takes one file. The previous file was replaced.",
      toast_too_large: (name) => `${name} is too large (max 50MB).`,
      toast_wrong_type: (kind) => `Wrong file type. This tool needs ${kind}.`,
      toast_job_over: "Total files exceed 100MB. Remove some first.",
      toast_no_files: "No files yet. Drop or pick a file first.",
      toast_removed: "File removed from queue.",
      toast_cleared: "Queue cleared.",
      toast_processing: "Processing...",
      toast_done: "Done. Result files are deleted automatically in 1 hour.",
      toast_error: "Processing failed. Try again.",
      toast_timeout: "Processing took too long. Try a smaller file.",
      job_download: "Download result",
      rail_toggle: "Choose a tool",
      stage_prep: "Preparing",
      stage_scan: "Scanning contents",
      stage_ocr: "Reading text",
      stage_optimize: "Optimizing",
      stage_finalize: "Finishing",
      stage_working: "Working",
    },
  };

  /* ---------- State ---------- */
  const state = {
    lang: "id",
    tool: "merge",
    files: [],
    processing: false,
    opts: {},
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const els = {
    dropZone: $("[data-drop-zone]"),
    fileInput: $("[data-file-input]"),
    browseBtn: $("[data-browse]"),
    toolGroups: $("[data-tool-groups]"),
    toolOpts: $("[data-tool-opts]"),
    railToggle: $("[data-rail-toggle]"),
    paneTitle: $("#pane-title"),
    paneSub: $(".pane-sub"),
    dropMain: $("[data-drop-main]"),
    toolCount: $("[data-tool-count]"),
    jobBoard: $("[data-job-board]"),
    jobList: $("[data-job-list]"),
    processBtn: $("[data-process]"),
    processHint: $(".process-hint"),
    clearBtn: $("[data-clear]"),
    langToggle: $("[data-lang-toggle]"),
    langLabel: $("[data-lang-label]"),
    toast: $("[data-toast]"),
  };

  /* ---------- i18n ---------- */
  function t(key, ...args) {
    const v = I18N[state.lang][key];
    return typeof v === "function" ? v(...args) : v;
  }

  function applyLang() {
    document.documentElement.lang = state.lang;
    $$("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (I18N[state.lang][key] !== undefined) el.textContent = t(key);
    });
    els.langLabel.textContent = state.lang === "id" ? "ID" : "EN";
    els.langToggle.title = t("lang_title");
    els.langToggle.setAttribute("aria-pressed", state.lang === "en");

    renderRail();
    renderPane();
    renderOpts();
    renderJobs();
  }

  function activeTool() {
    return TOOL_BY_ID[state.tool];
  }

  /* ---------- Tool rail (grouped) ---------- */
  function renderRail() {
    els.toolCount.textContent = TOOLS.length;
    els.toolGroups.innerHTML = "";
    GROUPS.forEach((g) => {
      const items = TOOLS.filter((x) => x.group === g);
      if (!items.length) return;

      const wrap = document.createElement("div");
      wrap.className = "tool-group";

      const label = document.createElement("div");
      label.className = "tool-group-label";
      label.textContent = t(`group_${g}`);
      wrap.append(label);

      const ul = document.createElement("ul");
      ul.className = "tool-list";
      items.forEach((tool) => {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tool-item";
        btn.dataset.tool = tool.id;
        btn.textContent = t(`tool_${tool.id}`);
        if (tool.id === state.tool) {
          btn.classList.add("is-active");
          btn.setAttribute("aria-current", "true");
        }
        li.append(btn);
        ul.append(li);
      });
      wrap.append(ul);
      els.toolGroups.append(wrap);
    });
  }

  /* ---------- Pane header + drop labels ---------- */
  function renderPane() {
    const tool = activeTool();
    els.paneTitle.textContent = t(`title_${tool.id}`);
    els.paneSub.textContent = t(`sub_${tool.id}`);

    const acc = ACCEPT[tool.accept];
    els.dropMain.textContent = t(`drop_${acc.kind}`);

    els.fileInput.accept = acc.attr;
    els.fileInput.multiple = !!tool.multiple;
  }

  /* ---------- Per-tool options ---------- */
  function optDefaults(tool) {
    const o = {};
    (tool.opts || []).forEach((spec) => { o[spec.key] = spec.def ?? ""; });
    return o;
  }
  function ensureOpts(tool) {
    if (!state.opts[tool.id]) state.opts[tool.id] = optDefaults(tool);
    return state.opts[tool.id];
  }
  function optVisible(spec, values) {
    if (!spec.dependsOn) return true;
    return String(values[spec.dependsOn.key]) === String(spec.dependsOn.value);
  }

  function renderOpts() {
    const tool = activeTool();
    const specs = tool.opts || [];
    if (!specs.length) { els.toolOpts.hidden = true; els.toolOpts.innerHTML = ""; return; }
    els.toolOpts.hidden = false;
    els.toolOpts.innerHTML = "";
    const values = ensureOpts(tool);

    specs.forEach((spec) => {
      if (!optVisible(spec, values)) return;
      const row = document.createElement("div");
      row.className = "opt-row";

      const lab = document.createElement("span");
      lab.className = "opt-label";
      lab.textContent = t(`opt_${spec.key}`);
      row.append(lab);

      if (spec.type === "choice") {
        const box = document.createElement("div");
        box.className = "opt-choices";
        box.setAttribute("role", "radiogroup");
        box.setAttribute("aria-label", t(`opt_${spec.key}`));
        spec.values.forEach((v) => {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "opt-choice";
          b.setAttribute("role", "radio");
          b.dataset.optKey = spec.key;
          b.dataset.optVal = v;
          const on = String(values[spec.key]) === String(v);
          b.setAttribute("aria-checked", on ? "true" : "false");
          if (on) b.classList.add("is-active");
          b.textContent = t(`optval_${spec.key}_${v}`);
          box.append(b);
        });
        row.append(box);
      } else {
        const input = document.createElement("input");
        input.className = "opt-input";
        input.type = spec.inputType || "text";
        input.dataset.optKey = spec.key;
        input.value = values[spec.key] ?? "";
        input.placeholder = t(`ph_${spec.key}`) || "";
        input.autocomplete = "off";
        row.append(input);
      }
      els.toolOpts.append(row);
    });
  }

  /* ---------- Format helpers ---------- */
  function fmtSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  /* ---------- Toast ---------- */
  let toastTimer = null;
  function showToast(msg) {
    els.toast.textContent = msg;
    els.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { els.toast.hidden = true; }, 3200);
  }

  /* ---------- Job state machine (split-flap) ---------- */
  const FLAP_STATES = ["uploaded", "processing", "done", "error"];

  function renderJobs() {
    els.jobBoard.hidden = state.files.length === 0;
    els.jobList.innerHTML = "";

    state.files.forEach((file) => {
      const li = document.createElement("li");
      li.className = "job-card";

      const info = document.createElement("div");
      info.className = "job-info";
      const name = document.createElement("div");
      name.className = "job-name";
      name.textContent = file.name;
      const size = document.createElement("div");
      size.className = "job-size";
      size.textContent = fmtSize(file.size);
      info.append(name, size);

      const flap = document.createElement("div");
      flap.className = "flap";
      flap.dataset.state = file.status;
      flap.setAttribute("role", "status");
      flap.setAttribute("aria-live", "polite");
      const front = document.createElement("span");
      front.className = "flap-face flap-face--front";
      const back = document.createElement("span");
      back.className = "flap-face flap-face--back";
      const setFace = (faceEl, st) => { faceEl.textContent = t(`state_${st}`); faceEl.dataset.state = st; };
      setFace(front, file.status);
      setFace(back, file.status);
      flap.append(front, back);

      const actions = document.createElement("div");
      actions.className = "job-actions";

      // Progress row: only meaningful while the job runs. Built once here so
      // polling can update it in place without touching the flap animation.
      let progressEl = null;
      if (file.status === "processing") {
        progressEl = document.createElement("div");
        progressEl.className = "job-progress";
        const bar = document.createElement("div");
        bar.className = "job-progress-bar";
        bar.setAttribute("role", "progressbar");
        bar.setAttribute("aria-valuemin", "0");
        bar.setAttribute("aria-valuemax", "100");
        const fill = document.createElement("div");
        fill.className = "job-progress-fill";
        const label = document.createElement("span");
        label.className = "job-progress-label";
        bar.append(fill);
        progressEl.append(bar, label);
        file._progEl = progressEl;
        file._progFill = fill;
        file._progLabel = label;
        file._progBar = bar;
        paintProgress(file, file.progress);
      }

      if (file.result) {
        const dl = document.createElement("a");
        dl.className = "icon-btn is-primary";
        dl.href = file.result.url;
        dl.download = file.result.name || "";
        dl.title = t("job_download");
        dl.setAttribute("aria-label", `${t("job_download")} ${file.result.name || ""}`.trim());
        dl.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 19h16"/></svg>';
        actions.append(dl);
      }

      const removeBtn = document.createElement("button");
      removeBtn.className = "icon-btn is-danger";
      removeBtn.type = "button";
      removeBtn.setAttribute("aria-label", `${state.lang === "id" ? "Hapus" : "Remove"} ${file.name}`);
      removeBtn.title = state.lang === "id" ? "Hapus" : "Remove";
      removeBtn.innerHTML =
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>';
      removeBtn.addEventListener("click", () => removeFile(file.id));
      actions.append(removeBtn);

      li.append(info, flap, actions);
      if (progressEl) li.append(progressEl);
      file._flapEl = flap; file._frontEl = front; file._backEl = back;
      els.jobList.append(li);
    });

    els.processBtn.disabled = state.files.length === 0 || state.processing;
    els.processHint.hidden = state.files.length === 0;
  }

  // Overall percent from the backend, clamped to 0-100.
  function paintProgress(file, progress) {
    if (!file._progFill) return;
    const pct = progress && typeof progress.pct === "number" ? progress.pct : 0;
    const stageKey = progress && progress.stage ? progress.stage : "working";
    file._progFill.style.width = `${pct}%`;
    if (file._progBar) file._progBar.setAttribute("aria-valuenow", String(pct));
    if (file._progLabel) {
      const stage = t(`stage_${stageKey}`);
      file._progLabel.textContent = `${pct}% · ${stage}`;
    }
  }

  function setStatus(file, status) {
    if (!FLAP_STATES.includes(status)) return;
    file.status = status;
    const flap = file._flapEl;
    if (!flap) return;
    const front = file._frontEl;
    const back = file._backEl;
    back.textContent = t(`state_${status}`);
    back.dataset.state = status;
    flap.classList.remove("is-flipping");
    void flap.offsetWidth;
    flap.classList.add("is-flipping");
    flap.dataset.state = status;
    setTimeout(() => {
      front.textContent = t(`state_${status}`);
      front.dataset.state = status;
      flap.classList.remove("is-flipping");
      flap.dataset.state = status;
    }, 120);
  }

  /* ---------- File management ---------- */
  function totalSize() {
    return state.files.reduce((sum, f) => sum + f.size, 0);
  }

  function addFiles(fileList) {
    const tool = activeTool();
    const acc = ACCEPT[tool.accept];
    const incoming = Array.from(fileList).filter((f) => acc.test(f));
    if (!incoming.length) {
      showToast(t("toast_wrong_type", acc.kind));
      return;
    }

    if (!tool.multiple && state.files.length) {
      state.files = [];
      showToast(t("toast_single"));
    }

    const toAdd = [];
    let rejectedLarge = 0;
    incoming.forEach((f) => {
      if (f.size / (1024 * 1024) > MAX_FILE_MB) { rejectedLarge++; return; }
      if (state.files.some((x) => x.name === f.name && x.size === f.size)) return;
      toAdd.push({
        id: crypto.randomUUID(), name: f.name, size: f.size, status: "uploaded",
        file: f, result: null, error: "", progress: null,
        _flapEl: null, _frontEl: null, _backEl: null,
      });
    });

    if (!tool.multiple && toAdd.length > 1) toAdd.length = 1;

    if (toAdd.length) {
      const addedSize = toAdd.reduce((s, f) => s + f.size, 0);
      if (totalSize() + addedSize > MAX_JOB_MB * 1024 * 1024) {
        showToast(t("toast_job_over"));
        return;
      }
      state.files.push(...toAdd);
    }

    renderJobs();
    if (toAdd.length) showToast(t("toast_added", toAdd.length));
    if (rejectedLarge) showToast(t("toast_too_large", "file"));
  }

  function removeFile(id) {
    const idx = state.files.findIndex((f) => f.id === id);
    if (idx === -1) return;
    state.files.splice(idx, 1);
    renderJobs();
    showToast(t("toast_removed"));
  }

  function clearJobs() {
    state.files = [];
    renderJobs();
    showToast(t("toast_cleared"));
  }

  /* ---------- Processing pipeline (talks to the FastAPI backend) ---------- */
  const API = "/api";

  async function submitJob(tool, values, files) {
    const fd = new FormData();
    fd.append("tool", tool.id);
    fd.append("options", JSON.stringify(values));
    files.forEach((f) => fd.append("files", f.file, f.name));
    const res = await fetch(`${API}/jobs`, { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || t("toast_error"));
    return data;
  }

  async function pollJob(id) {
    const deadline = Date.now() + 5 * 60 * 1000;
    for (;;) {
      const res = await fetch(`${API}/jobs/${id}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("toast_error"));
      // Paint progress in place: a full re-render would restart the flap.
      state.files.forEach((file) => paintProgress(file, data.progress));
      if (data.status === "done") return data;
      if (data.status === "error") throw new Error(data.error || t("toast_error"));
      if (Date.now() > deadline) throw new Error(t("toast_timeout"));
      await new Promise((r) => setTimeout(r, 600));
    }
  }

  async function runProcessing() {
    if (state.processing || !state.files.length) return;
    state.processing = true;
    state.files.forEach((file) => { file.result = null; file.error = ""; file.progress = null; setStatus(file, "processing"); });
    renderJobs();
    showToast(t("toast_processing"));

    const tool = activeTool();
    try {
      const job = await submitJob(tool, ensureOpts(tool), state.files);
      const final = await pollJob(job.id);
      const first = (final.files && final.files[0]) || {};
      const url = (final.downloads && final.downloads[0]) || `${API}/jobs/${job.id}/download`;
      state.files.forEach((file) => { file.result = { url, name: first.name || "" }; setStatus(file, "done"); });
      showToast(t("toast_done"));
    } catch (err) {
      const msg = (err && err.message) || t("toast_error");
      state.files.forEach((file) => { file.error = msg; setStatus(file, "error"); });
      showToast(msg);
    } finally {
      state.processing = false;
      renderJobs();
    }
  }

  /* ---------- Events ---------- */
  function openPicker() { els.fileInput.click(); }

  els.dropZone.addEventListener("click", (e) => {
    if (e.target.closest("[data-browse]")) return;
    openPicker();
  });
  els.dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPicker(); }
  });
  els.browseBtn.addEventListener("click", (e) => { e.stopPropagation(); openPicker(); });
  els.fileInput.addEventListener("change", () => {
    addFiles(els.fileInput.files);
    els.fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropZone.addEventListener(ev, (e) => { e.preventDefault(); els.dropZone.classList.add("is-dragging"); });
  });
  ["dragleave", "drop"].forEach((ev) => {
    els.dropZone.addEventListener(ev, (e) => { e.preventDefault(); els.dropZone.classList.remove("is-dragging"); });
  });
  els.dropZone.addEventListener("drop", (e) => { addFiles(e.dataTransfer.files); });
  ["dragover", "drop"].forEach((ev) => {
    window.addEventListener(ev, (e) => e.preventDefault());
  });

  // Tool selection (delegated: rail is re-rendered on language change)
  els.toolGroups.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tool]");
    if (!btn) return;
    state.tool = btn.dataset.tool;
    state.files = [];
    state.processing = false;
    renderRail();
    renderPane();
    renderOpts();
    renderJobs();
    // On mobile, picking a tool collapses the catalog so the work pane
    // is right there; on desktop the toggle is hidden and this is a no-op.
    if (NARROW.matches) {
      setRailOpen(false);
      document.querySelector(".tool-pane").scrollIntoView({ block: "start" });
    }
  });

  // Option interactions (delegated: options are re-rendered)
  els.toolOpts.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-opt-val]");
    if (!btn) return;
    const tool = activeTool();
    const values = ensureOpts(tool);
    values[btn.dataset.optKey] = btn.dataset.optVal;
    renderOpts();
  });
  els.toolOpts.addEventListener("input", (e) => {
    const input = e.target.closest("[data-opt-key]");
    if (!input || input.tagName !== "INPUT") return;
    const tool = activeTool();
    ensureOpts(tool)[input.dataset.optKey] = input.value;
  });
  els.toolOpts.addEventListener("change", (e) => {
    const input = e.target.closest("input[type=password]");
    if (!input) return;
    // no-op: values captured on input; placeholder for future validation
  });

  els.processBtn.addEventListener("click", runProcessing);
  els.clearBtn.addEventListener("click", clearJobs);

  // Catalog toggle on narrow screens. Below 860px the catalog starts
  // collapsed and this button reveals it; above it the button is hidden
  // by CSS and the catalog is always visible.
  const NARROW = window.matchMedia("(max-width: 860px)");
  function setRailOpen(open) {
    els.toolGroups.classList.toggle("is-open", open);
    els.railToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }
  els.railToggle.addEventListener("click", () => {
    setRailOpen(!els.toolGroups.classList.contains("is-open"));
  });
  // Follow the breakpoint both ways: narrowing collapses the catalog,
  // widening (toggle is CSS-hidden there) leaves it fully open.
  NARROW.addEventListener("change", (e) => setRailOpen(!e.matches));
  setRailOpen(!NARROW.matches);

  els.langToggle.addEventListener("click", () => {
    state.lang = state.lang === "id" ? "en" : "id";
    applyLang();
  });

  /* ---------- Init ---------- */
  applyLang();
})();
