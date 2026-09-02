/* ==========================================================================
   RASTRO — Widget de Acessibilidade (100% gratuito, sem dependências pagas)
   - Ler em voz alta (Web Speech API — funciona como "TalkBack" no site)
   - Fonte OpenDyslexic
   - VLibras (widget oficial do Governo Federal, gratuito)
   - Sublinhar links, cursor ampliado, escala de cinza, espaçamento de texto
   - Preferências salvas no localStorage
   ========================================================================== */
(function () {
  "use strict";

  const STORAGE_KEY = "rastro_a11y_prefs";
  const html = document.documentElement;

  const defaults = {
    dyslexic: "off",
    underline: "off",
    cursor: "off",
    grayscale: "off",
    spacing: "off",
    vlibras: "off"
  };

  function loadPrefs() {
    try {
      return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
    } catch (e) {
      return { ...defaults };
    }
  }

  function savePrefs(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (e) {}
  }

  let prefs = loadPrefs();

  function applyPrefs() {
    html.setAttribute("data-a11y-dyslexic", prefs.dyslexic);
    html.setAttribute("data-a11y-underline", prefs.underline);
    html.setAttribute("data-a11y-cursor", prefs.cursor);
    html.setAttribute("data-a11y-grayscale", prefs.grayscale);
    html.setAttribute("data-a11y-spacing", prefs.spacing);
    html.setAttribute("data-a11y-vlibras", prefs.vlibras);
    syncSwitches();
    if (prefs.vlibras === "on") loadVLibras(); else removeVLibras();
  }

  function syncSwitches() {
    document.querySelectorAll("[data-a11y-switch]").forEach((btn) => {
      const key = btn.getAttribute("data-a11y-switch");
      const isOn = prefs[key] === "on";
      btn.setAttribute("aria-pressed", String(isOn));
    });
  }

  /* ---------------- Painel abrir/fechar ---------------- */
  function initPanelToggle() {
    const toggle = document.getElementById("a11y-toggle");
    const panel = document.getElementById("a11y-panel");
    if (!toggle || !panel) return;

    toggle.addEventListener("click", () => {
      const isOpen = panel.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) {
        const firstFocusable = panel.querySelector("button, [tabindex]");
        if (firstFocusable) firstFocusable.focus();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && panel.classList.contains("open")) {
        panel.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });

    document.addEventListener("click", (e) => {
      if (!panel.contains(e.target) && !toggle.contains(e.target) && panel.classList.contains("open")) {
        panel.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---------------- Switches genéricos (dyslexic, etc) ------- */
  function initSwitches() {
    document.querySelectorAll("[data-a11y-switch]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-a11y-switch");
        prefs[key] = prefs[key] === "on" ? "off" : "on";
        savePrefs(prefs);
        applyPrefs();
      });
    });
  }

  /* ---------------- Reset ---------------- */
  function initReset() {
    const btn = document.getElementById("a11y-reset");
    if (!btn) return;
    btn.addEventListener("click", () => {
      prefs = { ...defaults };
      savePrefs(prefs);
      applyPrefs();
      stopSpeech();
    });
  }

  /* ---------------- Ler em voz alta (Web Speech API) ---------------- */
  let utterance = null;

  function getReadableText() {
    const main = document.querySelector("main.content, main.landing-main") || document.body;
    return main.innerText.trim();
  }

  function speak() {
    if (!("speechSynthesis" in window)) {
      alert("Seu navegador não suporta leitura em voz alta.");
      return;
    }
    stopSpeech();
    const text = getReadableText();
    if (!text) return;
    utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "pt-BR";
    utterance.rate = 1;
    const btn = document.getElementById("a11y-speak");
    if (btn) btn.setAttribute("aria-pressed", "true");
    utterance.onend = () => { if (btn) btn.setAttribute("aria-pressed", "false"); };
    window.speechSynthesis.speak(utterance);
  }

  function stopSpeech() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    const btn = document.getElementById("a11y-speak");
    if (btn) btn.setAttribute("aria-pressed", "false");
  }

  function initSpeech() {
    const speakBtn = document.getElementById("a11y-speak");
    const stopBtn = document.getElementById("a11y-speak-stop");
    if (speakBtn) speakBtn.addEventListener("click", speak);
    if (stopBtn) stopBtn.addEventListener("click", stopSpeech);
  }

  /* ---------------- VLibras (widget oficial, gratuito) ------------------
     https://www.gov.br/governodigital/pt-br/vlibras
  ------------------------------------------------------------------------- */
  function loadVLibras() {
    ensureVLibrasWrapper();
    if (document.getElementById("vlibras-script")) {
      if (window.VLibras) initVLibrasWidget();
      return;
    }
    const script = document.createElement("script");
    script.id = "vlibras-script";
    script.src = "https://vlibras.gov.br/app/vlibras-plugin.js";
    script.onload = initVLibrasWidget;
    document.body.appendChild(script);
  }

  function ensureVLibrasWrapper() {
    if (document.getElementById("vlibras-wrapper")) return;
    const wrapper = document.createElement("div");
    wrapper.setAttribute("vw", "");
    wrapper.className = "enabled";
    wrapper.id = "vlibras-wrapper";
    wrapper.innerHTML =
      '<div vw-access-button class="active"></div>' +
      '<div vw-plugin-wrapper><div class="vw-plugin-top-wrapper"></div></div>';
    document.body.appendChild(wrapper);
  }

  function initVLibrasWidget() {
    if (window.VLibras) {
      new window.VLibras.Widget("https://vlibras.gov.br/app");
    }
  }

  function removeVLibras() {
    // O widget oficial, depois de carregar, costuma mover o botão de dentro
    // da #vlibras-wrapper direto pro <body> (fora da nossa div). Por isso,
    // não basta apagar só a wrapper: procuramos qualquer resquício dele em
    // qualquer lugar do documento.
    document
      .querySelectorAll("#vlibras-wrapper, [vw], [vw-access-button], [vw-plugin-wrapper]")
      .forEach((el) => el.remove());
    // O <script> fica carregado (é leve) para reativar rápido, sem novo download.
  }

  /* ---------------- Init ---------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initPanelToggle();
    initSwitches();
    initReset();
    initSpeech();
    applyPrefs();
  });
})();
