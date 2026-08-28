/* RASTRO — interações client-side, sem frameworks */

/* ---------------- HOME: check-in de humor ---------------- */
const RastroHome = {
  init() {
    const grid = document.getElementById("mood-grid");
    const feedback = document.getElementById("checkin-feedback");
    if (!grid) return;

    grid.addEventListener("click", async (e) => {
      const btn = e.target.closest(".mood-card");
      if (!btn) return;
      const mood = btn.dataset.mood;

      grid.querySelectorAll(".mood-card").forEach((c) => c.classList.remove("selected"));
      btn.classList.add("selected");

      try {
        const res = await fetch("/api/checkin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mood }),
        });
        const data = await res.json();
        if (data.ok && feedback) {
          feedback.textContent = "Check-in registrado. Obrigado por compartilhar como você está.";
        }
      } catch (err) {
        if (feedback) feedback.textContent = "Não consegui registrar agora, mas obrigado por compartilhar.";
      }
    });
  },
};

/* ---------------- TALK: conversa em etapas ---------------- */
const RastroTalk = {
  init({ step }) {
    const log = document.getElementById("chat-log");
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");
    const inputRow = document.getElementById("chat-input-row");
    if (!log) return;

    let currentStep = step || 0;
    let sending = false;

    function addBubble(html, from) {
      const div = document.createElement("div");
      div.className = `bubble ${from}`;
      div.innerHTML = html;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
      return div;
    }

    function addOptions(options) {
      const wrap = document.createElement("div");
      wrap.className = "talk-options";
      options.forEach((opt) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "talk-option";
        btn.textContent = opt;
        btn.addEventListener("click", () => {
          wrap.remove();
          addBubble(opt, "user");
          sendToServer(opt);
        });
        wrap.appendChild(btn);
      });
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
    }

    function addResult(objective, barrier) {
      const div = document.createElement("div");
      div.className = "talk-result";
      div.innerHTML = `
        <span>✦</span>
        <div>
          <strong>Pronto! Seu 1% já está te esperando.</strong>
          <small>Objetivo: ${objective} · Barreira: ${barrier}</small>
        </div>`;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    }

    async function sendToServer(text) {
      if (sending) return;
      sending = true;
      try {
        const res = await fetch("/api/talk/answer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ step: currentStep, text }),
        });
        const data = await res.json();
        if (data.error) {
          sending = false;
          return;
        }

        currentStep = data.step;
        addBubble(data.reply, "rastro");

        if (data.options && data.options.length) {
          addOptions(data.options);
        }

        if (data.done) {
          inputRow.style.display = "none";
          addResult(data.objective, data.barrier);
          setTimeout(() => {
            window.location.href = data.redirect || "/onepct";
          }, 2200);
        }
      } catch (err) {
        addBubble("Tive um problema para responder agora. Tenta de novo?", "rastro");
      } finally {
        sending = false;
      }
    }

    function send() {
      const text = input.value.trim();
      if (!text) return;
      addBubble(text, "user");
      input.value = "";
      sendToServer(text);
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
  },
};

