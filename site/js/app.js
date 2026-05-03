/* ==========================================================================
   Hermes3D-OS · marketing site · client-side enhancements
   No build step. No external libs. Vanilla JS, GitHub-Pages-ready.
   Honors prefers-reduced-motion throughout.
   ========================================================================== */

(function () {
  "use strict";

  const reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- 1. Scroll-reveal via IntersectionObserver ----------
  function setupReveal() {
    const els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window) || reduceMotion) {
      els.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => io.observe(el));
  }

  // ---------- 2. Stat counters (count-up on first viewport entry) ----------
  function setupCounters() {
    const counters = document.querySelectorAll("[data-count-to]");
    if (!counters.length) return;
    if (reduceMotion) {
      counters.forEach((c) => (c.textContent = c.getAttribute("data-count-to")));
      return;
    }
    const animate = (el) => {
      const target = parseInt(el.getAttribute("data-count-to"), 10) || 0;
      const dur = 1200;
      const t0 = performance.now();
      function frame(t) {
        const p = Math.min(1, (t - t0) / dur);
        // ease-out-cubic
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = String(Math.round(target * eased));
        if (p < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    };
    if (!("IntersectionObserver" in window)) {
      counters.forEach(animate);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            animate(e.target);
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.6 }
    );
    counters.forEach((c) => io.observe(c));
  }

  // ---------- 3. Terminal typewriter (CLI demo) ----------
  function setupTerminal() {
    const term = document.getElementById("terminal-body");
    if (!term) return;

    const lines = [
      { c: "c-cmd", t: "$ python -m hermes3d.cli probe --workspace ." },
      { c: "c-dim", t: "" },
      { c: "c-purple", t: "┌─ probing fleet ..." },
      { c: "c-dim",    t: "│  scanning 192.168.0.0/24 for moonraker · mainsail · fluidd · octoprint" },
      { c: "c-ok",     t: "└─ [PASS] 6 printers reachable" },
      { c: "c-dim",    t: "" },
      { c: "c-cmd",    t: "$ hermes3d truth-gate ./mymesh.stl" },
      { c: "c-purple", t: "┌─ truth_gate_validator" },
      { c: "c-dim",    t: "│  manifold_closure  · wall_thickness  · overhang_ratio" },
      { c: "c-dim",    t: "│  support_estimate  · bridge_spans    · first_layer_area" },
      { c: "c-ok",     t: "└─ [PASS] 6 / 6 checks · proof envelope written" },
      { c: "c-dim",    t: "" },
      { c: "c-cmd",    t: "$ hermes3d dispatch --strategy=auto --material=PLA --quality=normal" },
      { c: "c-pink",   t: "┌─ dispatcher" },
      { c: "c-dim",    t: "│  candidate scoring: bed × material × load × quality" },
      { c: "c-dim",    t: "│  prusa-mk4-02 → 0.94 · voron-2.4-03 → 0.71 · bambu-x1c-05 → 0.68" },
      { c: "c-ok",     t: "└─ [SELECTED] prusa-mk4-02 · lock acquired · queued" },
      { c: "c-dim",    t: "" },
      { c: "c-cmd",    t: "$ hermes3d proof verify ./var/proofs/dispatch/2026-05-02T*.json" },
      { c: "c-ok",     t: "[PASS] HMAC-SHA256 verified · mesh hash matches · 6/6 gates passed" },
      { c: "c-dim",    t: "" },
      { c: "c-ok",     t: "Pass: 17  Fail: 0   Warn: 0   Skip: 0   Duration: 8.4s" },
    ];

    if (reduceMotion) {
      // render the entire transcript instantly
      term.innerHTML = lines
        .map((l) => `<span class="${l.c}">${escapeHtml(l.t)}</span>\n`)
        .join("");
      return;
    }

    let line = 0;
    let ch = 0;
    let curEl = null;
    let curLineEl = null;

    const cursor = document.createElement("span");
    cursor.className = "cursor";

    function type() {
      if (line >= lines.length) {
        // restart loop after a beat
        setTimeout(() => {
          term.textContent = "";
          line = 0;
          ch = 0;
          curEl = null;
          curLineEl = null;
          type();
        }, 4000);
        return;
      }
      const lineSpec = lines[line];

      if (!curLineEl) {
        curLineEl = document.createElement("div");
        curEl = document.createElement("span");
        curEl.className = lineSpec.c;
        curLineEl.appendChild(curEl);
        term.appendChild(curLineEl);
        // place cursor at end
        if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
        curLineEl.appendChild(cursor);
      }

      if (lineSpec.t.length === 0) {
        // empty line — move on
        if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
        line += 1;
        ch = 0;
        curLineEl = null;
        setTimeout(type, 40);
        return;
      }

      if (ch < lineSpec.t.length) {
        const c = lineSpec.t.charAt(ch);
        curEl.appendChild(document.createTextNode(c));
        ch += 1;
        const variableDelay =
          c === " " ? 8 : (lineSpec.c === "c-ok" || lineSpec.c === "c-pink" ? 14 : 8);
        const jitter = Math.random() * 16;
        setTimeout(type, variableDelay + jitter);
      } else {
        if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
        line += 1;
        ch = 0;
        curLineEl = null;
        const pause =
          lineSpec.c === "c-cmd" ? 220 : lineSpec.c === "c-ok" ? 380 : 80;
        setTimeout(type, pause);
      }
    }

    function escapeHtml(s) {
      return s.replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
    }

    // Start typing only when terminal scrolls into view
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              io.disconnect();
              type();
            }
          });
        },
        { threshold: 0.35 }
      );
      io.observe(term);
    } else {
      type();
    }
  }

  // ---------- 4. Screenshot lazy-swap (use real PNG when present) ----------
  function setupShotSwap() {
    const slots = document.querySelectorAll("[data-src]");
    if (!slots.length) return;
    slots.forEach((slot) => {
      const src = slot.getAttribute("data-src");
      if (!src) return;
      // Probe with a HEAD request; on success swap the placeholder for a real image
      fetch(src, { method: "HEAD", cache: "no-cache" })
        .then((r) => {
          if (r.ok) {
            const alt = slot.getAttribute("data-alt") || "Hermes3D screenshot";
            const img = new Image();
            img.src = src;
            img.alt = alt;
            img.loading = "lazy";
            img.decoding = "async";
            slot.replaceChildren(img);
          }
        })
        .catch(() => { /* placeholder remains */ });
    });
  }

  // ---------- 5. GitHub Releases auto-fetch ----------
  function setupReleases() {
    const root = document.getElementById("releases-list");
    if (!root) return;
    fetch("https://api.github.com/repos/Ghenghis/Hermes3D/releases?per_page=3", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("rate-limited"))))
      .then((releases) => {
        if (!Array.isArray(releases) || releases.length === 0) {
          root.innerHTML =
            '<p class="sub">No releases yet — first signed binary is on the way.</p>';
          return;
        }
        const rows = releases
          .slice(0, 3)
          .map((rel) => {
            const assets = (rel.assets || [])
              .map((a) => {
                const sizeMB = (a.size / (1024 * 1024)).toFixed(1);
                return `<tr>
                  <td><code>${escapeHtml(a.name)}</code></td>
                  <td>${sizeMB} MB</td>
                  <td><a href="${escapeHtml(a.browser_download_url)}">download</a></td>
                </tr>`;
              })
              .join("");
            const date = new Date(rel.published_at).toISOString().slice(0, 10);
            return `
              <h3 style="margin-top:2rem;">${escapeHtml(rel.name || rel.tag_name)} <span class="sub" style="font-weight:400; margin-left:0.5rem;">${date}</span></h3>
              <table class="table">
                <thead><tr><th>Asset</th><th>Size</th><th></th></tr></thead>
                <tbody>${assets || '<tr><td colspan="3" class="sub">Source-only release</td></tr>'}</tbody>
              </table>
              <p style="margin-top:0.5rem;"><a href="${escapeHtml(rel.html_url)}">View release notes →</a></p>
            `;
          })
          .join("");
        root.innerHTML = rows;
      })
      .catch(() => {
        root.innerHTML =
          '<p class="sub">Couldn\'t reach the GitHub API right now — see <a href="https://github.com/Ghenghis/Hermes3D/releases">releases on GitHub</a>.</p>';
      });

    function escapeHtml(s) {
      return String(s).replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
    }
  }

  // ---------- boot ----------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  function boot() {
    setupReveal();
    setupCounters();
    setupTerminal();
    setupShotSwap();
    setupReleases();
  }
})();
