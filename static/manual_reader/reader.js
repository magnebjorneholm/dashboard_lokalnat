/* Regumetrica manual reader — framework-agnostic behavior.
 *
 * Streamlit-free on purpose. The host (components.html today) only hands this file
 * one JSON blob — { markdown } — via a <script type="application/json"> tag, plus
 * the third-party libs (markdown-it, markdown-it-anchor, markdown-it-texmath, KaTeX)
 * already loaded on the page. Everything below is plain web: a React/Next.js port
 * reuses the same markdown-it config and the same slugify/scroll-spy logic (the
 * spy loop becomes a useScrollSpy hook; buildToc walks the same rendered article).
 *
 * Contract (stable across the port):
 *   - input:  markdown string (optionally with YAML-ish frontmatter)
 *   - slugs:  github-style, produced by slugify() — shared so deep links stay stable
 *   - DOM:    .reader > (.reader-toc, .reader-content > .reader-article)
 */
(function () {
    "use strict";

    // --- Stable slug function (must match between host and a future React port,
    // or in-document anchors / deep links break). GitHub-flavoured: lowercase,
    // drop punctuation, spaces -> hyphens. "3.1 The cost base" -> "31-the-cost-base".
    function slugify(s) {
        return String(s)
            .trim()
            .toLowerCase()
            .replace(/[^\w\s-]/g, "")
            .replace(/\s+/g, "-")
            .replace(/-+/g, "-");
    }

    // --- Minimal frontmatter parser (a leading --- ... --- block of key: value).
    // Not full YAML on purpose: the content store only needs flat string fields.
    function parseFrontmatter(src) {
        const meta = {};
        let body = src;
        const m = /^﻿?---\s*\n([\s\S]*?)\n---\s*\n?/.exec(src);
        if (m) {
            body = src.slice(m[0].length);
            for (const line of m[1].split("\n")) {
                const kv = /^([A-Za-z0-9_]+)\s*:\s*(.*)$/.exec(line.trim());
                if (kv) meta[kv[1]] = kv[2].replace(/^["']|["']$/g, "").trim();
            }
        }
        return { meta, body };
    }

    function buildMarkdownIt() {
        const md = window.markdownit({ html: true, linkify: true, typographer: false });
        if (window.markdownItAnchor) {
            md.use(window.markdownItAnchor, {
                level: [2, 3, 4],
                slugify: slugify,
                permalink: false,
            });
        }
        if (window.texmath && window.katex) {
            md.use(window.texmath, {
                engine: window.katex,
                delimiters: "dollars",
                katexOptions: { throwOnError: false },
            });
        }
        return md;
    }

    function renderHeader(meta) {
        if (!meta.title && !meta.subtitle) return "";
        const parts = ['<header class="reader-head">'];
        if (meta.title) parts.push(`<h1>${escapeHtml(meta.title)}</h1>`);
        if (meta.subtitle) parts.push(`<div class="reader-subtitle">${escapeHtml(meta.subtitle)}</div>`);
        const meta_bits = [];
        if (meta.status) meta_bits.push(`<span class="reader-badge">${escapeHtml(meta.status)}</span>`);
        if (meta.version) meta_bits.push(`<span>Version ${escapeHtml(meta.version)}</span>`);
        if (meta.date) meta_bits.push(`<span>${escapeHtml(meta.date)}</span>`);
        if (meta.url) {
            const label = meta.url.replace(/^https?:\/\//, "");
            meta_bits.push(`<a href="${escapeAttr(meta.url)}" target="_top">${escapeHtml(label)}</a>`);
        }
        if (meta_bits.length) parts.push(`<div class="reader-meta">${meta_bits.join("")}</div>`);
        parts.push("</header>");
        return parts.join("");
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    }
    function escapeAttr(s) { return escapeHtml(s).replace(/'/g, "&#39;"); }

    // --- Build the TOC from the rendered article's headings (h2-h4 carry ids
    // from markdown-it-anchor). DOM-driven so the TOC can never drift from the body.
    function buildToc(article, tocEl) {
        const headings = article.querySelectorAll("h2[id], h3[id], h4[id]");
        if (!headings.length) { tocEl.style.display = "none"; return []; }
        const ul = document.createElement("ul");
        const links = [];
        headings.forEach(h => {
            const level = Number(h.tagName.substring(1)); // 2 | 3 | 4
            const a = document.createElement("a");
            a.href = "#" + h.id;
            a.textContent = h.textContent;
            a.className = "lvl-" + level; // matches .lvl-2/.lvl-3/.lvl-4 in reader.css
            a.dataset.target = h.id;
            ul.appendChild(li(a));
            links.push({ a, h });
        });
        tocEl.appendChild(ul);
        return links;
    }
    function li(child) { const el = document.createElement("li"); el.appendChild(child); return el; }

    // --- Scroll-spy: mark the heading nearest the top of the content pane as
    // active. A scroll loop (rAF-throttled) is more reliable than IntersectionObserver
    // for "current section" and ports directly to a useScrollSpy hook.
    function wireScrollSpy(pane, links) {
        if (!links.length) return;
        let ticking = false;
        const ACTIVATION_OFFSET = 90; // px below the pane top counts as "current"

        function update() {
            ticking = false;
            const paneTop = pane.getBoundingClientRect().top;
            let activeIdx = 0;
            for (let i = 0; i < links.length; i++) {
                const top = links[i].h.getBoundingClientRect().top - paneTop;
                if (top <= ACTIVATION_OFFSET) activeIdx = i;
                else break;
            }
            // At the very bottom, force the last heading active (short tail sections).
            if (pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 4) {
                activeIdx = links.length - 1;
            }
            links.forEach((l, i) => l.a.classList.toggle("active", i === activeIdx));
        }
        function onScroll() {
            if (!ticking) { ticking = true; requestAnimationFrame(update); }
        }
        pane.addEventListener("scroll", onScroll, { passive: true });
        window.addEventListener("resize", onScroll, { passive: true });
        update();
    }

    // --- Click a TOC entry -> smooth-scroll the content pane to that heading.
    function wireTocClicks(tocEl, article) {
        tocEl.addEventListener("click", e => {
            const a = e.target.closest("a[data-target]");
            if (!a) return;
            e.preventDefault();
            const h = article.querySelector("#" + cssEscape(a.dataset.target));
            if (h) h.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }
    function cssEscape(id) {
        return window.CSS && CSS.escape ? CSS.escape(id) : id.replace(/([^\w-])/g, "\\$1");
    }

    // --- Make absolute links open in the top window (escape the iframe), keep
    // in-document anchors local.
    function fixExternalLinks(article) {
        article.querySelectorAll('a[href^="http"]').forEach(a => { a.target = "_top"; });
    }

    // --- Section mode: a single sliced section has no sibling headings in the DOM,
    // so in-document anchors (e.g. "see 3.4") would dangle. Strip their href so they
    // render as plain text instead of dead links. (.reader-anchor-inert styles them.)
    function neutralizeInternalAnchors(article) {
        article.querySelectorAll('a[href^="#"]').forEach(a => {
            a.classList.add("reader-anchor-inert");
            a.removeAttribute("href");
        });
    }

    function init() {
        const dataEl = document.getElementById("manual-data");
        if (!dataEl) return;
        const { markdown, mode } = JSON.parse(dataEl.textContent);
        const { meta, body } = parseFrontmatter(markdown || "");

        const md = buildMarkdownIt();
        const content = document.querySelector(".reader-content");
        const article = document.querySelector(".reader-article");

        article.innerHTML = renderHeader(meta) + md.render(body);
        fixExternalLinks(article);

        // Section mode renders one sliced section in a single column: no TOC pane,
        // no scroll-spy, internal cross-references neutralised.
        if (mode === "section") {
            neutralizeInternalAnchors(article);
            return;
        }

        const tocEl = document.querySelector(".reader-toc-list");
        const links = buildToc(article, tocEl);
        wireTocClicks(tocEl.parentElement, article);
        wireScrollSpy(content, links);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