/* ---------------- WORLD: marcas interativas ---------------- */
const RastroWorld = {
  init() {
    const modal = document.getElementById("world-modal");
    if (!modal) return;

    const emojiEl = document.getElementById("world-modal-emoji");
    const titleEl = document.getElementById("world-modal-title");
    const descEl = document.getElementById("world-modal-desc");

    const obtidoModal = document.getElementById("obtido-modal");
    const obtidoIcon = document.getElementById("obtido-icon");
    const obtidoName = document.getElementById("obtido-name");
    const obtidoMessage = document.getElementById("obtido-message");

    function currentPoints() {
      const el = document.getElementById("world-points");
      if (!el) return 0;
      const match = el.textContent.match(/-?\d+/);
      return match ? parseInt(match[0], 10) : 0;
    }

    function showObtido(emoji, label, message) {
      if (emoji === "🪴") {
        obtidoIcon.innerHTML = '<img src="/static/img/regador-emoji.png" alt="' + label + '">';
      } else {
        obtidoIcon.textContent = emoji;
      }
      obtidoName.textContent = label;
      obtidoMessage.textContent = message;

      modal.hidden = true;
      obtidoModal.hidden = false;
      obtidoModal.querySelector(".world-modal-close").focus();
    }

    async function buyItem(cost, tagEl, emoji, label) {
      tagEl.disabled = true;
      tagEl.textContent = "obtendo...";
      try {
        const res = await fetch("/api/world/buy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cost: cost }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          tagEl.textContent = "não foi possível obter";
          tagEl.disabled = false;
          return;
        }
        showObtido(emoji, label, data.message);
      } catch (err) {
        tagEl.textContent = "erro de conexão";
        tagEl.disabled = false;
      }
    }

    function openFor(btn) {
      const emoji = btn.dataset.emoji || "✦";
      const label = btn.dataset.label || "Marca do mundo";
      const status = btn.dataset.status || "unlocked";
      const threshold = btn.dataset.threshold;

      if (emoji === "🪴") {
        emojiEl.innerHTML = '<img src="/static/img/regador-emoji.png" alt="' + label + '" class="badge-icon-img">';
      } else {
        emojiEl.textContent = emoji;
      }
      titleEl.textContent = label;

      let desc = "";

      let tagEl = modal.querySelector(".world-modal-tag");
      if (tagEl) tagEl.remove();
      tagEl = document.createElement("button");
      tagEl.type = "button";
      tagEl.className = "world-modal-tag";
      descEl.insertAdjacentElement("afterend", tagEl);

      if (status === "unlocked") {
        desc = "Você já descobriu essa marca. Ela apareceu porque você deu um passo de verdade no seu Rastro.";
        tagEl.textContent = "descoberta";
        tagEl.classList.add("is-unlocked");
        tagEl.setAttribute("data-close", "");
      } else {
        const cost = threshold !== undefined ? Math.max(0, Number(threshold)) : 0;
        const balance = currentPoints();
        desc = "Essa marca ainda não faz parte do seu mundo. Você pode guardar seus pontos e obtê-la quando quiser.";
        if (balance >= cost) {
          tagEl.textContent = `obter por ${cost} pts`;
          tagEl.addEventListener("click", function () {
            buyItem(cost, tagEl, emoji, label);
          });
        } else {
          tagEl.textContent = `faltam ${cost - balance} pts`;
          tagEl.disabled = true;
          tagEl.setAttribute("data-close", "");
        }
      }

      descEl.textContent = desc;

      modal.hidden = false;
      modal.querySelector(".world-modal-close").focus();
    }

    function close() {
      modal.hidden = true;
    }

    function closeObtido() {
      obtidoModal.hidden = true;
      location.reload();
    }

    document.querySelectorAll(".world-badge, .unlocks button").forEach((btn) => {
      btn.addEventListener("click", () => openFor(btn));
    });

    modal.addEventListener("click", (e) => {
      if (e.target.closest("[data-close]")) close();
    });

    obtidoModal.addEventListener("click", (e) => {
      if (e.target.closest("[data-close-obtido]")) closeObtido();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) close();
      if (e.key === "Escape" && !obtidoModal.hidden) closeObtido();
    });
  },
};

