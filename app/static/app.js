/**
 * OTrace Frontend Single Page Web Application Engine
 * Pure Vanilla JavaScript (No Frameworks, No NPM)
 */

document.addEventListener('DOMContentLoaded', () => {
    // State Variables
    let currentResults = [];
    let currentParsedQuery = null;
    let currentExposureData = null;
    let activePlatformFilter = 'ALL';
    let parseDebounceTimer = null;

    // DOM Elements
    const heroSection = document.getElementById('hero-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const heroSearchForm = document.getElementById('hero-search-form');
    const heroSearchInput = document.getElementById('hero-search-input');
    const topSearchWrapper = document.getElementById('top-search-wrapper');
    const topSearchForm = document.getElementById('top-search-form');
    const topSearchInput = document.getElementById('top-search-input');
    const consentCheck = document.getElementById('consent-check');
    const consentMsgInline = document.getElementById('consent-msg-inline');
    const liveChips = document.getElementById('live-chips');
    const themeToggle = document.getElementById('theme-toggle');
    const warningBanner = document.getElementById('warning-banner');
    const warningText = document.getElementById('warning-text');
    const resultsCountBadge = document.getElementById('results-count-badge');
    const resultsParsedChips = document.getElementById('results-parsed-chips');
    const skeletonContainer = document.getElementById('skeleton-container');
    const gridLikely = document.getElementById('grid-likely');
    const gridOther = document.getElementById('grid-other');
    const emptyResultsCard = document.getElementById('empty-results-card');
    const filterPillsBar = document.getElementById('filter-pills-bar');
    const btnExportPdf = document.getElementById('btn-export-pdf');
    const btnDeleteData = document.getElementById('btn-delete-data');
    const btnClearHistory = document.getElementById('btn-clear-history');
    const historyList = document.getElementById('history-list');

    // Theme Management
    const savedTheme = localStorage.getItem('otrace_theme') || 'auto';
    document.documentElement.setAttribute('data-theme', savedTheme);

    themeToggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('otrace_theme', next);
    });

    // Helper: HTML Escaping to prevent XSS
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Debounced Live Parse Listener
    heroSearchInput.addEventListener('input', () => {
        clearTimeout(parseDebounceTimer);
        const queryVal = heroSearchInput.value.trim();
        if (!queryVal) {
            liveChips.innerHTML = '<span class="chip-placeholder">Type to see live parsing...</span>';
            return;
        }

        parseDebounceTimer = setTimeout(async () => {
            try {
                const res = await fetch('/parse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: queryVal })
                });
                if (res.ok) {
                    const data = await res.json();
                    renderLiveChips(data);
                }
            } catch (err) {
                console.error('Parse error:', err);
            }
        }, 300);
    });

    function renderLiveChips(parsed) {
        let html = '';
        if (parsed.name) {
            html += `<span class="chip-item">Name: <strong>${escapeHtml(parsed.name)}</strong></span>`;
        }
        if (parsed.college) {
            html += `<span class="chip-item">College: <strong>${escapeHtml(parsed.college)}</strong></span>`;
        }
        if (parsed.keywords && parsed.keywords.length > 0) {
            parsed.keywords.forEach(kw => {
                html += `<span class="chip-item">Keyword: <strong>${escapeHtml(kw)}</strong></span>`;
            });
        }
        liveChips.innerHTML = html || '<span class="chip-placeholder">Type to see live parsing...</span>';
    }

    // Example Chips Handler
    document.querySelectorAll('.chip-example').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            heroSearchInput.value = query;
            consentCheck.checked = true;
            consentMsgInline.style.display = 'none';
            heroSearchInput.dispatchEvent(new Event('input'));
            executeSearch(query);
        });
    });

    // Search Form Submit Handling
    heroSearchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = heroSearchInput.value.trim();
        if (!consentCheck.checked) {
            consentMsgInline.style.display = 'block';
            return;
        }
        consentMsgInline.style.display = 'none';
        executeSearch(query);
    });

    topSearchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = topSearchInput.value.trim();
        executeSearch(query);
    });

    // Main Search Execution
    async function executeSearch(rawQuery) {
        if (!rawQuery) return;

        // Show Skeleton & Dashboard
        heroSection.style.padding = '20px 24px 10px';
        topSearchWrapper.style.display = 'block';
        topSearchInput.value = rawQuery;
        dashboardSection.style.display = 'block';
        skeletonContainer.style.display = 'grid';
        gridLikely.innerHTML = '';
        gridOther.innerHTML = '';
        emptyResultsCard.style.display = 'none';

        // Scroll to dashboard
        dashboardSection.scrollIntoView({ behavior: 'smooth' });

        try {
            const res = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ q: rawQuery, consent: true })
            });

            const data = await res.json();
            skeletonContainer.style.display = 'none';

            if (!res.ok) {
                alert(`Search Error: ${data.detail || 'Failed to perform search'}`);
                return;
            }

            // Save to LocalStorage History
            saveSearchHistory(rawQuery);

            // Handle Warnings
            if (data.warnings && data.warnings.length > 0) {
                warningText.textContent = data.warnings[0];
                warningBanner.style.display = 'flex';
            } else {
                warningBanner.style.display = 'none';
            }

            currentResults = data.results || [];
            currentParsedQuery = data.parsed;
            currentExposureData = data.exposure;

            resultsCountBadge.textContent = currentResults.length;
            document.getElementById('method-tag').textContent = data.method + (data.llm_used ? ' + LLM Judge' : '');

            // Render Parsed Summary Chips
            renderLiveChipsSummary(currentParsedQuery);

            // Render Platform Filter Pills
            renderFilterPills(currentResults);

            // Render Cards
            renderCandidateCards(currentResults);

            // Render Exposure Tab
            renderExposureReport(currentExposureData);

            // Render Connection Graph SVG
            renderConnectionGraph(currentParsedQuery, currentResults);

        } catch (err) {
            skeletonContainer.style.display = 'none';
            alert(`Error communicating with backend server: ${err.message}`);
        }
    }

    function renderLiveChipsSummary(parsed) {
        let html = '';
        if (parsed.name) html += `<span class="chip-item">Name: <strong>${escapeHtml(parsed.name)}</strong></span>`;
        if (parsed.college) html += `<span class="chip-item">College: <strong>${escapeHtml(parsed.college)}</strong></span>`;
        if (parsed.keywords) {
            parsed.keywords.forEach(kw => {
                html += `<span class="chip-item">Keyword: <strong>${escapeHtml(kw)}</strong></span>`;
            });
        }
        resultsParsedChips.innerHTML = html;
    }

    function renderFilterPills(results) {
        const counts = { ALL: results.length };
        results.forEach(r => {
            const p = r.platform || 'Web';
            counts[p] = (counts[p] || 0) + 1;
        });

        let html = `<button class="pill-btn ${activePlatformFilter === 'ALL' ? 'active' : ''}" data-platform="ALL">All (${counts.ALL})</button>`;
        Object.keys(counts).forEach(p => {
            if (p !== 'ALL') {
                html += `<button class="pill-btn ${activePlatformFilter === p ? 'active' : ''}" data-platform="${escapeHtml(p)}">${escapeHtml(p)} (${counts[p]})</button>`;
            }
        });
        filterPillsBar.innerHTML = html;

        filterPillsBar.querySelectorAll('.pill-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                filterPillsBar.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activePlatformFilter = btn.getAttribute('data-platform');
                renderCandidateCards(currentResults);
            });
        });
    }

    function renderCandidateCards(results) {
        gridLikely.innerHTML = '';
        gridOther.innerHTML = '';

        const filtered = activePlatformFilter === 'ALL' 
            ? results 
            : results.filter(r => r.platform === activePlatformFilter);

        if (filtered.length === 0) {
            emptyResultsCard.style.display = 'block';
            return;
        }
        emptyResultsCard.style.display = 'none';

        const likelyList = filtered.filter(r => r.confidence_score >= 50);
        const otherList = filtered.filter(r => r.confidence_score < 50);

        likelyList.forEach(cand => gridLikely.appendChild(createCardElement(cand)));
        otherList.forEach(cand => gridOther.appendChild(createCardElement(cand)));

        document.getElementById('group-likely').style.display = likelyList.length > 0 ? 'block' : 'none';
        document.getElementById('group-other').style.display = otherList.length > 0 ? 'block' : 'none';
    }

    function createCardElement(cand) {
        const div = document.createElement('div');
        div.className = 'candidate-card';

        const band = cand.band || 'weak';
        const score = cand.confidence_score;

        div.innerHTML = `
            <div class="card-header">
                <span class="platform-badge">
                    ${escapeHtml(cand.platform)}
                </span>
                <div class="score-badge-large">
                    <span class="score-num band-${band}">${score}%</span>
                    <div class="band-label">${band}</div>
                </div>
            </div>

            <div class="card-body">
                <h3>${escapeHtml(cand.display_name)}</h3>
                <a href="${escapeHtml(cand.url)}" target="_blank" rel="noopener noreferrer" class="card-url">${escapeHtml(cand.url)}</a>
                <p class="card-snippet">${escapeHtml(cand.snippet || 'No summary available.')}</p>

                <div class="progress-bar-wrapper">
                    <div class="progress-fill band-${band}" style="width: ${score}%;"></div>
                    <div class="tick-mark tick-50"></div>
                    <div class="tick-mark tick-80"></div>
                </div>
            </div>

            <div class="card-footer">
                <button class="btn-expander">Why this score? &#9660;</button>
                <div class="feedback-buttons">
                    <button class="btn-fb btn-them">This is them</button>
                    <button class="btn-fb btn-not">Not them</button>
                </div>
            </div>

            <div class="evidence-drawer">
                <strong>Score Evidence Breakdown:</strong>
                <ul>
                    ${(cand.evidence?.supporting || []).map(s => `<li class="sup">${escapeHtml(s)}</li>`).join('')}
                    ${(cand.evidence?.contradicting || []).map(c => `<li class="con">${escapeHtml(c)}</li>`).join('')}
                    ${(cand.evidence?.missing || []).map(m => `<li class="mis">${escapeHtml(m)}</li>`).join('')}
                </ul>
            </div>
        `;

        // Expander Drawer Toggle
        const expanderBtn = div.querySelector('.btn-expander');
        const drawer = div.querySelector('.evidence-drawer');
        expanderBtn.addEventListener('click', () => {
            const isOpened = drawer.classList.toggle('open');
            expanderBtn.innerHTML = isOpened ? 'Hide breakdown &#9650;' : 'Why this score? &#9660;';
        });

        // Feedback Buttons
        const btnThem = div.querySelector('.btn-them');
        const btnNot = div.querySelector('.btn-not');

        btnThem.addEventListener('click', () => sendFeedback(cand, true, btnThem, btnNot));
        btnNot.addEventListener('click', () => sendFeedback(cand, false, btnNot, btnThem));

        return div;
    }

    async function sendFeedback(cand, isSame, activeBtn, otherBtn) {
        try {
            const res = await fetch('/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_name: currentParsedQuery.name,
                    candidate_url: cand.url,
                    candidate_platform: cand.platform,
                    is_same_person: isSame,
                    features: cand.features
                })
            });
            if (res.ok) {
                activeBtn.classList.add(isSame ? 'active-them' : 'active-not');
                otherBtn.classList.remove('active-them', 'active-not');
            }
        } catch (e) {
            console.error('Feedback submission failed:', e);
        }
    }

    // Render Exposure Report
    function renderExposureReport(exp) {
        if (!exp) return;
        document.getElementById('gauge-score-num').textContent = exp.exposure_score;
        document.getElementById('radial-gauge').style.borderColor = 
            exp.exposure_score >= 75 ? 'var(--accent-color)' : (exp.exposure_score >= 45 ? 'var(--plausible-amber)' : 'var(--strong-green)');

        const riskTag = document.getElementById('risk-tag');
        riskTag.textContent = exp.risk_level;
        riskTag.className = `risk-tag band-${exp.risk_level.toLowerCase()}`;

        // Attacker Insights
        const insightsList = document.getElementById('insights-list');
        insightsList.innerHTML = exp.attacker_insights.map(i => `<li>${escapeHtml(i)}</li>`).join('');

        // Recommendations
        const recsList = document.getElementById('recs-list');
        recsList.innerHTML = exp.recommendations.map(r => `
            <div class="rec-item">
                <h4>[${escapeHtml(r.platform)}] ${escapeHtml(r.title)}</h4>
                <p>${escapeHtml(r.action)}</p>
            </div>
        `).join('');
    }

    // Render Connection Graph SVG
    function renderConnectionGraph(parsed, results) {
        const svg = document.getElementById('connection-svg');
        svg.innerHTML = '';
        if (!parsed || results.length === 0) return;

        const width = 800;
        const height = 500;
        const centerX = width / 2;
        const centerY = height / 2;

        // Group SVG elements
        let svgHtml = '';

        // Center Person Node
        svgHtml += `<circle cx="${centerX}" cy="${centerY}" r="32" fill="var(--accent-color)" />`;
        svgHtml += `<text x="${centerX}" y="${centerY + 5}" text-anchor="middle" fill="#FFF" font-family="var(--font-heading)" font-weight="700" font-size="12">${escapeHtml(parsed.name.split(' ')[0])}</text>`;

        const topCands = results.slice(0, 10);
        const radius = 180;
        const angleStep = (2 * Math.PI) / topCands.length;

        topCands.forEach((cand, i) => {
            const angle = i * angleStep;
            const cx = centerX + radius * Math.cos(angle);
            const cy = centerY + radius * Math.sin(angle);

            const bandColor = cand.confidence_score >= 80 ? 'var(--strong-green)' : (cand.confidence_score >= 50 ? 'var(--plausible-amber)' : 'var(--weak-grey)');

            // Edge Line
            svgHtml += `<line x1="${centerX}" y1="${centerY}" x2="${cx}" y2="${cy}" stroke="${bandColor}" stroke-width="2" stroke-opacity="0.6" />`;

            // Candidate Node
            svgHtml += `<circle cx="${cx}" cy="${cy}" r="22" fill="var(--bg-surface)" stroke="${bandColor}" stroke-width="3" />`;
            svgHtml += `<text x="${cx}" y="${cy + 4}" text-anchor="middle" fill="var(--text-primary)" font-family="var(--font-mono)" font-size="10" font-weight="600">${cand.confidence_score}%</text>`;
            svgHtml += `<text x="${cx}" y="${cy + 34}" text-anchor="middle" fill="var(--text-secondary)" font-family="var(--font-body)" font-size="11">${escapeHtml(cand.platform)}</text>`;
        });

        svg.innerHTML = svgHtml;
    }

    // Navigation Tabs Router
    const tabs = document.querySelectorAll('.dashboard-tabs .tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const targetId = tab.getAttribute('href').replace('#', 'content-');
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.style.display = 'block';

            if (targetId === 'content-history') renderHistoryTab();
        });
    });

    // LocalStorage History
    function saveSearchHistory(query) {
        let history = JSON.parse(localStorage.getItem('otrace_history') || '[]');
        history = history.filter(h => h.query.toLowerCase() !== query.toLowerCase());
        history.unshift({ query, timestamp: new Date().toISOString() });
        localStorage.setItem('otrace_history', JSON.stringify(history.slice(0, 20)));
    }

    function renderHistoryTab() {
        const history = JSON.parse(localStorage.getItem('otrace_history') || '[]');
        if (history.length === 0) {
            historyList.innerHTML = '<li class="history-item">No recent searches saved.</li>';
            return;
        }

        historyList.innerHTML = history.map(item => `
            <li class="history-item" style="display:flex; justify-content:space-between; padding:12px; border-bottom:1px solid var(--border-color);">
                <div>
                    <strong>${escapeHtml(item.query)}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${new Date(item.timestamp).toLocaleString()}</div>
                </div>
                <button class="btn-secondary-sm btn-rerun" data-query="${escapeHtml(item.query)}">Re-run Search</button>
            </li>
        `).join('');

        historyList.querySelectorAll('.btn-rerun').forEach(btn => {
            btn.addEventListener('click', () => {
                const q = btn.getAttribute('data-query');
                heroSearchInput.value = q;
                consentCheck.checked = true;
                executeSearch(q);
            });
        });
    }

    btnClearHistory.addEventListener('click', () => {
        localStorage.removeItem('otrace_history');
        renderHistoryTab();
    });

    // Delete Data Endpoint Call
    btnDeleteData.addEventListener('click', async () => {
        if (confirm('Are you sure you want to delete all cached profiles, audit logs, and labels?')) {
            try {
                await fetch('/data', { method: 'DELETE' });
                localStorage.removeItem('otrace_history');
                alert('All user data cleared successfully.');
                location.reload();
            } catch (e) {
                alert('Error clearing data.');
            }
        }
    });

    // Export PDF Report
    btnExportPdf.addEventListener('click', () => {
        window.print();
    });
});
