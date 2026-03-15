/* global __renderIcons, __renderMath */

// Subject -> dataset URLs (first one that exists will be used).
// Mathematics prefers the full generated dataset, and falls back to the small sample.
const SUBJECT_DATASETS = {
  Mathematics: ['data/maths_data.json'],
  Science: ['data/science.json'],
  'Social Science': ['data/social_science.json'],
  English: ['data/english.json'],
};

const STORAGE = {
  subject: 'cbse10_subject_v1',
  chapter: 'cbse10_chapter_v1',
  masteredPrefix: 'cbse10_mastered_',
};

const FALLBACK_MATH_CHAPTERS = [
  'Real Numbers',
  'Polynomials',
  'Pair of Linear Equations',
  'Quadratic Equations',
  'Arithmetic Progressions',
  'Triangles',
  'Coordinate Geometry',
  'Trigonometry',
  'Circles',
  'Constructions',
  'Areas Related to Circles',
  'Surface Areas and Volumes',
  'Statistics',
  'Probability',
];

let state = {
  subject: 'Mathematics',
  chapter: null,
  query: '',
  filterMode: 'all', // all | hf | repeated | mastered | unmastered
};

let dataset = {
  chapters: [],
  questions: [],
};

let masteredIds = new Set();
let lastDataLoadError = '';
let lastRuntimeError = '';

function setRuntimeError(message) {
  lastRuntimeError = String(message || '');
}

window.addEventListener('error', (e) => {
  if (!e) return;
  const msg = e.message || (e.error && e.error.message) || 'Unknown error';
  setRuntimeError(msg);
});

window.addEventListener('unhandledrejection', (e) => {
  const msg = (e && e.reason && (e.reason.message || String(e.reason))) || 'Unhandled promise rejection';
  setRuntimeError(msg);
});

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text == null ? '' : String(text);
  return div.innerHTML;
}

function normalize(text) {
  return (text || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function readMastered() {
  const key = `${STORAGE.masteredPrefix}${state.subject}_v1`;
  try {
    const raw = localStorage.getItem(key);
    const list = raw ? JSON.parse(raw) : [];
    masteredIds = new Set(Array.isArray(list) ? list : []);
  } catch {
    masteredIds = new Set();
  }
}

function writeMastered() {
  const key = `${STORAGE.masteredPrefix}${state.subject}_v1`;
  localStorage.setItem(key, JSON.stringify(Array.from(masteredIds)));
}

function uniq(arr) {
  return Array.from(new Set(arr));
}

function deriveChaptersFromQuestions(questions) {
  const names = uniq(questions.map((q) => q.chapter).filter(Boolean));
  // Keep order close to Oswaal chapter order when possible.
  const ordered = [];
  for (const c of FALLBACK_MATH_CHAPTERS) {
    if (names.includes(c)) ordered.push(c);
  }
  for (const c of names) {
    if (!ordered.includes(c)) ordered.push(c);
  }
  return ordered;
}

function toArrayYears(val) {
  if (Array.isArray(val)) return val;
  if (!val) return [];
  if (typeof val === 'string') {
    return val
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => Number(s) || s);
  }
  return [];
}

function normalizeDataset(raw) {
  // Supports:
  // 1) Array of questions (Prompt-3 style sample)
  // 2) Object {chapters:[...], questions:[...]} (our generator)
  let questions = [];
  let chapters = [];

  if (Array.isArray(raw)) {
    questions = raw;
    const chapterNames = deriveChaptersFromQuestions(questions);
    chapters = chapterNames.map((name) => ({ name }));
  } else {
    questions = Array.isArray(raw?.questions) ? raw.questions : [];
    chapters = Array.isArray(raw?.chapters) ? raw.chapters : [];

    if (!chapters.length && questions.length) {
      chapters = deriveChaptersFromQuestions(questions).map((name) => ({ name }));
    }
  }

  // Normalize question fields to one shape.
  const normalizedQuestions = questions.map((q, idx) => {
    const years = toArrayYears(q.years_appeared || q.years || []);
    const solutionSteps = Array.isArray(q.solution_steps) ? q.solution_steps : Array.isArray(q.solutionSteps) ? q.solutionSteps : [];

    return {
      id: q.id || `${normalize(q.chapter || 'chapter')}|${idx}`,
      subject: q.subject || state.subject,
      chapter: q.chapter || 'Unknown',
      marks: Number(q.marks || 1),
      frequency: Number(q.frequency || years.length || 1),
      text: q.question_text || q.text || '',
      years: years.map((y) => String(y)),
      solution_steps: solutionSteps,
      solution: q.solution_text || q.solution || '',
      // Accept both singular + plural forms.
      common_errors: Array.isArray(q.common_errors)
        ? q.common_errors
        : q.common_error
          ? [q.common_error]
          : Array.isArray(q.common_errors_box)
            ? q.common_errors_box
            : [],
      toppers_secrets: Array.isArray(q.toppers_secrets)
        ? q.toppers_secrets
        : q.toppers_tip
          ? [q.toppers_tip]
          : q.toppers_secrets_box
            ? q.toppers_secrets_box
            : [],
    };
  });

  const normalizedChapters = chapters.map((c) => ({
    name: c.name || c.chapter || c,
    errors: c.errors || [],
    secrets: c.secrets || [],
    mind_map_note: c.mind_map_note || c.mindMapNote || '',
  }));

  return {
    chapters: normalizedChapters,
    questions: normalizedQuestions,
  };
}

async function fetchSubjectData(subject) {
  const urls = SUBJECT_DATASETS[subject] || [];
  if (!urls.length) return { chapters: [], questions: [] };

  let lastError = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) {
        lastError = new Error(`Failed to fetch ${url}: ${res.status}`);
        continue;
      }
      const raw = await res.json();
      return normalizeDataset(raw);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error(`No dataset found for subject: ${subject}`);
}

