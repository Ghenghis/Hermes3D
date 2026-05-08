/* Wonder Emporium — Hero Particle Constellation
   Pure Canvas 2D, zero dependencies, prefers-reduced-motion safe.
   Wrap with initParticles(canvasId) from app.js. */

(function () {
  "use strict";

  function initParticles(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const isMobile = window.innerWidth < 768;
    const COUNT = isMobile ? 50 : 140;
    const LINK_DIST = isMobile ? 80 : 120;
    const REPEL_DIST = 80;
    const COLORS = ["#a855f7", "#06b6d4", "#ec4899", "#f59e0b"];

    let W, H, dpr, particles, mouse = { x: -9999, y: -9999 };

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.offsetWidth;
      H = canvas.offsetHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.scale(dpr, dpr);
    }

    function rand(min, max) { return Math.random() * (max - min) + min; }

    function mkParticle() {
      return {
        x: rand(0, W),
        y: rand(0, H),
        vx: rand(-0.25, 0.25),
        vy: rand(-0.25, 0.25),
        r: rand(1, 2.5),
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        alpha: rand(0.4, 0.9),
      };
    }

    function init() {
      resize();
      particles = Array.from({ length: COUNT }, mkParticle);
    }

    let lastT = 0;
    function frame(t) {
      const dt = Math.min(t - lastT, 50);
      lastT = t;

      ctx.clearRect(0, 0, W, H);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Mouse repulsion
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < REPEL_DIST * REPEL_DIST && d2 > 0.01) {
          const d = Math.sqrt(d2);
          const force = (REPEL_DIST - d) / REPEL_DIST * 0.06;
          p.vx += (dx / d) * force;
          p.vy += (dy / d) * force;
        }

        // Speed cap + damping
        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        if (speed > 1.2) { p.vx *= 0.95; p.vy *= 0.95; }
        p.vx *= 0.998;
        p.vy *= 0.998;

        p.x += p.vx * dt * 0.06;
        p.y += p.vy * dt * 0.06;

        // Wrap edges
        if (p.x < 0) p.x += W;
        if (p.x > W) p.x -= W;
        if (p.y < 0) p.y += H;
        if (p.y > H) p.y -= H;

        // Draw dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Links
        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j];
          const lx = p.x - q.x, ly = p.y - q.y;
          const ld = Math.sqrt(lx * lx + ly * ly);
          if (ld < LINK_DIST) {
            const linkAlpha = (1 - ld / LINK_DIST) * 0.18;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = "#a855f7";
            ctx.globalAlpha = linkAlpha;
            ctx.lineWidth = 0.7;
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
        }
      }

      requestAnimationFrame(frame);
    }

    function staticFrame() {
      // Prefers-reduced-motion: single static render
      ctx.clearRect(0, 0, W, H);
      particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha * 0.5;
        ctx.fill();
        ctx.globalAlpha = 1;
      });
    }

    init();
    window.addEventListener("resize", () => { resize(); });

    canvas.addEventListener("mousemove", e => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    });
    canvas.addEventListener("mouseleave", () => { mouse.x = -9999; mouse.y = -9999; });

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      staticFrame();
    } else {
      requestAnimationFrame(frame);
    }
  }

  window.WonderParticles = { init: initParticles };
})();
