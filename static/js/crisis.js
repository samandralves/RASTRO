/* ==========================================================================
   RASTRO — Widget de Apoio em Crise
   Painel flutuante com orientações para pânico, ansiedade, crise
   situacional e TEPT, respiração guiada e contatos de emergência.
   ========================================================================== */
(function () {
  "use strict";

  const toggle = document.getElementById("crisis-toggle");
  const panel = document.getElementById("crisis-panel");
  const closeBtn = document.getElementById("crisis-close");
  const tabs = document.querySelectorAll(".crisis-tab");
  const sections = document.querySelectorAll(".crisis-section");

  if (!toggle || !panel) return;

  function openPanel() {
    panel.classList.add("open");
    toggle.setAttribute("aria-expanded", "true");
    const firstFocusable = panel.querySelector("button, a");
    if (firstFocusable) firstFocusable.focus();
  }

  function closePanel() {
    panel.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
    stopBreathing();
  }

  toggle.addEventListener("click", function () {
    panel.classList.contains("open") ? closePanel() : openPanel();
  });

  if (closeBtn) closeBtn.addEventListener("click", closePanel);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("open")) closePanel();
  });

  document.addEventListener("click", function (e) {
    if (
      panel.classList.contains("open") &&
      !panel.contains(e.target) &&
      !toggle.contains(e.target)
    ) {
      closePanel();
    }
  });

  /* ---------- Abas ---------- */
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      const target = tab.getAttribute("data-tab");

      tabs.forEach(function (t) {
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
      });

      sections.forEach(function (s) {
        s.classList.toggle("active", s.id === "crisis-tab-" + target);
      });

      if (target !== "panico") stopBreathing();
    });
  });

  /* ---------- Respiração guiada (4-4-6) ---------- */
  const breatheEl = document.getElementById("crisis-breathe");
  const breatheLabel = document.getElementById("crisis-breathe-label");
  const breatheBtn = document.getElementById("crisis-breathe-btn");

  let breathingTimer = null;
  let breathingActive = false;

  const cycle = [
    { phase: "inhale", duration: 4000, text: "Inspire pelo nariz…" },
    { phase: "hold", duration: 4000, text: "Segure…" },
    { phase: "exhale", duration: 6000, text: "Solte o ar devagar…" }
  ];
  let cycleIndex = 0;

  function runCycleStep() {
    if (!breathingActive) return;
    const step = cycle[cycleIndex];

    breatheEl.classList.remove("inhale", "hold", "exhale");
    breatheEl.classList.add(step.phase);
    if (breatheLabel) breatheLabel.textContent = step.text;

    breathingTimer = setTimeout(function () {
      cycleIndex = (cycleIndex + 1) % cycle.length;
      runCycleStep();
    }, step.duration);
  }

  function startBreathing() {
    breathingActive = true;
    cycleIndex = 0;
    if (breatheBtn) breatheBtn.textContent = "Parar";
    runCycleStep();
  }

  function stopBreathing() {
    breathingActive = false;
    clearTimeout(breathingTimer);
    if (breatheEl) breatheEl.classList.remove("inhale", "hold", "exhale");
    if (breatheLabel) breatheLabel.textContent = "Toque em começar quando estiver pronto(a).";
    if (breatheBtn) breatheBtn.textContent = "Começar";
  }

  if (breatheBtn) {
    breatheBtn.addEventListener("click", function () {
      breathingActive ? stopBreathing() : startBreathing();
    });
  }
})();