function setChapterMetaFromData(chapterName) {
  const chapterInfo = dataset.chapters.find((c) => c.name === chapterName) || { errors: [], secrets: [], mind_map_note: '' };

  const chapterQs = dataset.questions.filter((q) => q.chapter === chapterName);

  // If chapter-level meta not present, derive from question fields.
  const chapterErrors = Array.isArray(chapterInfo.errors) ? chapterInfo.errors : [];
  const chapterSecrets = Array.isArray(chapterInfo.secrets) ? chapterInfo.secrets : [];
  const errors = chapterErrors.length ? chapterErrors : uniq(chapterQs.flatMap((q) => q.common_errors)).slice(0, 4);
  const secrets = chapterSecrets.length ? chapterSecrets : uniq(chapterQs.flatMap((q) => q.toppers_secrets)).slice(0, 4);

  $('errorsBox').innerHTML = (errors.length ? errors : [
    'Arithmetic slips (signs, fractions, simplification).',
    'Not writing the correct formula/theorem before applying.',
    'Messy layout: unclear steps or missing final answer box.',
  ]).slice(0, 4).map((e) => `<li>${escapeHtml(e)}</li>`).join('');

  $('secretsBox').innerHTML = (secrets.length ? secrets : [
    'Underline the given and what is asked.',
    'Keep steps short and aligned; avoid skipping logic.',
    'Write units/conditions and box the final answer.',
  ]).slice(0, 4).map((s) => `<li>${escapeHtml(s)}</li>`).join('');

  $('mindMapTitle').innerText = `${chapterName} Mind Map`;
  $('mindMapNote').innerText = chapterInfo.mind_map_note || 'Placeholder: add your mind map image or link here.';
}

