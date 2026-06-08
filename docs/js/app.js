/**
 * UAE-France Economic Monitor — Dashboard Application
 */

(function () {
    "use strict";

    // --- State ---
    let currentDigest = null;
    let filteredArticles = [];
    let activeSector = "all";
    let activeSource = "all";
    let searchQuery = "";
    let showStarredOnly = false;
    let starredIds = new Set();

    // Load starred from localStorage (survives within a session)
    try {
        const saved = localStorage.getItem("uae-monitor-starred");
        if (saved) starredIds = new Set(JSON.parse(saved));
    } catch (e) { /* ignore */ }

    // --- DOM refs ---
    const $articlesContainer = document.getElementById("articles-container");
    const $digestTime = document.getElementById("digest-time");
    const $totalArticles = document.getElementById("total-articles");
    const $totalSources = document.getElementById("total-sources");
    const $searchInput = document.getElementById("search-input");
    const $sourceFilter = document.getElementById("source-filter");
    const $digestSelect = document.getElementById("digest-select");
    const $sectorTabs = document.getElementById("sector-tabs");
    const $btnStarred = document.getElementById("btn-starred");
    const $starredCount = document.getElementById("starred-count");
    const $btnExport = document.getElementById("btn-export");

    // --- Data loading ---

    // Build base URL for data files — works on GitHub Pages and locally
    const BASE_URL = (function () {
        const loc = window.location;
        // GitHub Pages: https://user.github.io/repo-name/
        // The data files are at /repo-name/data/
        const base = loc.pathname.replace(/\/+$/, "") + "/";
        return base;
    })();

    async function fetchJson(url) {
        console.log("[Monitor] Fetching:", url);
        const resp = await fetch(url, { cache: "no-cache" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
        return resp.json();
    }

    async function loadDigestIndex() {
        try {
            const index = await fetchJson(BASE_URL + "data/index.json");
            const select = $digestSelect;
            select.innerHTML = "";

            if (index.digests && index.digests.length > 0) {
                index.digests.forEach((d, i) => {
                    const opt = document.createElement("option");
                    opt.value = d.filename;
                    const dateStr = d.date.replace("_", " at ").replace(
                        /(\d{4})(\d{2})(\d{2}) at (\d{2})(\d{2})/,
                        "$1-$2-$3 $4:$5"
                    );
                    opt.textContent = i === 0 ? `Latest (${dateStr})` : dateStr;
                    select.appendChild(opt);
                });
            } else {
                const opt = document.createElement("option");
                opt.value = "latest";
                opt.textContent = "Latest digest";
                select.appendChild(opt);
            }
        } catch (e) {
            console.warn("[Monitor] Index load failed:", e);
        }
    }

    async function loadDigest(filename) {
        showLoading();
        try {
            let url;
            if (!filename || filename === "latest") {
                url = BASE_URL + "data/latest.json";
            } else {
                url = BASE_URL + "data/digests/" + filename;
            }
            currentDigest = await fetchJson(url);
            console.log("[Monitor] Loaded digest:", currentDigest.total_articles, "articles");
            updateHeader();
            updateSectorCounts();
            applyFilters();
        } catch (e) {
            console.error("[Monitor] Digest load failed:", e);
            showError("Unable to load digest (" + e.message + "). Check browser console for details.");
        }
    }

    // --- Rendering ---

    function showLoading() {
        $articlesContainer.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading digest...</p>
            </div>`;
    }

    function showError(msg) {
        $articlesContainer.innerHTML = `
            <div class="no-results">
                <h3>No data available</h3>
                <p>${msg}</p>
            </div>`;
    }

    function updateHeader() {
        if (!currentDigest) return;
        $digestTime.textContent = currentDigest.generated_at_cet + " CET";
        $totalArticles.textContent = currentDigest.total_articles;
        $totalSources.textContent = currentDigest.sources_fetched;
    }

    function updateSectorCounts() {
        if (!currentDigest) return;

        const articles = currentDigest.articles || [];
        document.getElementById("count-all").textContent = articles.length;

        const sectors = ["energy", "ai_tech", "climate", "food_security",
            "logistics", "aeronautics", "space", "fintech", "health"];

        sectors.forEach(s => {
            const count = articles.filter(a =>
                a.sectors && a.sectors.some(sec => sec.id === s)
            ).length;
            const el = document.getElementById("count-" + s);
            if (el) el.textContent = count;
        });
    }

    function applyFilters() {
        if (!currentDigest || !currentDigest.articles) {
            filteredArticles = [];
            renderArticles();
            return;
        }

        let articles = [...currentDigest.articles];

        // Sector filter
        if (activeSector !== "all") {
            articles = articles.filter(a =>
                a.sectors && a.sectors.some(s => s.id === activeSector)
            );
        }

        // Source category filter
        if (activeSource !== "all") {
            articles = articles.filter(a => a.category === activeSource);
        }

        // Search filter
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            articles = articles.filter(a =>
                (a.title && a.title.toLowerCase().includes(q)) ||
                (a.summary && a.summary.toLowerCase().includes(q)) ||
                (a.source && a.source.toLowerCase().includes(q))
            );
        }

        // Starred filter
        if (showStarredOnly) {
            articles = articles.filter(a => starredIds.has(a.id));
        }

        filteredArticles = articles;
        renderArticles();
    }

    function renderArticles() {
        if (filteredArticles.length === 0) {
            $articlesContainer.innerHTML = `
                <div class="no-results">
                    <h3>No articles found</h3>
                    <p>Try adjusting your filters or search query.</p>
                </div>`;
            return;
        }

        const html = filteredArticles.map(article => {
            const isStarred = starredIds.has(article.id);
            const relevanceClass = article.relevance_score >= 8 ? "high"
                : article.relevance_score >= 4 ? "medium" : "";
            const cardClass = article.relevance_score >= 8 ? "high-relevance"
                : article.bilateral_score >= 4 ? "bilateral" : "";

            const sectorTags = (article.sectors || []).map(s =>
                `<span class="sector-tag ${s.id}">${s.label}</span>`
            ).join("");

            const dateStr = formatDate(article.published);

            return `
            <article class="article-card ${cardClass}" data-id="${article.id}">
                <div class="article-main">
                    <div class="article-meta">
                        <span class="source-badge ${article.category}">${article.category}</span>
                        <span class="source-name">${escapeHtml(article.source)}</span>
                        <span class="lang-badge">${article.source_lang}</span>
                        <span class="article-date">${dateStr}</span>
                    </div>
                    <h3 class="article-title">
                        <a href="${escapeHtml(article.link)}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a>
                    </h3>
                    ${article.summary ? `<p class="article-summary">${escapeHtml(article.summary)}</p>` : ""}
                    <div class="article-sectors">${sectorTags}</div>
                </div>
                <div class="article-actions">
                    <div class="relevance-score ${relevanceClass}" title="Relevance score">
                        ${article.relevance_score}
                    </div>
                    <button class="star-btn ${isStarred ? 'starred' : ''}" data-id="${article.id}" title="Star article">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="${isStarred ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                    </button>
                </div>
            </article>`;
        }).join("");

        $articlesContainer.innerHTML = html;

        // Attach star button handlers
        $articlesContainer.querySelectorAll(".star-btn").forEach(btn => {
            btn.addEventListener("click", () => toggleStar(btn.dataset.id));
        });
    }

    function formatDate(dateStr) {
        if (!dateStr) return "";
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            const now = new Date();
            const diffMs = now - d;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

            if (diffHours < 1) return "Just now";
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffHours < 48) return "Yesterday";
            return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
        } catch (e) {
            return dateStr;
        }
    }

    function escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Interactions ---

    function toggleStar(articleId) {
        if (starredIds.has(articleId)) {
            starredIds.delete(articleId);
        } else {
            starredIds.add(articleId);
        }
        try {
            localStorage.setItem("uae-monitor-starred", JSON.stringify([...starredIds]));
        } catch (e) { /* ignore */ }
        updateStarredCount();
        // Re-render to update star state (or just toggle the button)
        const btn = $articlesContainer.querySelector(`.star-btn[data-id="${articleId}"]`);
        if (btn) {
            const isStarred = starredIds.has(articleId);
            btn.classList.toggle("starred", isStarred);
            btn.querySelector("svg").setAttribute("fill", isStarred ? "currentColor" : "none");
        }
    }

    function updateStarredCount() {
        $starredCount.textContent = starredIds.size;
    }

    function exportCSV() {
        if (!filteredArticles.length) return;

        const headers = ["Title", "Source", "Category", "Language", "Sectors", "Relevance", "Published", "Link"];
        const rows = filteredArticles.map(a => [
            `"${(a.title || "").replace(/"/g, '""')}"`,
            `"${a.source}"`,
            a.category,
            a.source_lang,
            `"${(a.sectors || []).map(s => s.label).join(", ")}"`,
            a.relevance_score,
            a.published,
            a.link
        ]);

        const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
        const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `uae-monitor-export-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // --- Event listeners ---

    $searchInput.addEventListener("input", debounce(() => {
        searchQuery = $searchInput.value.trim();
        applyFilters();
    }, 300));

    $sourceFilter.addEventListener("change", () => {
        activeSource = $sourceFilter.value;
        applyFilters();
    });

    $digestSelect.addEventListener("change", () => {
        const val = $digestSelect.value;
        loadDigest(val);
    });

    $sectorTabs.addEventListener("click", (e) => {
        const tab = e.target.closest(".sector-tab");
        if (!tab) return;
        $sectorTabs.querySelectorAll(".sector-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeSector = tab.dataset.sector;
        applyFilters();
    });

    $btnStarred.addEventListener("click", () => {
        showStarredOnly = !showStarredOnly;
        $btnStarred.classList.toggle("active", showStarredOnly);
        applyFilters();
    });

    $btnExport.addEventListener("click", exportCSV);

    function debounce(fn, ms) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    }

    // --- Init ---

    async function init() {
        updateStarredCount();
        await loadDigestIndex();
        await loadDigest("latest");
    }

    init();
})();
