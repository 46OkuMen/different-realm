/* ── Different Realm Script Viewer — app.js ─────────── */

(function () {
  'use strict';

  const DATA = window.DR_VIEWER_DATA;
  if (!DATA) {
    document.body.textContent = 'Error: viewer-data.js not loaded.';
    return;
  }

  // ── PC-98 color map ──────────────────────────────
  const COLOR_MAP = {
    Color1: 'c-Color1',
    Color2: 'c-Color2',
    Color3: 'c-Color3',
    Color4: 'c-Color4',
    Color5: 'c-Color5',
    Color6: 'c-Color6',
    Color7: 'c-Color7',
  };

  // ── State ────────────────────────────────────────
  let allRecords = DATA.records;
  let filtered = allRecords.slice();
  let currentIndex = 0;
  let currentPage = 0;
  let showTags = false;

  // ── DOM refs ─────────────────────────────────────
  const $fileFilter   = document.getElementById('fileFilter');
  const $pathFilter   = document.getElementById('pathFilter');
  const $searchInput  = document.getElementById('searchInput');
  const $progressLabel = document.getElementById('progressLabel');
  const $progressFill = document.getElementById('progressFill');
  const $validationLabel = document.getElementById('validationLabel');
  const $prevBtn      = document.getElementById('prevButton');
  const $nextBtn      = document.getElementById('nextButton');
  const $counter      = document.getElementById('recordCounter');
  const $matchCount   = document.getElementById('matchCount');
  const $recordList   = document.getElementById('recordList');
  const $gameText     = document.getElementById('gameText');
  const $pageInd      = document.getElementById('pageIndicator');
  const $blockMeta    = document.getElementById('blockMeta');
  const $rawText      = document.getElementById('rawText');
  const $englishText  = document.getElementById('englishText');
  const $validationSummary = document.getElementById('validationSummary');
  const $validationIssues = document.getElementById('validationIssues');
  const $sideBySide   = document.getElementById('sideBySidePanel');
  const $gameStage     = document.getElementById('gameStage');
  const $textwinUp     = document.getElementById('textwinUp');
  const $textwinDown   = document.getElementById('textwinDown');
  const $portraitUpLabel = document.getElementById('portraitUpLabel');
  const $portraitDownLabel = document.getElementById('portraitDownLabel');
  const $areaName      = document.getElementById('areaName');
  const $langMode     = document.getElementById('langMode');
  const $showTags     = document.getElementById('showTagsToggle');
  const $hideEmpty    = document.getElementById('hideEmptyToggle');
  const $onlyWarnings = document.getElementById('onlyWarningsToggle');
  const $fileMapGrid  = document.getElementById('fileMapGrid');

  // ── Initialize ───────────────────────────────────

  function init() {
    buildFileFilter();
    updateProgress();
    buildFileMap();

    $fileFilter.addEventListener('change', applyFilters);
    $pathFilter.addEventListener('change', applyFilters);
    $searchInput.addEventListener('input', debounce(applyFilters, 200));
    $prevBtn.addEventListener('click', () => navigate(-1));
    $nextBtn.addEventListener('click', () => navigate(1));
    $langMode.addEventListener('change', renderCurrent);
    $showTags.addEventListener('change', () => { showTags = $showTags.checked; renderCurrent(); });
    $hideEmpty.addEventListener('change', applyFilters);
    $onlyWarnings.addEventListener('change', applyFilters);

    // Tab switching
    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Keyboard navigation
    document.addEventListener('keydown', onKeyDown);

    applyFilters();
  }

  // ── File filter dropdown ─────────────────────────

  function buildFileFilter() {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = `All files (${DATA.meta.fileCount})`;
    $fileFilter.appendChild(opt);

    for (const f of DATA.meta.files) {
      const o = document.createElement('option');
      o.value = f;
      const count = allRecords.filter(r => r.file === f).length;
      o.textContent = `${f} (${count})`;
      $fileFilter.appendChild(o);
    }

    // Default to the first game file
    if (DATA.meta.files.includes('AT01.TOS')) {
      $fileFilter.value = 'AT01.TOS';
    }
  }

  // ── Progress bar ─────────────────────────────────

  function updateProgress() {
    const total = DATA.meta.totalBlocks;
    const done = DATA.meta.translatedBlocks;
    const pct = total > 0 ? ((done / total) * 100).toFixed(1) : '0.0';
    $progressLabel.textContent = `${done} / ${total} (${pct}%)`;
    $progressFill.style.width = `${pct}%`;

    const validationBlocks = DATA.meta.validationBlocks || 0;
    const validationIssues = DATA.meta.validationIssues || 0;
    $validationLabel.textContent = validationIssues > 0
      ? `${validationBlocks} block${validationBlocks === 1 ? '' : 's'} flagged · ${validationIssues} warning${validationIssues === 1 ? '' : 's'}`
      : 'No validator warnings in current viewer data.';
  }

  // ── Filtering ────────────────────────────────────

  function applyFilters() {
    const fileVal = $fileFilter.value;
    const pathVal = $pathFilter.value;
    const query = $searchInput.value.toLowerCase().trim();
    const hideEmpty = $hideEmpty.checked;
    const onlyWarnings = $onlyWarnings.checked;

    filtered = allRecords.filter(r => {
      if (fileVal && r.file !== fileVal) return false;
      if (pathVal && r.path !== pathVal) return false;
      if (hideEmpty && !r.text.trim()) return false;
      if (onlyWarnings && (!r.validation || r.validation.issueCount === 0)) return false;
      if (query) {
        const haystack = (r.text + ' ' + r.raw + ' ' + r.file + ' ' + r.english).toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });

    currentIndex = 0;
    currentPage = 0;
    buildRecordList();
    renderCurrent();
    $matchCount.textContent = `${filtered.length} of ${allRecords.length}`;
  }

  // ── Record list ──────────────────────────────────

  function buildRecordList() {
    $recordList.innerHTML = '';

    // Virtual scrolling: only render visible items
    const fragment = document.createDocumentFragment();
    const max = Math.min(filtered.length, 500); // cap for performance
    for (let i = 0; i < max; i++) {
      const r = filtered[i];
      const div = document.createElement('div');
      div.className = 'record-item' + (i === currentIndex ? ' active' : '');
      div.dataset.index = i;

      const preview = r.text.replace(/\n/g, ' ').substring(0, 50);
      const warningCount = r.validation ? r.validation.issueCount : 0;

      div.innerHTML =
        `<div class="record-item-header">` +
          `<span class="record-file">${esc(r.file)}</span>` +
          `<span class="record-block">Block ${r.block}</span>` +
        `</div>` +
        `<div class="record-preview">${esc(preview)}</div>` +
        (r.english ? '<div class="record-translated">Translated</div>' : '') +
        (warningCount ? `<div class="record-warning">${warningCount} warning${warningCount === 1 ? '' : 's'}</div>` : '');

      div.addEventListener('click', () => selectRecord(i));
      fragment.appendChild(div);
    }

    if (filtered.length > 500) {
      const note = document.createElement('div');
      note.className = 'record-item';
      note.style.color = 'var(--muted)';
      note.style.textAlign = 'center';
      note.textContent = `… and ${filtered.length - 500} more. Refine your search.`;
      fragment.appendChild(note);
    }

    $recordList.appendChild(fragment);
  }

  function selectRecord(idx) {
    if (idx < 0 || idx >= filtered.length) return;
    currentIndex = idx;
    currentPage = 0;
    highlightActive();
    renderCurrent();
  }

  function highlightActive() {
    $recordList.querySelectorAll('.record-item.active').forEach(el => el.classList.remove('active'));
    const active = $recordList.querySelector(`[data-index="${currentIndex}"]`);
    if (active) {
      active.classList.add('active');
      active.scrollIntoView({ block: 'nearest' });
    }
  }

  // ── Navigation ───────────────────────────────────

  function navigate(delta) {
    const newIdx = currentIndex + delta;
    if (newIdx >= 0 && newIdx < filtered.length) {
      selectRecord(newIdx);
    }
  }

  function onKeyDown(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); navigate(1); }
    else if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); navigate(-1); }
    else if (e.key === 'ArrowRight' || e.key === 'l') { e.preventDefault(); changePage(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'h') { e.preventDefault(); changePage(-1); }
  }

  // ── Rendering ────────────────────────────────────

  function renderCurrent() {
    if (filtered.length === 0) {
      $gameStage.className = 'game-stage show-lower-text';
      $textwinDown.appendChild($gameText);
      $textwinDown.appendChild($pageInd);
      $gameText.innerHTML = '<span style="color:var(--muted)">No matching blocks.</span>';
      $pageInd.innerHTML = '';
      $blockMeta.innerHTML = '';
      $rawText.textContent = '';
      $counter.textContent = '0 / 0';
      $areaName.textContent = '';
      $validationSummary.textContent = '';
      $validationIssues.innerHTML = '';
      return;
    }

    const r = filtered[currentIndex];
    $counter.textContent = `${currentIndex + 1} / ${filtered.length}`;

    // ── Determine game-stage layout from control codes ──
    const hasPortraitUp = r.portrait && r.portrait.startsWith('PortraitUp');
    const hasPortraitDown = r.portrait && r.portrait.startsWith('PortraitDown');
    const isMapName = r.tags && r.tags.includes('MapName');

    let textPos;
    if (isMapName) {
      textPos = 'mapname';
    } else if (r.window === 'upper') {
      textPos = 'upper';
    } else if (r.window === 'lower') {
      textPos = 'lower';
    } else if (hasPortraitUp) {
      textPos = 'upper';
    } else {
      textPos = 'lower';
    }

    $gameStage.className = 'game-stage';
    if (textPos === 'upper') $gameStage.classList.add('show-upper-text');
    if (textPos === 'lower') $gameStage.classList.add('show-lower-text');
    if (hasPortraitUp) $gameStage.classList.add('show-upper-portrait');
    if (hasPortraitDown) $gameStage.classList.add('show-lower-portrait');

    const $targetWin = textPos === 'upper' ? $textwinUp : $textwinDown;
    $targetWin.appendChild($gameText);
    $targetWin.appendChild($pageInd);

    $portraitUpLabel.textContent = hasPortraitUp ? r.portrait : 'Portrait';
    $portraitUpLabel.className = 'gs-label' + (hasPortraitUp ? ' has-name' : '');
    $portraitDownLabel.textContent = hasPortraitDown ? r.portrait : 'Portrait';
    $portraitDownLabel.className = 'gs-label' + (hasPortraitDown ? ' has-name' : '');

    $areaName.textContent = isMapName ? r.text.trim() : '';

    // Render game text display
    const renderSource = getRenderSource(r);
    const lang = $langMode.value;
    const useEnglish = renderSource.useEnglish;
    const pages = parsePages(renderSource.source, renderSource.isPlainText, renderSource.playerName);
    if (currentPage >= pages.length) currentPage = 0;

    renderPage(pages[currentPage] || []);
    renderPageIndicator(pages.length);

    // Side-by-side
    if (lang === 'both' && r.english) {
      $sideBySide.style.display = '';
      $englishText.textContent = r.english;
    } else {
      $sideBySide.style.display = 'none';
    }

    // Block metadata
    renderMetadata(r);
    renderValidation(r);

    // Raw text
    $rawText.textContent = r.raw;
  }

  /**
   * Parse tagged text into pages. Each page is an array of lines.
   * Each line is an array of {text, colorClass} segments.
   */
  function parsePages(raw, isPlainText, playerName) {
    if (isPlainText) {
      // English translation — plain text, split into one page
      const lines = raw.split('\n').map(line => [{ text: line, colorClass: 'c-default' }]);
      return [lines];
    }

    const pages = [];
    let currentPageLines = [];
    let currentLine = [];
    let currentColor = 'c-default';

    // Tokenize: split into text chunks and [tags]
    const tokenRegex = /(\[[^\]]+\])/;
    const tokens = raw.split(tokenRegex).filter(Boolean);

    for (const tok of tokens) {
      if (tok.startsWith('[') && tok.endsWith(']')) {
        const tag = tok.slice(1, -1);

        if (tag === 'LN') {
          currentPageLines.push(currentLine);
          currentLine = [];
        } else if (tag === 'Input') {
          currentPageLines.push(currentLine);
          currentLine = [];
          pages.push(currentPageLines);
          currentPageLines = [];
        } else if (tag.startsWith('Color')) {
          currentColor = COLOR_MAP[tag] || 'c-default';
        } else if (tag === 'PlayerName') {
          currentLine.push({ text: playerName, colorClass: currentColor });
        } else if (tag.startsWith('Spaces')) {
          const n = parseInt(tag.substring(6), 10) || 1;
          currentLine.push({ text: '\u3000'.repeat(n), colorClass: currentColor });
        } else if (tag === 'MapNameEnd' || tag.startsWith('MapName')) {
          // skip
        } else if (tag === 'Clear') {
          // Clear acts like a page break
          currentPageLines.push(currentLine);
          currentLine = [];
          pages.push(currentPageLines);
          currentPageLines = [];
        } else {
          // Show as inline annotation if toggled
          if (showTags) {
            currentLine.push({ text: `[${tag}]`, colorClass: 'ctrl-code', isCtrl: true });
          }
        }
      } else {
        // Regular text
        if (tok) {
          const parts = tok.split('\n');
          parts.forEach((part, idx) => {
            if (part) {
              currentLine.push({ text: part, colorClass: currentColor });
            }
            if (idx < parts.length - 1) {
              currentPageLines.push(currentLine);
              currentLine = [];
            }
          });
        }
      }
    }

    // Flush
    if (currentLine.length > 0) currentPageLines.push(currentLine);
    if (currentPageLines.length > 0) pages.push(currentPageLines);

    return pages.length > 0 ? pages : [[[{ text: '(empty)', colorClass: 'c-default' }]]];
  }

  function renderPage(lines) {
    $gameText.innerHTML = '';
    for (const line of lines) {
      const lineEl = document.createElement('div');
      for (const seg of line) {
        const span = document.createElement('span');
        span.className = seg.isCtrl ? 'ctrl-code' : seg.colorClass;
        span.textContent = seg.text;
        lineEl.appendChild(span);
      }
      if (line.length === 0) {
        lineEl.innerHTML = '&nbsp;';
      }
      $gameText.appendChild(lineEl);
    }

    // Add cursor prompt indicator
    const prompt = document.createElement('div');
    prompt.style.color = '#446';
    prompt.style.marginTop = '0.3rem';
    prompt.textContent = '▼';
    $gameText.appendChild(prompt);
  }

  function renderPageIndicator(totalPages) {
    if (totalPages <= 1) {
      $pageInd.innerHTML = '';
      return;
    }

    let html = `Page ${currentPage + 1} / ${totalPages} `;
    if (currentPage > 0) {
      html += `<button class="page-btn" data-delta="-1">◀</button>`;
    }
    if (currentPage < totalPages - 1) {
      html += `<button class="page-btn" data-delta="1">▶</button>`;
    }
    $pageInd.innerHTML = html;

    $pageInd.querySelectorAll('.page-btn').forEach(btn => {
      btn.addEventListener('click', () => changePage(parseInt(btn.dataset.delta, 10)));
    });
  }

  function changePage(delta) {
    if (filtered.length === 0) return;
    const r = filtered[currentIndex];
    const renderSource = getRenderSource(r);
    const pages = parsePages(renderSource.source, renderSource.isPlainText, renderSource.playerName);
    const newPage = currentPage + delta;
    if (newPage >= 0 && newPage < pages.length) {
      currentPage = newPage;
      renderPage(pages[currentPage]);
      renderPageIndicator(pages.length);
    }
  }

  function renderMetadata(r) {
    const pairs = [
      ['File', r.file],
      ['Category', r.path],
      ['Block', r.block],
      ['Portrait', r.portrait || '—'],
      ['Window', r.window || '—'],
      ['Translated', r.english ? 'Yes' : 'No'],
      ['Warnings', r.validation ? r.validation.issueCount : 0],
    ];

    $blockMeta.innerHTML = pairs.map(([k, v]) =>
      `<dt>${esc(k)}</dt><dd>${esc(String(v))}</dd>`
    ).join('');
  }

  function renderValidation(r) {
    const validation = r.validation || { issueCount: 0, issues: [] };
    const widthLimit = validation.widthLimit == null ? 'Special UI block' : `${validation.widthLimit} cells`;

    if (!r.english) {
      $validationSummary.textContent = `No English translation to validate yet. Width target: ${widthLimit}.`;
      $validationIssues.innerHTML = '';
      return;
    }

    $validationSummary.textContent =
      `Width target: ${widthLimit} · ` +
      `English pages: ${validation.pageCount || 0} / Japanese pages: ${validation.rawPageCount || 0} · ` +
      `Max line: ${validation.maxLineUnits || 0} cells`;

    if (!validation.issueCount) {
      $validationIssues.innerHTML = '<li class="validation-item ok">No validator warnings for this block.</li>';
      return;
    }

    $validationIssues.innerHTML = validation.issues.map(issue =>
      `<li class="validation-item ${esc(issue.severity || 'warning')}">` +
        `<span class="validation-severity">${esc((issue.severity || 'warning').toUpperCase())}</span>` +
        `<span>${esc(issue.message)}</span>` +
      `</li>`
    ).join('');
  }

  // ── Tabs ─────────────────────────────────────────

  function switchTab(tabId) {
    document.querySelectorAll('.tab-button').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tabId}`));

    // Show/hide script toolbar
    document.getElementById('scriptToolbar').style.display = tabId === 'script' ? '' : 'none';
  }

  // ── File map ─────────────────────────────────────

  function buildFileMap() {
    $fileMapGrid.innerHTML = '';

    // Group records by file
    const byFile = {};
    for (const r of allRecords) {
      if (!byFile[r.file]) byFile[r.file] = { path: r.path, total: 0, translated: 0, warnings: 0 };
      byFile[r.file].total++;
      if (r.english) byFile[r.file].translated++;
      if (r.validation) byFile[r.file].warnings += r.validation.issueCount;
    }

    for (const [file, info] of Object.entries(byFile).sort((a, b) => a[0].localeCompare(b[0]))) {
      const pct = info.total > 0 ? ((info.translated / info.total) * 100) : 0;
      const card = document.createElement('div');
      card.className = 'file-card';
      card.innerHTML =
        `<div class="file-card-name">${esc(file)}</div>` +
        `<div class="file-card-path">${esc(info.path)}</div>` +
        `<div class="file-card-stats">${info.total} blocks · ${info.translated} translated · ${info.warnings} warning${info.warnings === 1 ? '' : 's'}</div>` +
        `<div class="file-card-bar"><div class="file-card-bar-fill" style="width:${pct}%"></div></div>`;

      card.addEventListener('click', () => {
        $fileFilter.value = file;
        switchTab('script');
        applyFilters();
      });

      $fileMapGrid.appendChild(card);
    }
  }

  // ── Utilities ────────────────────────────────────

  function esc(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function getRenderSource(record) {
    const lang = $langMode.value;
    if (lang === 'english' && (record.englishRaw || record.english)) {
      return {
        useEnglish: true,
        source: record.englishRaw || record.english,
        isPlainText: !record.englishRaw,
        playerName: 'Stockman',
      };
    }

    return {
      useEnglish: false,
      source: record.raw,
      isPlainText: false,
      playerName: 'ストックマン',
    };
  }

  // ── Boot ─────────────────────────────────────────
  init();
})();