function renderProgress(chapterName) {
  const qs = dataset.questions.filter((q) => q.chapter === chapterName);
  const total = qs.length;
  let mastered = 0;
  for (const q of qs) {
    if (masteredIds.has(q.id)) mastered += 1;
  }
  const pct = total ? Math.round((mastered / total) * 100) : 0;

  $('progressText').innerText = `${mastered}/${total} questions mastered`;
  $('progressPct').innerText = `${pct}%`;
  $('progressBar').style.width = `${pct}%`;

  $('chapterBadge').classList.remove('hidden');
  $('chapterMeta').innerText = `${total} questions`;
}

function renderHeader() {
  $('currentChapter').innerText = state.chapter || 'Select a chapter';
  renderProgress(state.chapter);
  if (typeof __renderIcons === 'function') __renderIcons();
}

function renderSidebar() {
  const list = $('chapterList');
  const chapters = state.subject === 'Mathematics'
    ? FALLBACK_MATH_CHAPTERS
    : (dataset.chapters.length ? dataset.chapters.map((c) => c.name) : []);
  $('chapterCount').innerText = `${chapters.length}`;

  const html = chapters
    .map((name) => {
      const active = name === state.chapter;
      const base = 'w-full text-left px-3 py-2 rounded-xl border transition flex items-center justify-between gap-3';
      const cls = active
        ? `${base} bg-white/12 border-amberPrime-500/35 shadow-glow`
        : `${base} bg-white/5 hover:bg-white/10 border-white/10`;

      return `
        <button class="${cls}" data-chapter="${escapeHtml(name)}">
          <span class="text-sm font-medium truncate">${escapeHtml(name)}</span>
          <span class="text-xs text-white/60 flex items-center gap-2">
            <i data-lucide="chevron-right" class="h-4 w-4"></i>
          </span>
        </button>
      `;
    })
    .join('');

  list.innerHTML = `<div class="space-y-2">${html}</div>`;

  for (const btn of list.querySelectorAll('button[data-chapter]')) {
    btn.addEventListener('click', () => {
      const ch = btn.getAttribute('data-chapter');
      loadContent(state.subject, ch);
    });
  }

  if (typeof __renderIcons === 'function') __renderIcons();
}

function yearsLine(q) {
  const years = q.years || [];
  if (!years.length) return '';
  return `<div class="mt-2 text-xs text-slate-600 flex items-center gap-2">
    <i data-lucide="calendar" class="h-4 w-4"></i>
    <span class="font-medium">Years:</span>
    <span>${escapeHtml(years.join(', '))}</span>
  </div>`;
}

function highFrequencyBadge(q) {
  const years = q.years || [];
  if (years.length >= 2 || q.frequency >= 2) {
    return `<span class="inline-flex items-center gap-2 text-[11px] px-2.5 py-1 rounded-full bg-amberPrime-500 text-white shadow-glow">
      <span>🔥</span>
      <span class="font-semibold tracking-wide">REPEATED QUESTION</span>
    </span>`;
  }
  return '';
}

function solutionInner(q) {
  const steps = Array.isArray(q.solution_steps) ? q.solution_steps : [];
  if (steps.length) {
    const items = steps.map((s) => `<li class="leading-relaxed">${s}</li>`).join('');
    return `<ol class="list-decimal pl-5 space-y-1">${items}</ol>`;
  }
  if (q.solution) {
    return `<div class="whitespace-pre-wrap leading-relaxed">${q.solution}</div>`;
  }
  return `<div class="text-slate-600 text-sm">Solution not available in this dataset yet.</div>`;
}

