/* Wonder Emporium M2 — Pipeline Stage Sequential Animation
   Requires GSAP + ScrollTrigger (loaded before this via CDN defer).
   Falls back gracefully if GSAP is absent. */

(function () {
  "use strict";

  const STAGE_COLORS = {
    INIT:      "#06b6d4",
    VISION:    "#a855f7",
    GENERATE:  "#f59e0b",
    REPAIR:    "#f97316",
    GATE:      "#22c55e",
    SLICE:     "#ec4899",
    PRINT:     "#3b82f6",
    REPORT:    "#6366f1",
    DONE:      "#22c55e",
  };

  const STAGES = [
    { id: "INIT",     label: "01 INIT",     desc: "Intent received · session opened" },
    { id: "VISION",   label: "02 VISION",   desc: "Image analysed · model selected" },
    { id: "GENERATE", label: "03 GENERATE", desc: "RTX 3090 Ti · mesh materialises" },
    { id: "REPAIR",   label: "04 REPAIR",   desc: "Auto-repair loop · up to N passes" },
    { id: "GATE",     label: "05 GATE",     desc: "6 truth checks · signed verdict" },
    { id: "SLICE",    label: "06 SLICE",    desc: "OrcaSlicer · GCode emitted" },
    { id: "PRINT",    label: "07 PRINT",    desc: "Build plate clear · print starts" },
    { id: "REPORT",   label: "08 REPORT",   desc: "Evidence bundle written" },
    { id: "DONE",     label: "09 DONE",     desc: "Proof signed · PR open" },
  ];

  function buildTracker() {
    const pipeline = document.getElementById("pipeline");
    if (!pipeline) return null;

    const wrap = document.createElement("div");
    wrap.className = "stage-tracker";
    wrap.setAttribute("aria-label", "9-stage pipeline tracker");

    STAGES.forEach((s, i) => {
      const node = document.createElement("div");
      node.className = "stage-node";
      node.dataset.stage = s.id;
      node.innerHTML = `
        <div class="stage-node__dot" style="--stage-color:${STAGE_COLORS[s.id]}"></div>
        <div class="stage-node__label">${s.label}</div>
        <div class="stage-node__desc">${s.desc}</div>
      `;
      wrap.appendChild(node);

      if (i < STAGES.length - 1) {
        const line = document.createElement("div");
        line.className = "stage-line";
        wrap.appendChild(line);
      }
    });

    const diagramEl = pipeline.querySelector(".diagram");
    if (diagramEl) {
      pipeline.querySelector(".container").insertBefore(wrap, diagramEl);
    } else {
      const head = pipeline.querySelector(".section__head");
      head && head.insertAdjacentElement("afterend", wrap);
    }
    return wrap;
  }

  function animateStages(wrap) {
    const nodes = wrap.querySelectorAll(".stage-node");
    const lines = wrap.querySelectorAll(".stage-line");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion || typeof gsap === "undefined") {
      nodes.forEach(n => n.classList.add("stage-node--lit"));
      lines.forEach(l => l.classList.add("stage-line--lit"));
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: wrap,
        start: "top 75%",
        once: true,
      }
    });

    nodes.forEach((node, i) => {
      tl.to(node, {
        duration: 0,
        onComplete: () => node.classList.add("stage-node--lit"),
      }, i * 0.22);

      if (lines[i]) {
        tl.to(lines[i], {
          duration: 0.18,
          onStart: () => lines[i].classList.add("stage-line--lit"),
        }, i * 0.22 + 0.12);
      }
    });
  }

  function init() {
    const wrap = buildTracker();
    if (!wrap) return;

    // Wait for GSAP to be available (it's deferred)
    if (typeof gsap !== "undefined") {
      animateStages(wrap);
    } else {
      window.addEventListener("load", () => animateStages(wrap));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
