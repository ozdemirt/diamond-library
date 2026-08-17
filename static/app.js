/**
 * Library Full-Text Search Engine - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // State Management
    const state = {
        query: '',
        scope: 'all',        // 'all', 'title', 'author', 'exact'
        format: '',          // '', 'PDF', 'EPUB'
        page: 1,
        limit: 15,
        totalResults: 0,
        activeTab: 'search', // 'search' or 'catalog'
        theme: localStorage.getItem('lib_theme') || 'dark',
        
        // Reader State
        reader: {
            bookId: null,
            title: '',
            author: '',
            format: 'PDF',
            pageNum: 1,
            totalPages: 1,
            theme: localStorage.getItem('reader_theme') || 'dark',
            fontSize: parseInt(localStorage.getItem('reader_fontsize') || '15', 10),
            highlightWord: ''
        },

        // Catalog State
        catalog: {
            page: 1,
            limit: 24,
            filter: ''
        }
    };

    // DOM Elements Cache
    const DOM = {
        // Theme
        themeToggle: document.getElementById('themeToggle'),
        themeIcon: document.getElementById('themeIcon'),
        
        // Tabs
        tabSearch: document.getElementById('tabSearch'),
        tabCatalog: document.getElementById('tabCatalog'),
        brandLogo: document.getElementById('brandLogo'),
        navBookCount: document.getElementById('navBookCount'),

        // Sections
        searchHeroSection: document.getElementById('searchHeroSection'),
        resultsSection: document.getElementById('resultsSection'),
        catalogSection: document.getElementById('catalogSection'),

        // Search Controls
        searchInput: document.getElementById('searchInput'),
        clearSearchBtn: document.getElementById('clearSearchBtn'),
        searchSubmitBtn: document.getElementById('searchSubmitBtn'),
        scopeGroup: document.getElementById('scopeGroup'),
        formatGroup: document.getElementById('formatGroup'),

        // Stats
        statBooks: document.getElementById('statBooks'),
        statPages: document.getElementById('statPages'),
        statWords: document.getElementById('statWords'),
        statSpeed: document.getElementById('statSpeed'),

        // Results
        resultsCount: document.getElementById('resultsCount'),
        resultsTime: document.getElementById('resultsTime'),
        btnBackToHero: document.getElementById('btnBackToHero'),
        loadingState: document.getElementById('loadingState'),
        emptyState: document.getElementById('emptyState'),
        resultsList: document.getElementById('resultsList'),
        paginationBar: document.getElementById('paginationBar'),
        pageInfo: document.getElementById('pageInfo'),
        prevPageBtn: document.getElementById('prevPageBtn'),
        nextPageBtn: document.getElementById('nextPageBtn'),

        // Catalog
        catalogGrid: document.getElementById('catalogGrid'),
        catalogFilterInput: document.getElementById('catalogFilterInput'),
        catPageInfo: document.getElementById('catPageInfo'),
        catPrevBtn: document.getElementById('catPrevBtn'),
        catNextBtn: document.getElementById('catNextBtn'),

        // Reader Modal
        readerModal: document.getElementById('readerModal'),
        readerFormatBadge: document.getElementById('readerFormatBadge'),
        readerBookTitle: document.getElementById('readerBookTitle'),
        readerBookAuthor: document.getElementById('readerBookAuthor'),
        readerBody: document.getElementById('readerBody'),
        readerContent: document.getElementById('readerContent'),
        closeReaderBtn: document.getElementById('closeReaderBtn'),
        readerPrevPageBtn: document.getElementById('readerPrevPageBtn'),
        readerNextPageBtn: document.getElementById('readerNextPageBtn'),
        readerPageInput: document.getElementById('readerPageInput'),
        readerTotalPages: document.getElementById('readerTotalPages'),
        readerJumpBtn: document.getElementById('readerJumpBtn'),
        readerCopyBtn: document.getElementById('readerCopyBtn'),
        fontDecBtn: document.getElementById('fontDecBtn'),
        fontIncBtn: document.getElementById('fontIncBtn')
    };

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    function init() {
        applyTheme(state.theme);
        applyReaderTheme(state.reader.theme);
        applyReaderFontSize(state.reader.fontSize);
        fetchStats();
        bindEvents();
    }

    // =========================================================================
    // THEME MANAGEMENT
    // =========================================================================

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        DOM.themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        localStorage.setItem('lib_theme', theme);
        state.theme = theme;
    }

    function toggleTheme() {
        const newTheme = state.theme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }

    function applyReaderTheme(theme) {
        DOM.readerBody.setAttribute('data-theme', theme);
        document.querySelectorAll('.reader-theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-reader-theme') === theme);
        });
        localStorage.setItem('reader_theme', theme);
        state.reader.theme = theme;
    }

    function applyReaderFontSize(size) {
        state.reader.fontSize = Math.max(12, Math.min(26, size));
        DOM.readerBody.style.fontSize = `${state.reader.fontSize}px`;
        localStorage.setItem('reader_fontsize', state.reader.fontSize);
    }

    // =========================================================================
    // STATS FETCHER
    // =========================================================================

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                const data = await res.json();
                if (data.total_books) {
                    DOM.statBooks.textContent = Number(data.total_books).toLocaleString('tr-TR');
                    DOM.navBookCount.textContent = Number(data.total_books).toLocaleString('tr-TR');
                }
                if (data.total_pages) {
                    DOM.statPages.textContent = Number(data.total_pages).toLocaleString('tr-TR');
                }
                if (data.total_words) {
                    const millions = (data.total_words / 1000000).toFixed(1);
                    DOM.statWords.textContent = `${millions} M`;
                }
            }
        } catch (e) {
            console.warn('Stats fetch error:', e);
        }
    }

    // =========================================================================
    // SEARCH EXECUTION
    // =========================================================================

    let searchDebounceTimer = null;

    async function performSearch(page = 1) {
        const rawQ = DOM.searchInput.value.trim();
        if (!rawQ) {
            resetToHero();
            return;
        }

        state.query = rawQ;
        state.page = page;

        // UI transitions
        DOM.searchHeroSection.style.display = 'block';
        DOM.resultsSection.style.display = 'block';
        DOM.catalogSection.style.display = 'none';
        DOM.loadingState.style.display = 'block';
        DOM.emptyState.style.display = 'none';
        DOM.resultsList.innerHTML = '';
        DOM.paginationBar.style.display = 'none';

        // Prepare query param
        let queryFormatted = state.query;
        if (state.scope === 'exact' && !queryFormatted.startsWith('"')) {
            queryFormatted = `"${queryFormatted}"`;
        }

        const params = new URLSearchParams({
            q: queryFormatted,
            scope: state.scope === 'exact' ? 'all' : state.scope,
            format: state.format,
            page: state.page,
            limit: state.limit
        });

        try {
            const res = await fetch(`/api/search?${params.toString()}`);
            const data = await res.json();
            DOM.loadingState.style.display = 'none';

            if (!res.ok || !data.results || data.results.length === 0) {
                DOM.emptyState.style.display = 'block';
                DOM.resultsCount.textContent = '0 sonuç bulundu';
                DOM.resultsTime.textContent = `⚡ ${data.time_ms || 0} ms`;
                return;
            }

            state.totalResults = data.total;
            renderResults(data);

        } catch (err) {
            DOM.loadingState.style.display = 'none';
            DOM.emptyState.style.display = 'block';
            console.error('Search error:', err);
        }
    }

    function renderResults(data) {
        DOM.resultsCount.textContent = `${Number(data.total).toLocaleString('tr-TR')} sonuç bulundu`;
        DOM.resultsTime.textContent = `⚡ ${data.time_ms} ms`;
        DOM.resultsList.innerHTML = '';

        data.results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'result-card';

            const formatClass = (item.file_type || '').toLowerCase() === 'epub' ? 'badge-epub' : 'badge-pdf';
            const pageBadgeText = item.page_num ? `📍 Sayfa ${item.page_num}` : '📍 Sayfa 1';

            card.innerHTML = `
                <div class="result-top">
                    <div class="result-title-group">
                        <div class="result-title">${escapeHTML(item.title)}</div>
                        <div class="result-author">✍️ ${escapeHTML(item.author || 'Bilinmiyor')}</div>
                    </div>
                    <div class="result-badges">
                        <span class="badge-format ${formatClass}">${escapeHTML(item.file_type || 'PDF')}</span>
                        <span class="badge-page">${pageBadgeText}</span>
                    </div>
                </div>
                <div class="result-snippet">${item.snippet || '...'}</div>
                <div class="result-actions">
                    <button class="btn-primary btn-sm read-page-btn" data-book-id="${item.book_id}" data-page="${item.page_num || 1}">
                        📖 ${item.page_num || 1}. Sayfayı Oku
                    </button>
                    <a href="/api/books/${item.book_id}/download" class="btn-secondary btn-sm" download title="Kitap Metnini İndir">
                        ⬇️ TXT İndir
                    </a>
                </div>
            `;

            DOM.resultsList.appendChild(card);
        });

        // Pagination
        const totalPages = Math.ceil(data.total / state.limit);
        if (totalPages > 1) {
            DOM.paginationBar.style.display = 'flex';
            DOM.pageInfo.textContent = `Sayfa ${state.page} / ${totalPages}`;
            DOM.prevPageBtn.disabled = state.page <= 1;
            DOM.nextPageBtn.disabled = state.page >= totalPages;
        } else {
            DOM.paginationBar.style.display = 'none';
        }

        // Attach Reader Button Event Listeners
        document.querySelectorAll('.read-page-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const bookId = parseInt(btn.getAttribute('data-book-id'), 10);
                const pageNum = parseInt(btn.getAttribute('data-page'), 10);
                openReader(bookId, pageNum, state.query);
            });
        });
    }

    function resetToHero() {
        DOM.resultsSection.style.display = 'none';
        DOM.emptyState.style.display = 'none';
        DOM.resultsList.innerHTML = '';
        DOM.clearSearchBtn.style.display = 'none';
    }

    // =========================================================================
    // IN-APP READER MODAL
    // =========================================================================

    async function openReader(bookId, pageNum = 1, highlightKeyword = '') {
        state.reader.bookId = bookId;
        state.reader.pageNum = pageNum;
        state.reader.highlightWord = highlightKeyword;

        DOM.readerModal.style.display = 'flex';
        DOM.readerContent.textContent = 'Sayfa yükleniyor...';
        DOM.readerPageInput.value = pageNum;

        await loadReaderPage(bookId, pageNum);
    }

    async function loadReaderPage(bookId, pageNum) {
        DOM.readerPrevPageBtn.disabled = true;
        DOM.readerNextPageBtn.disabled = true;

        try {
            const res = await fetch(`/api/books/${bookId}/page/${pageNum}`);
            if (!res.ok) {
                DOM.readerContent.innerHTML = `<p style="color: #f87171;">Sayfa yüklenirken hata oluştu.</p>`;
                return;
            }

            const data = await res.json();
            state.reader.title = data.title;
            state.reader.author = data.author;
            state.reader.format = data.file_type;
            state.reader.totalPages = data.total_pages || 1;

            DOM.readerBookTitle.textContent = data.title;
            DOM.readerBookAuthor.textContent = data.author ? `✍️ ${data.author}` : '';
            DOM.readerFormatBadge.textContent = data.file_type || 'PDF';
            DOM.readerTotalPages.textContent = state.reader.totalPages;
            DOM.readerPageInput.value = pageNum;
            DOM.readerPageInput.max = state.reader.totalPages;

            // Highlight keywords if query provided
            let pageText = data.content;
            if (state.reader.highlightWord) {
                pageText = highlightText(pageText, state.reader.highlightWord);
                DOM.readerContent.innerHTML = pageText;
            } else {
                DOM.readerContent.textContent = pageText;
            }

            DOM.readerPrevPageBtn.disabled = pageNum <= 1;
            DOM.readerNextPageBtn.disabled = pageNum >= state.reader.totalPages;

            // Scroll reader body to top
            DOM.readerBody.scrollTop = 0;

        } catch (e) {
            DOM.readerContent.textContent = `Hata: ${e.message}`;
        }
    }

    function closeReader() {
        DOM.readerModal.style.display = 'none';
    }

    function highlightText(text, keyword) {
        if (!keyword) return escapeHTML(text);
        const cleanKw = keyword.replace(/["*]/g, '').trim();
        if (!cleanKw) return escapeHTML(text);

        const words = cleanKw.split(/\s+/).filter(w => w.length > 1);
        if (words.length === 0) return escapeHTML(text);

        // Escape HTML first
        let safeText = escapeHTML(text);

        words.forEach(w => {
            const regex = new RegExp(`(${escapeRegExp(w)})`, 'gi');
            safeText = safeText.replace(regex, '<mark>$1</mark>');
        });

        return safeText;
    }

    // =========================================================================
    // CATALOG BROWSER
    // =========================================================================

    async function loadCatalog(page = 1) {
        state.catalog.page = page;
        DOM.catalogGrid.innerHTML = '<div class="spinner" style="grid-column: 1/-1;"></div>';

        const params = new URLSearchParams({
            page: state.catalog.page,
            limit: state.catalog.limit,
            q: state.catalog.filter
        });

        try {
            const res = await fetch(`/api/books?${params.toString()}`);
            const data = await res.json();
            renderCatalog(data);
        } catch (e) {
            DOM.catalogGrid.innerHTML = `<p style="grid-column: 1/-1; text-align: center;">Katalog yüklenemedi: ${e.message}</p>`;
        }
    }

    function renderCatalog(data) {
        DOM.catalogGrid.innerHTML = '';
        if (!data.books || data.books.length === 0) {
            DOM.catalogGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center;">Eşleşen kitap bulunamadı.</p>';
            return;
        }

        data.books.forEach(b => {
            const card = document.createElement('div');
            card.className = 'book-card';
            const formatClass = (b.file_type || '').toLowerCase() === 'epub' ? 'badge-epub' : 'badge-pdf';
            const wordsFormatted = b.total_words ? Number(b.total_words).toLocaleString('tr-TR') : '0';

            card.innerHTML = `
                <div class="book-card-top">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <span class="badge-format ${formatClass}">${b.file_type || 'PDF'}</span>
                        <span style="font-size: 11px; color: var(--text-dim);">📖 ${b.total_pages || 0} Sayfa</span>
                    </div>
                    <div class="book-card-title">${escapeHTML(b.title)}</div>
                    <div class="book-card-author">✍️ ${escapeHTML(b.author || 'Bilinmiyor')}</div>
                </div>
                <div class="book-card-meta">
                    <span>${wordsFormatted} Kelime</span>
                    <button class="btn-primary btn-sm read-catalog-btn" data-book-id="${b.id}">
                        📖 Oku
                    </button>
                </div>
            `;
            DOM.catalogGrid.appendChild(card);
        });

        const totalPages = Math.ceil(data.total / state.catalog.limit);
        DOM.catPageInfo.textContent = `Sayfa ${state.catalog.page} / ${totalPages}`;
        DOM.catPrevBtn.disabled = state.catalog.page <= 1;
        DOM.catNextBtn.disabled = state.catalog.page >= totalPages;

        document.querySelectorAll('.read-catalog-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const bId = parseInt(btn.getAttribute('data-book-id'), 10);
                openReader(bId, 1, '');
            });
        });
    }

    // =========================================================================
    // EVENT BINDINGS
    // =========================================================================

    function bindEvents() {
        // Theme Switcher
        DOM.themeToggle.addEventListener('click', toggleTheme);

        // Tab Switchers
        DOM.tabSearch.addEventListener('click', () => switchTab('search'));
        DOM.tabCatalog.addEventListener('click', () => switchTab('catalog'));
        DOM.brandLogo.addEventListener('click', () => switchTab('search'));

        // Search Input Events
        DOM.searchInput.addEventListener('input', () => {
            const hasVal = DOM.searchInput.value.trim().length > 0;
            DOM.clearSearchBtn.style.display = hasVal ? 'block' : 'none';

            clearTimeout(searchDebounceTimer);
            if (hasVal) {
                searchDebounceTimer = setTimeout(() => performSearch(1), 350);
            } else {
                resetToHero();
            }
        });

        DOM.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(searchDebounceTimer);
                performSearch(1);
            }
        });

        DOM.searchSubmitBtn.addEventListener('click', () => performSearch(1));

        DOM.clearSearchBtn.addEventListener('click', () => {
            DOM.searchInput.value = '';
            DOM.searchInput.focus();
            resetToHero();
        });

        DOM.btnBackToHero.addEventListener('click', () => {
            DOM.searchInput.value = '';
            DOM.searchInput.focus();
            resetToHero();
        });

        // Scope Switchers
        DOM.scopeGroup.querySelectorAll('.scope-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.scopeGroup.querySelectorAll('.scope-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.scope = btn.getAttribute('data-scope');
                if (DOM.searchInput.value.trim()) {
                    performSearch(1);
                }
            });
        });

        // Format Filter Buttons
        DOM.formatGroup.querySelectorAll('.format-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.formatGroup.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.format = btn.getAttribute('data-format');
                if (DOM.searchInput.value.trim()) {
                    performSearch(1);
                }
            });
        });

        // Search Pagination
        DOM.prevPageBtn.addEventListener('click', () => {
            if (state.page > 1) {
                performSearch(state.page - 1);
                window.scrollTo({ top: DOM.resultsSection.offsetTop - 80, behavior: 'smooth' });
            }
        });

        DOM.nextPageBtn.addEventListener('click', () => {
            performSearch(state.page + 1);
            window.scrollTo({ top: DOM.resultsSection.offsetTop - 80, behavior: 'smooth' });
        });

        // Catalog Filter & Pagination
        let catFilterTimer = null;
        DOM.catalogFilterInput.addEventListener('input', () => {
            clearTimeout(catFilterTimer);
            catFilterTimer = setTimeout(() => {
                state.catalog.filter = DOM.catalogFilterInput.value.trim();
                loadCatalog(1);
            }, 300);
        });

        DOM.catPrevBtn.addEventListener('click', () => {
            if (state.catalog.page > 1) loadCatalog(state.catalog.page - 1);
        });

        DOM.catNextBtn.addEventListener('click', () => {
            loadCatalog(state.catalog.page + 1);
        });

        // Reader Modal Controls
        DOM.closeReaderBtn.addEventListener('click', closeReader);
        DOM.readerModal.addEventListener('click', (e) => {
            if (e.target === DOM.readerModal) closeReader();
        });

        document.querySelectorAll('.reader-theme-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                applyReaderTheme(btn.getAttribute('data-reader-theme'));
            });
        });

        DOM.fontDecBtn.addEventListener('click', () => applyReaderFontSize(state.reader.fontSize - 1));
        DOM.fontIncBtn.addEventListener('click', () => applyReaderFontSize(state.reader.fontSize + 1));

        DOM.readerPrevPageBtn.addEventListener('click', () => {
            if (state.reader.pageNum > 1) {
                loadReaderPage(state.reader.bookId, state.reader.pageNum - 1);
            }
        });

        DOM.readerNextPageBtn.addEventListener('click', () => {
            if (state.reader.pageNum < state.reader.totalPages) {
                loadReaderPage(state.reader.bookId, state.reader.pageNum + 1);
            }
        });

        DOM.readerJumpBtn.addEventListener('click', () => {
            const targetP = parseInt(DOM.readerPageInput.value, 10);
            if (targetP >= 1 && targetP <= state.reader.totalPages) {
                loadReaderPage(state.reader.bookId, targetP);
            }
        });

        DOM.readerPageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const targetP = parseInt(DOM.readerPageInput.value, 10);
                if (targetP >= 1 && targetP <= state.reader.totalPages) {
                    loadReaderPage(state.reader.bookId, targetP);
                }
            }
        });

        DOM.readerCopyBtn.addEventListener('click', () => {
            const textToCopy = DOM.readerContent.innerText || DOM.readerContent.textContent;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const orig = DOM.readerCopyBtn.textContent;
                DOM.readerCopyBtn.textContent = '✓ Kopyalandı!';
                setTimeout(() => { DOM.readerCopyBtn.textContent = orig; }, 1800);
            });
        });

        // Global Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            // Escape to close reader
            if (e.key === 'Escape' && DOM.readerModal.style.display === 'flex') {
                closeReader();
            }
            // Arrow keys in reader
            if (DOM.readerModal.style.display === 'flex') {
                if (e.key === 'ArrowLeft' && state.reader.pageNum > 1) {
                    loadReaderPage(state.reader.bookId, state.reader.pageNum - 1);
                } else if (e.key === 'ArrowRight' && state.reader.pageNum < state.reader.totalPages) {
                    loadReaderPage(state.reader.bookId, state.reader.pageNum + 1);
                }
            }
            // Ctrl + K or / to focus search
            if ((e.ctrlKey && e.key.toLowerCase() === 'k') || (e.key === '/' && document.activeElement !== DOM.searchInput && document.activeElement !== DOM.catalogFilterInput && DOM.readerModal.style.display !== 'flex')) {
                e.preventDefault();
                switchTab('search');
                DOM.searchInput.focus();
                DOM.searchInput.select();
            }
        });
    }

    function switchTab(tab) {
        state.activeTab = tab;
        DOM.tabSearch.classList.toggle('active', tab === 'search');
        DOM.tabCatalog.classList.toggle('active', tab === 'catalog');

        if (tab === 'search') {
            DOM.searchHeroSection.style.display = 'block';
            DOM.catalogSection.style.display = 'none';
            if (DOM.searchInput.value.trim() && state.totalResults > 0) {
                DOM.resultsSection.style.display = 'block';
            }
        } else {
            DOM.searchHeroSection.style.display = 'none';
            DOM.resultsSection.style.display = 'none';
            DOM.catalogSection.style.display = 'block';
            loadCatalog(1);
        }
    }

    // =========================================================================
    // HELPER FUNCTIONS
    // =========================================================================

    function escapeHTML(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Run
    init();
});