function cardTemplate(q) {
  const mastered = masteredIds.has(q.id);
  const border = mastered ? 'border-emerald-400 ring-2 ring-emerald-200/60' : 'border-slate-200';

  return `
    <article class="rounded-2xl bg-white border ${border} shadow-card p-4 transition" data-card="${escapeHtml(q.id)}">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="text-sm font-semibold leading-snug whitespace-pre-wrap">
            ${q.text}
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-2">${highFrequencyBadge(q)}</div>
          ${yearsLine(q)}
        </div>

        <div class="shrink-0">
          <span class="inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-slate-100 border border-slate-200">
            <i data-lucide="badge" class="h-4 w-4 text-slate-600"></i>
            <span class="font-medium">${Number(q.marks || 1)} Marks</span>
          </span>
        </div>
      </div>

      <div class="mt-3 flex items-center justify-between gap-3">
        <button class="text-xs px-3 py-2 rounded-xl bg-amberPrime-500 text-white hover:bg-amberPrime-600 shadow-glow flex items-center gap-2" data-action="toggle" data-qid="${escapeHtml(q.id)}">
          <i data-lucide="maximize-2" class="h-4 w-4"></i>
          <span>Show Solution</span>
        </button>

        <label class="inline-flex items-center gap-2 text-xs text-slate-700 select-none">
          <input type="checkbox" class="h-4 w-4 rounded border-slate-300 text-emerald-600" data-action="mastered" data-qid="${escapeHtml(q.id)}" ${mastered ? 'checked' : ''} />
          <span class="font-medium">Mark as Mastered</span>
        </label>
      </div>

      <div class="mt-4 overflow-hidden max-h-0 opacity-0 transition-all duration-300" id="sol-${escapeHtml(q.id)}" data-solution="closed">
        <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div class="text-xs font-semibold text-slate-700 flex items-center gap-2">
            <i data-lucide="scroll-text" class="h-4 w-4"></i>
            <span>Step-by-step solution</span>
          </div>
          <div class="mt-2 text-sm text-slate-800">${solutionInner(q)}</div>
        </div>
      </div>
    </article>
  `;
}

function applyFilters(questions) {
  let out = questions.slice();

  if (state.query) {
    const qn = normalize(state.query);
    out = out.filter((q) => normalize(q.text).includes(qn));
  }

  if (state.filterMode === 'hf' || state.filterMode === 'repeated') {
    out = out.filter((q) => (q.years || []).length >= 2 || (q.frequency || 1) >= 2);
  } else if (state.filterMode === 'mastered') {
    out = out.filter((q) => masteredIds.has(q.id));
  } else if (state.filterMode === 'unmastered') {
    out = out.filter((q) => !masteredIds.has(q.id));
  }

  return out;
}

function setEmptyState(show) {
  const empty = $('emptyState');
  if (show) empty.classList.remove('hidden');
  else empty.classList.add('hidden');
}

function toggleSolution(qid) {
  const el = document.getElementById(`sol-${qid}`);
  if (!el) return;

  const open = el.getAttribute('data-solution') === 'open';
  if (open) {
    el.style.maxHeight = `${el.scrollHeight}px`;
    // allow layout flush
    requestAnimationFrame(() => {
      el.style.maxHeight = '0px';
      el.style.opacity = '0';
      el.setAttribute('data-solution', 'closed');
    });
  } else {
    el.style.maxHeight = `${el.scrollHeight}px`;
    el.style.opacity = '1';
    el.setAttribute('data-solution', 'open');
    if (typeof __renderMath === 'function') __renderMath(el);
  }
}