/* ---------------- WORLD: Troca de Pontos ---------------- */
const RastroTroca = {
  init() {
    const btn = document.getElementById("troca-pontos-btn");
    const modal = document.getElementById("troca-modal");
    if (!btn || !modal) return;

    const balanceEl = document.getElementById("troca-balance-value");
    const costEl = document.getElementById("troca-selected-cost");
    const giftEl = document.getElementById("troca-selected-gift");
    const confirmBtn = document.getElementById("troca-confirm-btn");
    const feedbackEl = document.getElementById("troca-feedback");
    const rewardButtons = Array.from(modal.querySelectorAll(".troca-reward"));

    let selected = null;

    function currentPoints() {
      const match = (balanceEl.textContent || "").match(/-?\d+/);
      return match ? parseInt(match[0], 10) : 0;
    }

    function syncPoints(points) {
      balanceEl.textContent = `${points} pts`;
      const worldPointsEl = document.getElementById("world-points");
      if (worldPointsEl) worldPointsEl.textContent = `${points} pts`;
    }

    function selectReward(rewardBtn) {
      rewardButtons.forEach((b) => b.classList.remove("selected"));
      rewardBtn.classList.add("selected");

      selected = {
        id: rewardBtn.dataset.rewardId,
        cost: Number(rewardBtn.dataset.cost),
        emoji: rewardBtn.dataset.emoji,
        label: rewardBtn.dataset.label,
      };

      costEl.textContent = selected.cost;
      giftEl.textContent = selected.emoji;
      feedbackEl.textContent = "";
      confirmBtn.textContent = "Trocar Pontos";
      confirmBtn.disabled = currentPoints() < selected.cost;
    }

    function resetSelection() {
      selected = null;
      rewardButtons.forEach((b) => b.classList.remove("selected"));
      costEl.textContent = "—";
      giftEl.textContent = "🎁";
      confirmBtn.textContent = "Trocar Pontos";
      confirmBtn.disabled = true;
      feedbackEl.textContent = "";
    }

    function open() {
      resetSelection();
      modal.hidden = false;
      document.body.classList.add("troca-open");
      modal.querySelector(".world-modal-close").focus();
    }

    function close() {
      modal.hidden = true;
      document.body.classList.remove("troca-open");
    }

    async function confirmExchange() {
      if (!selected || confirmBtn.disabled) return;
      confirmBtn.disabled = true;
      confirmBtn.textContent = "trocando...";

      try {
        const res = await fetch("/api/benefits/redeem", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: selected.id }),
        });
        const data = await res.json();

        if (!res.ok || !data.ok) {
          feedbackEl.textContent = "Não foi possível concluir a troca agora.";
          confirmBtn.textContent = "Trocar Pontos";
          confirmBtn.disabled = false;
          return;
        }

        syncPoints(data.points);
        feedbackEl.textContent = `Solicitação registrada: ${data.benefit.emoji} ${data.benefit.label}.`;
        confirmBtn.textContent = "Trocar Pontos";
        confirmBtn.disabled = currentPoints() < selected.cost;
      } catch (err) {
        feedbackEl.textContent = "Erro de conexão. Tenta de novo?";
        confirmBtn.textContent = "Trocar Pontos";
        confirmBtn.disabled = false;
      }
    }

    btn.addEventListener("click", open);

    rewardButtons.forEach((rewardBtn) => {
      rewardBtn.addEventListener("click", () => selectReward(rewardBtn));
    });

    confirmBtn.addEventListener("click", confirmExchange);

    modal.addEventListener("click", (e) => {
      if (e.target.closest("[data-close-troca]")) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) close();
    });
  },
};

