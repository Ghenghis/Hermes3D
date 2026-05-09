/* Wonder Emporium M2 — Agent Team Identity & Orbital Rings
   Pure CSS class injection + GSAP for the orbit pulse.
   No external assets needed. */

(function () {
  "use strict";

  // Agent team identity cards
  const TEAM_A = { name: "MiniMax-M2.7", role: "Builders", color: "#f97316", glow: "rgba(249,115,22,0.35)" };
  const TEAM_B = { name: "DeepSeek-V4",  role: "Reviewers", color: "#06b6d4", glow: "rgba(6,182,212,0.35)" };

  function injectTeamIdentity() {
    const teamsSection = document.getElementById("hermes-teams");
    if (!teamsSection) return;

    const grid2 = teamsSection.querySelector(".grid--2");
    if (!grid2) return;

    const cards = grid2.querySelectorAll(".card");
    if (cards.length < 2) return;

    function styleTeamCard(card, team) {
      card.classList.add("agent-team-card");
      card.style.setProperty("--team-color", team.color);
      card.style.setProperty("--team-glow", team.glow);

      // Inject orbital avatar above the heading
      const h4 = card.querySelector("h4");
      if (!h4) return;

      const avatar = document.createElement("div");
      avatar.className = "agent-avatar";
      avatar.innerHTML = `
        <div class="agent-avatar__ring" style="border-color:${team.color}88;"></div>
        <div class="agent-avatar__ring agent-avatar__ring--2" style="border-color:${team.color}44;"></div>
        <div class="agent-avatar__core" style="background:${team.color}22; border-color:${team.color};">
          <span style="color:${team.color}; font-size:1.4rem; font-weight:800;">
            ${team.name.charAt(0)}
          </span>
        </div>
      `;
      h4.insertAdjacentElement("beforebegin", avatar);

      // Color the heading
      h4.style.color = team.color;
    }

    styleTeamCard(cards[0], TEAM_A);
    styleTeamCard(cards[1], TEAM_B);
  }

  function animateOrbits() {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    const rings = document.querySelectorAll(".agent-avatar__ring");

    if (typeof gsap !== "undefined") {
      rings.forEach((ring, i) => {
        gsap.to(ring, {
          rotation: i % 2 === 0 ? 360 : -360,
          duration: i % 2 === 0 ? 8 : 12,
          repeat: -1,
          ease: "none",
          transformOrigin: "50% 50%",
        });
      });
    } else {
      // CSS fallback — add animation class
      rings.forEach((ring, i) => {
        ring.style.animation = `orbitSpin${i % 2} ${i % 2 === 0 ? 8 : 12}s linear infinite`;
      });
    }
  }

  // Nav active section indicator
  function initNavIndicator() {
    const nav = document.querySelector(".nav__links");
    if (!nav) return;

    const indicator = document.createElement("div");
    indicator.className = "nav-active-indicator";
    nav.style.position = "relative";
    nav.appendChild(indicator);

    const sections = document.querySelectorAll("section[id]");
    const links = nav.querySelectorAll("a[href^='#']");

    if (!("IntersectionObserver" in window)) return;

    let activeId = "";
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            activeId = e.target.id;
            links.forEach(a => {
              const isActive = a.getAttribute("href") === `#${activeId}`;
              a.classList.toggle("nav-link--active", isActive);
            });
          }
        });
      },
      { threshold: 0.3, rootMargin: "-10% 0px -60% 0px" }
    );

    sections.forEach(s => io.observe(s));
  }

  // Gate checkmark draw animation
  function initGateCards() {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    const gateSection = document.getElementById("truth-gate");
    if (!gateSection) return;

    const cards = gateSection.querySelectorAll(".card");
    cards.forEach((card, i) => {
      // Add a checkmark badge
      const check = document.createElement("div");
      check.className = "gate-check";
      check.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none">
        <path class="gate-check__path" d="M5 12l5 5L19 7" stroke="#22c55e"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
          stroke-dasharray="30" stroke-dashoffset="30"/>
      </svg>`;
      card.insertAdjacentElement("afterbegin", check);
    });

    // Animate checkmarks on scroll
    const drawChecks = () => {
      cards.forEach((card, i) => {
        const path = card.querySelector(".gate-check__path");
        if (!path) return;
        if (typeof gsap !== "undefined") {
          gsap.to(path, {
            scrollTrigger: { trigger: card, start: "top 85%", once: true },
            strokeDashoffset: 0,
            duration: 0.5,
            delay: i * 0.08,
            ease: "power2.out",
          });
        } else {
          setTimeout(() => { path.style.strokeDashoffset = "0"; path.style.transition = "stroke-dashoffset 0.5s ease"; }, i * 80);
        }
      });
    };

    if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
      gsap.registerPlugin(ScrollTrigger);
      drawChecks();
    } else {
      window.addEventListener("load", drawChecks);
    }
  }

  function init() {
    injectTeamIdentity();
    initNavIndicator();
    initGateCards();
    if (typeof gsap !== "undefined") {
      animateOrbits();
    } else {
      window.addEventListener("load", animateOrbits);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