function renderGrid() {
  const grid = $('grid');
  const chapterQuestions = dataset.questions.filter((q) => q.chapter === state.chapter);
  const filtered = applyFilters(chapterQuestions).slice();

  // Most repeated first within the chapter, then marks (descending), then text length.
  filtered.sort((a, b) => {
    const fa = (a.years || []).length || a.frequency || 1;
    const fb = (b.years || []).length || b.frequency || 1;
    if (fb !== fa) return fb - fa;
    if ((b.marks || 0) !== (a.marks || 0)) return (b.marks || 0) - (a.marks || 0);
    return (b.text || '').length - (a.text || '').length;
  });

  $('currentChapter').innerText = state.chapter || 'Select a chapter';
  renderProgress(state.chapter);
  const status = $('dataStatus');
  if (status) {
    const s = lastRuntimeError ? ` Runtime error: ${lastRuntimeError}` : '';
    status.innerText = `Loaded ${dataset.questions.length} questions. Chapter has ${chapterQuestions.length}. Showing ${filtered.length}.${s}`;
  }

  if (!filtered.length) {
    grid.innerHTML = '';
    setEmptyState(true);

    const empty = $('emptyState');
    if (lastRuntimeError) {
      empty.innerHTML =
        '<div class=\"max-w-xl\">' +
        '<div class=\"text-lg font-semibold\">Dashboard error</div>' +
        '<div class=\"mt-1 text-sm\">' + escapeHtml(lastRuntimeError) + '</div>' +
        '<div class=\"mt-3 text-sm\">Open DevTools Console for details.</div>' +
        '</div>';
    } else if (lastDataLoadError) {
      empty.innerHTML =
        '<div class="max-w-xl">' +
        '<div class="text-lg font-semibold">Data not loaded</div>' +
        '<div class="mt-1 text-sm">' + escapeHtml(lastDataLoadError) + '</div>' +
        '<div class="mt-3 text-sm">Open the dashboard via the local server (not file://):</div>' +
        '<div class="mt-1 text-sm font-mono bg-white rounded-xl border border-slate-200 px-3 py-2">http://127.0.0.1:5173</div>' +
        '</div>';
    } else {
      empty.innerHTML =
        '<div class="max-w-xl">' +
        '<div class="text-lg font-semibold">No questions found</div>' +
        '<div class="mt-1 text-sm">Try another chapter, clear filters, or adjust search.</div>' +
        '</div>';
    }
  } else {
    setEmptyState(false);
    // Group by marks with separators (1, 2, 5 are emphasized, but we include others if present).
    const groups = new Map();
    for (const q of filtered) {
      const m = Number(q.marks || 1);
      const key = [1, 2, 5].includes(m) ? m : m;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(q);
    }

    const preferredOrder = [5, 4, 3, 2, 1];
    const keys = Array.from(groups.keys()).sort((a, b) => {
      const ia = preferredOrder.indexOf(a);
      const ib = preferredOrder.indexOf(b);
      if (ia === -1 && ib === -1) return b - a;
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });

    const parts = [];
    for (const k of keys) {
      const label = `${k} Mark${k === 1 ? '' : 's'}`;
      parts.push(
        `<div class="col-span-1 lg:col-span-2 2xl:col-span-3 mt-2">
          <div class="flex items-center justify-between">
            <div class="text-sm font-semibold text-slate-800">${label}</div>
            <div class="h-px flex-1 ml-3 bg-slate-200"></div>
          </div>
        </div>`
      );
      parts.push((groups.get(k) || []).map(cardTemplate).join(''));
    }

    grid.innerHTML = parts.join('');
  }

  for (const btn of grid.querySelectorAll('[data-action="toggle"]')) {
    btn.addEventListener('click', () => toggleSolution(btn.getAttribute('data-qid')));
  }

  for (const cb of grid.querySelectorAll('[data-action="mastered"]')) {
    cb.addEventListener('change', () => {
      const qid = cb.getAttribute('data-qid');
      if (cb.checked) masteredIds.add(qid);
      else masteredIds.delete(qid);
      writeMastered();
      renderSidebar();
      renderHeader();
      renderGrid();
    });
  }

  if (typeof __renderIcons === 'function') __renderIcons();
  if (typeof __renderMath === 'function') __renderMath(grid);
}