/* ---------------- SECRET: posts anônimos ---------------- */
const RastroSecret = {
  init() {
    const feed = document.getElementById("secret-feed");
    const textarea = document.getElementById("secret-textarea");
    const counter = document.getElementById("secret-counter");
    const postBtn = document.getElementById("secret-post-btn");
    if (!feed) return;

    if (textarea && counter) {
      textarea.addEventListener("input", () => {
        counter.textContent = `${textarea.value.length}/500`;
      });
    }

    postBtn.addEventListener("click", async () => {
      const text = textarea.value.trim();
      if (!text) return;

      const res = await fetch("/api/secret/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!data.post) return;

      const article = document.createElement("article");
      article.className = "secret-post";
      article.dataset.id = data.post.id;
      article.innerHTML = `
        <p></p>
        <button class="secret-heart">♡ <span class="heart-count">0</span> <span>eu também</span></button>
        <button class="secret-report">denunciar</button>`;
      article.querySelector("p").textContent = data.post.text;
      feed.prepend(article);

      textarea.value = "";
      if (counter) counter.textContent = "0/500";
    });

    feed.addEventListener("click", async (e) => {
      const heartBtn = e.target.closest(".secret-heart");
      if (heartBtn) {
        const post = heartBtn.closest(".secret-post");
        const id = post.dataset.id;
        const res = await fetch("/api/secret/heart", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id }),
        });
        const data = await res.json();
        if (data.hearts !== undefined) {
          heartBtn.querySelector(".heart-count").textContent = data.hearts;
        }
        return;
      }

      const reportBtn = e.target.closest(".secret-report");
      if (reportBtn) {
        reportBtn.textContent = "denunciado";
        reportBtn.disabled = true;
        reportBtn.style.opacity = "0.5";
        reportBtn.style.cursor = "default";
      }
    });
  },
};

/* ---------------- 1% novo: ciclo mensal/semanal/diário ---------------- */
const RastroCycle = {
  init() {
    const list = document.querySelectorAll(".goal[data-kind]");
    if (!list.length) return;

    async function toggle(item) {
      if (item.classList.contains("locked-card")) return;
      const kind = item.dataset.kind;
      const id = item.dataset.id;
      item.style.pointerEvents = "none";
      try {
        const res = await fetch("/api/goals/toggle", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind, id }),
        });
        const data = await res.json();
        if (data.error) {
          item.style.pointerEvents = "";
          return;
        }
        // o desbloqueio de novas semanas/dias muda a estrutura da página,
        // então recarregamos pra refletir o estado real vindo do servidor
        window.location.reload();
      } catch (err) {
        item.style.pointerEvents = "";
      }
    }

    list.forEach((item) => {
      item.addEventListener("click", () => toggle(item));
      item.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle(item);
        }
      });
    });
  },
};