async function loadSubject(subject) {
  state.subject = subject;
  localStorage.setItem(STORAGE.subject, subject);

  readMastered();

  try {
    dataset = await fetchSubjectData(subject);
    lastDataLoadError = '';
  } catch (err) {
    console.error(err);
    dataset = { chapters: [], questions: [] };
    lastDataLoadError = String(err?.message || err || 'Failed to load dataset');
  }

  // If dataset lacks subject, treat all as current subject.
  for (const q of dataset.questions) {
    q.subject = subject;
  }

  // Always show the full 14-chapter sidebar for Maths, even if some chapters have 0 questions.
  if (subject === 'Mathematics') {
    dataset.chapters = FALLBACK_MATH_CHAPTERS.map((name) => ({ name, errors: [], secrets: [], mind_map_note: '' }));
  }

  // Pick chapter
  const chapters = subject === 'Mathematics'
    ? FALLBACK_MATH_CHAPTERS
    : (dataset.chapters.length ? dataset.chapters.map((c) => c.name) : []);

  const savedChapterKey = `${STORAGE.chapter}_${subject}`;
  const savedChapter = localStorage.getItem(savedChapterKey);
  const firstChapter = chapters[0] || null;

  state.chapter = chapters.includes(savedChapter) ? savedChapter : firstChapter;

  renderSidebar();
  if (state.chapter) {
    setChapterMetaFromData(state.chapter);
  }
  renderHeader();
  renderGrid();

  if (typeof __renderIcons === 'function') __renderIcons();
}

function loadContent(subject, chapter) {
  // Called by sidebar clicks.
  if (subject !== state.subject) {
    // If subject mismatch, switch subject first then set chapter.
    $('subjectSelect').value = subject;
    loadSubject(subject).then(() => {
      loadContent(subject, chapter);
    });
    return;
  }

  state.chapter = chapter;
  localStorage.setItem(`${STORAGE.chapter}_${subject}`, chapter);

  renderSidebar();
  setChapterMetaFromData(chapter);
  renderHeader();
  renderGrid();
  if (typeof __renderMath === 'function') __renderMath(document.body);
}

function wireHeaderControls() {
  $('searchBox').addEventListener('input', (e) => {
    state.query = e.target.value || '';
    renderGrid();
  });

  $('btnShowAll').addEventListener('click', (e) => {
    e.preventDefault();
    state.query = '';
    $('searchBox').value = '';
    state.filterMode = 'all';
    renderGrid();
  });

  $('btnOnlyRepeated').addEventListener('click', () => {
    state.filterMode = 'repeated';
    renderGrid();
  });

  $('btnOnlyHF').addEventListener('click', () => {
    state.filterMode = 'hf';
    renderGrid();
  });

  $('btnOnlyMastered').addEventListener('click', () => {
    state.filterMode = 'mastered';
    renderGrid();
  });

  $('btnOnlyUnmastered').addEventListener('click', () => {
    state.filterMode = 'unmastered';
    renderGrid();
  });

  $('btnReset').addEventListener('click', () => {
    if (!confirm('Reset mastered progress for this subject?')) return;
    masteredIds = new Set();
    writeMastered();
    renderHeader();
    renderGrid();
  });

  $('btnHelp').addEventListener('click', (e) => {
    e.preventDefault();
    alert(
      'How to use:\n\n1) Pick a subject, then a chapter.\n2) Use search/filters to find questions.\n3) Show solution and mark mastered.\n\nHigh Frequency = appeared in 3+ years.'
    );
  });
}

async function init() {
  // Subject select
  const subjectSelect = $('subjectSelect');
  const savedSubject = localStorage.getItem(STORAGE.subject) || 'Mathematics';
  state.subject = SUBJECT_DATASETS[savedSubject] ? savedSubject : 'Mathematics';
  subjectSelect.value = state.subject;

  subjectSelect.addEventListener('change', () => {
    state.query = '';
    $('searchBox').value = '';
    state.filterMode = 'all';
    loadSubject(subjectSelect.value);
  });

  wireHeaderControls();

  await loadSubject(state.subject);

  // Contract: auto-select first chapter and call loadContent.
  if (state.chapter) {
    loadContent(state.subject, state.chapter);
  }
}

window.loadContent = loadContent;

document.addEventListener('DOMContentLoaded', init);