/* ---------------- Voluntariado (usuário): chat persistente com voluntário ---------------- */
const RastroVolunteer = {
  init() {
    const chat = document.getElementById("volunteer-chat");
    if (!chat) return;

    const log = document.getElementById("volunteer-log");
    const input = document.getElementById("volunteer-input");
    const sendBtn = document.getElementById("volunteer-send");
    const areasBox = document.getElementById("volunteer-areas-box");
    const outcomeBox = document.getElementById("volunteer-outcome-box");

    let ticketId = chat.dataset.ticketId ? parseInt(chat.dataset.ticketId, 10) : null;
    let ticketOpen = chat.dataset.ticketOpen === "true";
    let sending = false;
    let pollTimer = null;

    function addBubble(text, sender) {
      const div = document.createElement("div");
      div.className = `bubble ${sender === "usuario" ? "user" : "rastro"}`;
      div.textContent = text;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    }

    function collectAreas() {
      if (!areasBox) return [];
      return Array.from(areasBox.querySelectorAll('input[name="areas"]:checked')).map((el) => el.value);
    }

    async function createTicket(text) {
      const areas = collectAreas();
      const res = await fetch("/api/voluntario/ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, areas }),
      });
      const data = await res.json();
      if (data.error) return;

      ticketId = data.ticket_id;
      ticketOpen = !data.crisis;
      chat.dataset.ticketId = ticketId;
      chat.dataset.ticketOpen = ticketOpen ? "true" : "false";

      if (areasBox) areasBox.remove();

      // a bolha de abertura (sistema) e a mensagem do usuário já estão na tela;
      // adiciona só o que veio depois delas (aviso de espera ou mensagem do CVV)
      (data.messages || []).slice(2).forEach((m) => addBubble(m.text, m.sender));

      if (!ticketOpen) {
        document.getElementById("volunteer-input-row")?.remove();
      } else {
        startPolling();
      }
    }

    async function sendFollowUp(text) {
      const res = await fetch("/api/voluntario/mensagem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_id: ticketId, text }),
      });
      const data = await res.json();
      if (data.error) return;
    }

    async function send() {
      if (sending) return;
      const text = input.value.trim();
      if (!text) return;
      sending = true;
      input.value = "";
      addBubble(text, "usuario");

      try {
        if (!ticketId) {
          await createTicket(text);
        } else {
          await sendFollowUp(text);
        }
      } finally {
        sending = false;
      }
    }

    if (sendBtn) sendBtn.addEventListener("click", send);
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") send();
      });
    }

    function startPolling() {
      if (pollTimer || !ticketId) return;
      pollTimer = setInterval(async () => {
        try {
          const res = await fetch(`/api/voluntario/mensagens/${ticketId}`);
          const data = await res.json();
          if (!data.messages) return;
          const current = log.querySelectorAll(".bubble").length;
          if (data.messages.length > current) {
            data.messages.slice(current).forEach((m) => addBubble(m.text, m.sender));
          }
          if (data.status !== "fila" && data.status !== "em_atendimento") {
            clearInterval(pollTimer);
            pollTimer = null;
            document.getElementById("volunteer-input-row")?.remove();
            window.location.reload();
          }
        } catch (err) {
          /* silencioso — tenta de novo no próximo ciclo */
        }
      }, 4000);
    }

    if (ticketId && ticketOpen) startPolling();

    // ---- registrar resultado do atendimento (encerrado/encaminhado ao CVV) ----
    if (outcomeBox) {
      const commentEl = document.getElementById("volunteer-outcome-comment");
      outcomeBox.querySelectorAll("[data-rating]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          outcomeBox.querySelectorAll("[data-rating]").forEach((b) => (b.disabled = true));
          try {
            await fetch(`/api/voluntario/ticket/${ticketId}/resultado`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ rating: btn.dataset.rating, comment: commentEl ? commentEl.value.trim() : "" }),
            });
          } finally {
            outcomeBox.innerHTML = "<p>Obrigado por contar como foi. 🌿</p>";
          }
        });
      });
    }
  },
};

/* ---------------- Voluntariado (painel do voluntário): abas + chat das conversas ---------------- */
const RastroVolunteerPanel = {
  init() {
    const tabs = document.querySelectorAll(".volunteer-panel-tab");
    if (!tabs.length) return;

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        document.querySelectorAll(".volunteer-panel-tabpage").forEach((page) => {
          page.hidden = page.dataset.tabpage !== tab.dataset.tab;
        });
      });
    });

    document.querySelectorAll(".volunteer-conversation").forEach((card) => {
      const ticketId = card.dataset.ticketId;
      const log = document.getElementById(`conv-log-${ticketId}`);
      const input = document.getElementById(`conv-input-${ticketId}`);
      const sendBtn = card.querySelector(".conv-send");

      function addBubble(text, sender) {
        const div = document.createElement("div");
        div.className = `bubble ${sender === "voluntario" ? "user" : "rastro"}`;
        div.textContent = text;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
      }

      async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        addBubble(text, "voluntario");
        await fetch(`/voluntario/tickets/${ticketId}/mensagem`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
      }

      if (sendBtn) sendBtn.addEventListener("click", send);
      if (input) {
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") send();
        });
      }

      setInterval(async () => {
        try {
          const res = await fetch(`/voluntario/tickets/${ticketId}/mensagens`);
          const data = await res.json();
          if (!data.messages) return;
          const current = log.querySelectorAll(".bubble").length;
          if (data.messages.length > current) {
            data.messages.slice(current).forEach((m) => addBubble(m.text, m.sender));
          }
        } catch (err) {
          /* silencioso — tenta de novo no próximo ciclo */
        }
      }, 4000);
    });
  },
};
