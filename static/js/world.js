/**
 * world.js — o WORLD inteiro (cena + interface).
 *
 * A ilha, a casa, a árvore e todos os elementos são desenhados em PixiJS
 * dentro de #world-stage-pixi. Não existe mais versão em CSS: o que está
 * na tela vem daqui.
 *
 * Três peças convivem neste arquivo:
 *   WorldEngine — a cena Pixi (céu, estrelas, nuvens, ilha e elementos).
 *   RastroWorld — a interface em volta (progresso, lista lateral, modais
 *                 de detalhe/compra) que conversa com /api/world/*.
 *   RastroTroca — a janela "Resgatar benefício".
 *
 * O estado do mundo chega do servidor em #world-state (mesmo formato de
 * /api/world/state):
 *   { points, progress, remaining,
 *     elements: [{ cost, emoji, label, owned, message }] }
 *
 * ISLAND_TARGET_WIDTH controla o tamanho final da ilha; o halo e todos os
 * elementos escalam junto, proporcionalmente, para nada ficar
 * desproporcional quando esse valor mudar.
 *
 * Paleta reaproveitada das variáveis do projeto (style.css):
 *   --brand:#4fe0b3  --sun:#f7bd6a  --dusk:#b8a6ef  --bg:#03091a
 */

(function () {
  "use strict";

  const ISLAND_IMAGE_URL = "/static/img/island-base-mossy.png";
  const ISLAND_TARGET_WIDTH = 672; // largura final da ilha em px na tela (480 + 40%)
  const ISLAND_BASE_WIDTH = 340; // tamanho original em que halo/elementos foram calibrados

    // Cenário fixo — atualmente vazio: lago e banco viraram elementos de
  // progressão (ver ELEMENT_SLOTS) em vez de aparecerem sempre na ilha.
  const SCENERY = [];

  // Elementos do WORLD: um lugar na ilha para cada marca de
  // rastro_data.WORLD_ELEMENTS (a chave é o custo em pontos). Quem ainda
  // não foi conquistado aparece apagado e pode ser obtido com pontos.
  // Sem `url`, o elemento é desenhado a partir do próprio emoji.
const ELEMENT_SLOTS = {
    0: {
      url: "/static/img/house.png",
      baseWidth: 95,
      offset: { x: 0, y: -55 },
      anchor: { x: 0.5, y: 1 },
      idle: "smoke",
    },
    30: {
      url: "/static/img/pond.png",
      baseWidth: 96,
      offset: { x: -82, y: 20 },
      anchor: { x: 0.5, y: 0.62 },
      idle: "shimmer",
    },
    50: {
      url: "/static/img/bench_recortado.png",
      baseWidth: 48, // mais ~10% menor (era 53)
      offset: { x: 72, y: 22 },, // mais perto da lagoa, fechando o vazio no meio da grama
      anchor: { x: 0.5, y: 0.78 },
      idle: null,
    },
    75: {
      url: "/static/img/arvore_azul.png",
      baseWidth: 68, // um pouco menor que a roxa — leitura de "mais ao fundo"
      offset: { x: 125, y: -12 },
      anchor: { x: 0.5, y: 1 },
      idle: "sway",
    },
    // Árvore roxa — mesmo tratamento visual da árvore azul (slot 75),
    // espelhada pro outro lado da ilha pra não sobrepor a primeira.
    100: {
      url: "/static/img/arvore_roxa.png",
      baseWidth: 88, // um pouco maior que a azul — leitura de "mais em primeiro plano"
      offset: { x: -125, y: -12 },
      anchor: { x: 0.5, y: 1 },
      idle: "sway",
    },
  };
  // Texto fixo de cada balão (visual de referência do mundo). Não depende
  // do `label`/`message` que vêm do servidor — é sempre este texto, pro
  // item aparecer ou não (bloqueado ou não).
  const ELEMENT_MESSAGES = {
    0: "Sua casinha no mundo — cresce junto com você.",
    30: "Um lago calmo pra respirar entre uma tarefa e outra.",
    50: "Um banco pra sentar e ver o quanto você já andou.",
    75: "Uma árvore que cresce a cada nova novidade.",
    100: "Uma árvore roxa que floresce quando você vai além.",
  };

  // Paleta usada pelo engine (halo da ilha, itens bloqueados, tooltip).
  // Reaproveitada das variáveis de style.css citadas no cabeçalho deste
  // arquivo. Ajuste aqui se os tons de style.css mudarem.
  const COLORS = {
    brand: 0x4fe0b3,
    sun: 0xf7bd6a,
    dusk: 0xb8a6ef,
    bg: 0x03091a,
    locked: 0x8a97ad,
    tooltipBg: 0x0b1830,
    tooltipBorder: 0x4fe0b3,
  };

  class WorldEngine {
    constructor(containerId, options) {
      this.container = document.getElementById(containerId);
      if (!this.container) return;

      this.options = options || {};

      this.app = new PIXI.Application({
        resizeTo: this.container,
        backgroundAlpha: 0,
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
      });

      this.container.appendChild(this.app.view);

      this.worldRoot = new PIXI.Container();
      this.app.stage.addChild(this.worldRoot);

      this.time = 0;
      this.hoverables = []; // itens com animação de escala (hover)
      this.smokePuffs = []; // fumacinha da chaminé
      this.tooltips = []; // balões de texto ativos
      this.pieces = []; // tudo que está na ilha (cenário + elementos)
      this.state = null;

      this._boot();
    }

    async _boot() {
      this._buildSky();
      this._buildStars();

      try {
        await this._buildIsland();
      } catch (err) {
        console.error("[world] falha ao carregar a ilha (" + ISLAND_IMAGE_URL + "):", err);
      }

      try {
        await this._buildScenery();
        if (this.state) await this._buildElements();
      } catch (err) {
        console.error("[world] falha ao montar os elementos da ilha:", err);
      }

      this.app.ticker.add((delta) => this._tick(delta));

      this._layout();
      // guarda a referência pra poder remover no destroy() — sem isso,
      // cada init() novo (ex: troca de aba) empilha mais um listener e
      // pode disputar o mesmo container com um engine "fantasma"
      this._onResize = () => this._layout();
      window.addEventListener("resize", this._onResize);

      this.ready = true;
      // sempre esconde o loading no final, mesmo se alguma imagem falhou —
      // assim a cena nunca fica travada em "Preparando seu mundo..."
      this._hideLoading();
    }

    /** Desliga o engine por completo: ticker, listener de resize e o
     * canvas Pixi. Precisa ser chamado antes de criar uma nova WorldEngine
     * no mesmo container (ex: ao trocar de aba/re-render da página),
     * senão sobra um canvas "fantasma" preso ao DOM antigo e a cena nova
     * pode nunca aparecer. */
    destroy() {
      if (this._onResize) window.removeEventListener("resize", this._onResize);
      try {
        this.app.destroy(true, { children: true, texture: true, baseTexture: true });
      } catch (err) {
        console.warn("[world] erro ao destruir engine anterior:", err);
      }
    }

    /** Atualiza a cena com um estado novo vindo do servidor. */
    async setState(state) {
      this.state = state;
      if (!this.elementLayer) return; // ainda montando: _boot usa this.state
      await this._buildElements();
      this._layout();
    }

    _hideLoading() {
      const loading = document.getElementById("world-loading");
      if (loading) {
        loading.classList.add("hidden");
        setTimeout(() => loading.remove(), 400);
      }
    }

    // -------------------------------------------------------------- sky --
    _buildSky() {
      const w = 32, h = 480;
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "#03091a");
      grad.addColorStop(0.65, "#06152b");
      grad.addColorStop(1, "#0b2830");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      this.skyTexture = PIXI.Texture.from(canvas);
      this.sky = new PIXI.Sprite(this.skyTexture);
      this.worldRoot.addChild(this.sky);
    }

    // ----------------------------------------------------------- stars --
    _buildStars() {
      this.stars = new PIXI.Container();
      this.starData = [];

      const STAR_COUNT = 60;
      for (let i = 0; i < STAR_COUNT; i++) {
        const g = new PIXI.Graphics();
        const r = Math.random() * 1.4 + 0.6;
        g.beginFill(0xffffff);
        g.drawCircle(0, 0, r);
        g.endFill();
        g.alpha = Math.random() * 0.6 + 0.2;

        this.starData.push({
          g,
          baseAlpha: g.alpha,
          speed: Math.random() * 1.5 + 0.5,
          phase: Math.random() * Math.PI * 2,
          rx: Math.random(),
          ry: Math.random() * 0.7,
        });
        this.stars.addChild(g);
      }
      this.worldRoot.addChild(this.stars);
    }

    // ---------------------------------------------------------- island --
    async _buildIsland() {
      this.islandRoot = new PIXI.Container();

      // fator de escala aplicado no halo e em todos os elementos, pra
      // crescerem junto com a ilha quando ISLAND_TARGET_WIDTH mudar
      const scaleFactor = ISLAND_TARGET_WIDTH / ISLAND_BASE_WIDTH;
      this._islandScaleFactor = scaleFactor;

      // brilho suave atrás da ilha (halo)
      const glow = new PIXI.Graphics();
      glow.beginFill(COLORS.brand, 0.1);
      glow.drawEllipse(0, 0, 190, 90);
      glow.endFill();
      glow.filters = [new PIXI.BlurFilter(24)];
      glow.scale.set(scaleFactor);
      this.islandRoot.addChild(glow);

      // ilha vinda da imagem
      const texture = await PIXI.Assets.load(ISLAND_IMAGE_URL);
      const island = new PIXI.Sprite(texture);

      // centro da imagem = origem (0,0) do islandRoot, onde todos os
      // elementos se posicionam em cima
      island.anchor.set(0.5, 0.5);
      island.scale.set(ISLAND_TARGET_WIDTH / island.texture.width);

      this.islandRoot.addChild(island);
      this.island = island;
      this.worldRoot.addChild(this.islandRoot);

      // camada dos itens, sempre acima da ilha. O cenário nunca é
      // reconstruído; os elementos sim, a cada mudança de estado.
      this.decorLayer = new PIXI.Container();
      this.islandRoot.addChild(this.decorLayer);

      this.sceneryLayer = new PIXI.Container();
      this.elementLayer = new PIXI.Container();
      this.decorLayer.addChild(this.sceneryLayer, this.elementLayer);
    }

    // --------------------------------------------------------- cenário --
    async _buildScenery() {
      for (const item of SCENERY) {
        await this._addPiece(this.sceneryLayer, item, { locked: false });
      }
    }

    // ------------------------------------------------------- elementos --
    async _buildElements() {
      // limpa só os elementos (o cenário fica onde está)
      this.pieces = this.pieces.filter((piece) => {
        if (!piece.isElement) return true;
        piece.destroy();
        return false;
      });
      this.hoverables = this.hoverables.filter((h) => !h.piece.isElement);
      this.smokePuffs.forEach((puff) => puff.g.destroy());
      this.smokePuffs = [];
      this.elementLayer.removeChildren();

      for (const element of (this.state && this.state.elements) || []) {
        const slot = ELEMENT_SLOTS[element.cost];
        if (!slot) continue; // marca sem lugar na ilha: aparece só na lista lateral
        await this._addPiece(
          this.elementLayer,
          {
            key: "element-" + element.cost,
            url: slot.url,
            emoji: element.emoji,
            baseWidth: slot.baseWidth,
            offset: slot.offset,
            anchor: slot.anchor,
            idle: slot.idle,
            label: element.label,
            tooltipText: ELEMENT_MESSAGES[element.cost] || null,
            element: element,
          },
          { locked: !element.owned }
        );
      }

      this._measureTop();
    }

    /** Cria o sprite de um item (imagem ou emoji) e pendura na camada. */
    async _addPiece(layer, item, opts) {
      const scaleFactor = this._islandScaleFactor || 1;
      const locked = !!(opts && opts.locked);

      let sprite;
      if (item.url) {
        let texture;
        try {
          texture = await PIXI.Assets.load(item.url);
        } catch (err) {
          console.error("[world] falha ao carregar " + item.key + " (" + item.url + "):", err);
          return null;
        }
        sprite = new PIXI.Sprite(texture);
      } else {
        // sem imagem: o próprio emoji vira o sprite
        sprite = new PIXI.Text(item.emoji || "✦", new PIXI.TextStyle({ fontSize: 96 }));
      }

      sprite.anchor.set(item.anchor.x, item.anchor.y);

      // sprite.width já considera a escala atual (1 aqui), então a razão
      // abaixo leva o item exatamente para baseWidth * escala da ilha
      const baseScale = (item.baseWidth / sprite.width) * scaleFactor;
      sprite.scale.set(baseScale);
      sprite.x = item.offset.x * scaleFactor;
      sprite.y = item.offset.y * scaleFactor;

      if (locked) {
        sprite.alpha = 0.22;
        sprite.tint = COLORS.locked;
      }

      // sombra leve embaixo, pra "fixar" o item na grama
      const shadow = new PIXI.Graphics();
      shadow.beginFill(0x03091a, locked ? 0.1 : 0.28);
      const radius = (sprite.width / baseScale) * 0.3;
      shadow.drawEllipse(0, 0, radius, radius * 0.34);
      shadow.endFill();
      shadow.filters = [new PIXI.BlurFilter(6)];
      shadow.x = sprite.x;
      shadow.y = sprite.y - (item.anchor.y === 1 ? 2 : 0);
      shadow.scale.set(baseScale);
      layer.addChildAt(shadow, 0);
      layer.addChild(sprite);

      const piece = {
        item,
        sprite,
        shadow,
        baseScale,
        locked,
        isElement: !!item.element,
        smokeTimer: 0,
        smokeOrigin: null,
        destroy() {
          layer.removeChild(sprite);
          layer.removeChild(shadow);
          sprite.destroy();
          shadow.destroy();
        },
      };
      this.pieces.push(piece);

      this._makeInteractive(piece);

      if (item.idle === "smoke" && !locked) {
        // saída aproximada da chaminé, relativa ao sprite (anchor 0.5,1)
        piece.smokeOrigin = { x: sprite.width * 0.3, y: -sprite.height * 0.92 };
      }
      return piece;
    }

    _measureTop() {
      // ponto mais alto entre todos os itens (coordenada local, antes da
      // escala do islandRoot) — usado no _layout pra nunca cortar nada no topo
      this._decorTopLocal = this.decorLayer.getLocalBounds().y;
    }

    // ---------------------------------------------------- interatividade --
    _makeInteractive(piece) {
      const sprite = piece.sprite;
      sprite.eventMode = "static";
      sprite.cursor = "pointer";

      const state = { piece, sprite, currentMul: 1, targetMul: 1, hovering: false };
      this.hoverables.push(state);

      sprite.on("pointerover", () => {
        state.targetMul = 1.1;
        state.hovering = true;
      });
      sprite.on("pointerout", () => {
        state.targetMul = 1;
        state.hovering = false;
      });
      sprite.on("pointertap", () => {
        // pequeno "pulo" de clique, além do zoom de hover
        state.targetMul = 1.22;
        setTimeout(() => {
          state.targetMul = state.hovering ? 1.1 : 1;
        }, 140);

        // balão de texto: usa o texto fixo do elemento (casa/lago/banco/
        // árvore), aparecendo sempre — obtido ou não. Se não houver texto
        // fixo, cai pro label do próprio elemento.
        if (piece.item.tooltipText) {
          this._showTooltip(sprite, piece.item.tooltipText);
        } else if (piece.item.label) {
          this._showTooltip(sprite, piece.item.label);
        }

        // o modal de detalhe/compra só abre pra item ainda bloqueado (é
        // por ele que a compra acontece). Item já obtido fica só com o
        // balão — sem a tela de "você já descobriu essa marca".
        if (piece.item.element && !piece.item.element.owned && this.options.onSelectElement) {
          this.options.onSelectElement(piece.item.element);
        }
      });
    }

    _showTooltip(sprite, text) {
      const container = new PIXI.Container();

      const label = new PIXI.Text(
        text,
        new PIXI.TextStyle({
          fontFamily: "Space Grotesk, sans-serif",
          fontSize: 13,
          fontWeight: "600",
          fill: 0xe9f2ff,
          wordWrap: true,
          wordWrapWidth: 180,
          align: "center",
        })
      );
      label.anchor.set(0.5, 0.5);

      const paddingX = 14, paddingY = 10;
      const bg = new PIXI.Graphics();
      bg.lineStyle(1, COLORS.tooltipBorder, 0.6);
      bg.beginFill(COLORS.tooltipBg, 0.92);
      bg.drawRoundedRect(
        -label.width / 2 - paddingX,
        -label.height / 2 - paddingY,
        label.width + paddingX * 2,
        label.height + paddingY * 2,
        10
      );
      bg.endFill();

      // setinha (tail) do balão, apontando pro item — como na referência
      const tailSize = 7;
      const tailY = label.height / 2 + paddingY;
      bg.lineStyle(1, COLORS.tooltipBorder, 0.6);
      bg.beginFill(COLORS.tooltipBg, 0.92);
      bg.moveTo(-tailSize, tailY);
      bg.lineTo(0, tailY + tailSize);
      bg.lineTo(tailSize, tailY);
      bg.closePath();
      bg.endFill();

      container.addChild(bg, label);
      container.x = sprite.x;
      container.y = sprite.y - sprite.height - 18;
      container.alpha = 0;
      container.scale.set(0.9);

      this.decorLayer.addChild(container);
      this.tooltips.push({ container, born: this.time, ttl: 210 });
    }

    // ------------------------------------------------------------ fumaça --
    _spawnSmokePuff(piece) {
      const g = new PIXI.Graphics();
      g.beginFill(0xcfd9e8, 0.22);
      g.drawCircle(0, 0, 3 + Math.random() * 2);
      g.endFill();
      g.x = piece.sprite.x + piece.smokeOrigin.x + (Math.random() * 6 - 3);
      g.y = piece.sprite.y + piece.smokeOrigin.y;
      this.elementLayer.addChild(g);
      this.smokePuffs.push({
        g,
        born: this.time,
        vx: (Math.random() * 0.3 - 0.15) * (this._islandScaleFactor || 1),
        vy: -(0.5 + Math.random() * 0.3) * (this._islandScaleFactor || 1),
      });
    }

    // ------------------------------------------------------------ tick --
    _tick(delta) {
      this.time += delta;

      for (const s of this.starData) {
        s.g.alpha = s.baseAlpha * (0.6 + 0.4 * Math.sin(this.time * 0.02 * s.speed + s.phase));
      }

      const bob = Math.sin(this.time * 0.02) * 6;
      if (this.islandRoot && this._baseIslandY !== undefined) {
        this.islandRoot.y = this._baseIslandY + bob;
        this.islandRoot.rotation = Math.sin(this.time * 0.012) * 0.01;
      }

      this._tickPieces(delta);
    }

    _tickPieces(delta) {
      // hover/clique: aproxima suavemente a escala atual da escala-alvo
      for (const state of this.hoverables) {
        state.currentMul += (state.targetMul - state.currentMul) * Math.min(1, 0.18 * delta);
        state.sprite.scale.set(state.piece.baseScale * state.currentMul);
      }

      const scaleFactor = this._islandScaleFactor || 1;
      for (const piece of this.pieces) {
        const sprite = piece.sprite;
        if (piece.item.idle === "sway") {
          sprite.rotation = Math.sin(this.time * 0.02) * 0.045;
        } else if (piece.item.idle === "shimmer") {
          sprite.alpha = piece.locked ? 0.22 : 0.94 + Math.sin(this.time * 0.04) * 0.06;
        } else if (piece.item.idle === "fly") {
          sprite.x = piece.item.offset.x * scaleFactor + Math.sin(this.time * 0.012) * 18;
          sprite.y = piece.item.offset.y * scaleFactor + Math.sin(this.time * 0.035) * 6;
        } else if (piece.item.idle === "smoke" && piece.smokeOrigin) {
          piece.smokeTimer -= delta;
          if (piece.smokeTimer <= 0) {
            this._spawnSmokePuff(piece);
            piece.smokeTimer = 55 + Math.random() * 25;
          }
        }
      }

      // partículas de fumaça
      for (let i = this.smokePuffs.length - 1; i >= 0; i--) {
        const p = this.smokePuffs[i];
        const age = this.time - p.born;
        p.g.x += p.vx * delta;
        p.g.y += p.vy * delta;
        p.g.alpha = Math.max(0, 0.22 - age * 0.0022);
        p.g.scale.set(1 + age * 0.01);
        if (age > 110) {
          this.elementLayer.removeChild(p.g);
          p.g.destroy();
          this.smokePuffs.splice(i, 1);
        }
      }

      // balões de texto: fade in, segura um tempo, fade out e remove
      for (let i = this.tooltips.length - 1; i >= 0; i--) {
        const t = this.tooltips[i];
        const age = this.time - t.born;
        if (age < 14) {
          t.container.alpha = Math.min(1, age / 14);
          t.container.scale.set(0.9 + 0.1 * Math.min(1, age / 14));
        } else if (age > t.ttl - 20 && age <= t.ttl) {
          t.container.alpha = Math.max(0, (t.ttl - age) / 20);
        } else if (age > t.ttl) {
          this.decorLayer.removeChild(t.container);
          t.container.destroy({ children: true });
          this.tooltips.splice(i, 1);
        }
      }
    }

    // ---------------------------------------------------------- layout --
    _layout() {
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;

      this.sky.width = w;
      this.sky.height = h;

      for (const s of this.starData) {
        s.g.x = s.rx * w;
        s.g.y = s.ry * h;
      }

      if (!this.islandRoot) return;

      this.islandRoot.x = w / 2;

      const islandScale = Math.max(Math.min(1, w / 640), 0.55);
      this.islandRoot.scale.set(islandScale);

      // posição vertical "ideal"...
      let baseY = h * 0.62;

      // ...mas nunca deixando o item mais alto passar do topo do palco: se
      // passaria, empurra a ilha pra baixo até caber com uma margem.
      const TOP_MARGIN = 24;
      if (this._decorTopLocal !== undefined) {
        const minY = TOP_MARGIN - this._decorTopLocal * islandScale;
        if (baseY < minY) baseY = minY;
      }

      this._baseIslandY = baseY;
      this.islandRoot.y = baseY;
    }
  }

  /* ---------------- WORLD: progresso, marcas e compra ---------------- */
  const RastroWorld = {
    engine: null,
    state: null,

    init() {
      const stage = document.getElementById("world-stage-pixi");
      const modal = document.getElementById("world-modal");
      if (!stage || !modal) {
        // antes isso retornava em silêncio — se essa função rodar antes
        // do DOM estar pronto, ou numa aba/rota que não tem esses
        // elementos, ninguém saberia por que o mundo não apareceu
        console.warn(
          "[world] RastroWorld.init() chamado sem #world-stage-pixi ou #world-modal no DOM — nada foi desenhado."
        );
        return;
      }

      // se já existir um engine de uma chamada anterior (ex: troca de
      // aba Meu Mundo/Mundo Real chamando init() de novo), desliga ele
      // primeiro — evita canvas duplicado/fantasma disputando o container
      if (this.engine) {
        this.engine.destroy();
        this.engine = null;
      }

      this.modal = modal;
      this.emojiEl = document.getElementById("world-modal-emoji");
      this.titleEl = document.getElementById("world-modal-title");
      this.descEl = document.getElementById("world-modal-desc");

      this.obtidoModal = document.getElementById("obtido-modal");
      this.obtidoIcon = document.getElementById("obtido-icon");
      this.obtidoName = document.getElementById("obtido-name");
      this.obtidoMessage = document.getElementById("obtido-message");

      this.state = this._readInitialState();

      if (window.PIXI) {
        this.engine = new WorldEngine("world-stage-pixi", {
          onSelectElement: (element) => this.openFor(element),
        });
        this.engine.setState(this.state);
      } else {
        console.error("[world] PixiJS não carregou — a ilha não será desenhada.");
        const loading = document.getElementById("world-loading");
        if (loading) loading.textContent = "Não foi possível carregar seu mundo agora.";
      }

      // lista lateral: mesmo fluxo do clique na ilha, e acessível por teclado
      document.querySelectorAll("#world-unlocks button").forEach((btn) => {
        btn.addEventListener("click", () => {
          const element = this._elementByCost(Number(btn.dataset.cost));
          if (element) this.openFor(element);
        });
      });

      modal.addEventListener("click", (e) => {
        if (e.target.closest("[data-close]")) this.close();
      });
      this.obtidoModal.addEventListener("click", (e) => {
        if (e.target.closest("[data-close-obtido]")) this.closeObtido();
      });
      document.addEventListener("keydown", (e) => {
        if (e.key !== "Escape") return;
        if (!modal.hidden) this.close();
        if (!this.obtidoModal.hidden) this.closeObtido();
      });
    },

    _readInitialState() {
      const empty = { points: 0, progress: 0, remaining: 0, elements: [] };
      const el = document.getElementById("world-state");
      if (!el) return empty;
      try {
        return JSON.parse(el.textContent);
      } catch (err) {
        console.error("[world] estado inicial inválido:", err);
        return empty;
      }
    },

    _elementByCost(cost) {
      return (this.state.elements || []).find((el) => el.cost === cost) || null;
    },

    /** O 🪴 tem arte própria; os outros usam o emoji mesmo. */
    _iconHtml(emoji, label) {
      if (emoji !== "🪴") return null;
      return '<img src="/static/img/regador-emoji.png" alt="' + label + '" class="badge-icon-img">';
    },

    /** Aplica um estado novo na tela inteira, sem recarregar a página. */
    applyState(state) {
      this.state = state;

      const pointsEl = document.getElementById("world-points");
      if (pointsEl) pointsEl.textContent = state.points + " pts";

      const bar = document.getElementById("world-progress-bar");
      if (bar) bar.style.width = state.progress + "%";

      const pct = document.getElementById("world-progress-pct");
      if (pct) pct.textContent = Math.round(state.progress) + "%";

      const remaining = document.getElementById("world-remaining");
      if (remaining) remaining.textContent = state.remaining + " pts até a próxima marca";

      const balance = document.getElementById("troca-balance-value");
      if (balance) balance.textContent = state.points + " pts";

      const count = document.getElementById("world-found-count");
      if (count) {
        const owned = (state.elements || []).filter((el) => el.owned).length;
        count.textContent = owned + " marcas descobertas.";
      }

      document.querySelectorAll("#world-unlocks button").forEach((btn) => {
        const element = this._elementByCost(Number(btn.dataset.cost));
        if (!element) return;
        btn.classList.toggle("unlocked", element.owned);
        btn.dataset.status = element.owned ? "unlocked" : "locked";
      });

      if (this.engine) this.engine.setState(state);
    },

    /** Relê o estado no servidor (usado depois de gastar pontos na troca). */
    async refresh() {
      try {
        const res = await fetch("/api/world/state");
        if (!res.ok) return;
        this.applyState(await res.json());
      } catch (err) {
        /* sem conexão: mantém a tela como está */
      }
    },

    openFor(element) {
      const icon = this._iconHtml(element.emoji, element.label);
      if (icon) {
        this.emojiEl.innerHTML = icon;
      } else {
        this.emojiEl.textContent = element.emoji;
      }
      this.titleEl.textContent = element.label;

      let tagEl = this.modal.querySelector(".world-modal-tag");
      if (tagEl) tagEl.remove();
      tagEl = document.createElement("button");
      tagEl.type = "button";
      tagEl.className = "world-modal-tag";
      this.descEl.insertAdjacentElement("afterend", tagEl);

      if (element.owned) {
        this.descEl.textContent =
          "Você já descobriu essa marca. Ela apareceu porque você deu um passo de verdade no seu Rastro.";
        tagEl.textContent = "descoberta";
        tagEl.classList.add("is-unlocked");
        tagEl.setAttribute("data-close", "");
      } else {
        this.descEl.textContent =
          "Essa marca ainda não faz parte do seu mundo. Você pode guardar seus pontos e obtê-la quando quiser.";
        const cost = Math.max(0, Number(element.cost) || 0);
        const balance = this.state.points || 0;
        if (balance >= cost) {
          tagEl.textContent = "obter por " + cost + " pts";
          tagEl.addEventListener("click", () => this.buy(element, tagEl));
        } else {
          tagEl.textContent = "faltam " + (cost - balance) + " pts";
          tagEl.disabled = true;
          tagEl.setAttribute("data-close", "");
        }
      }

      this.modal.hidden = false;
      this.modal.querySelector(".world-modal-close").focus();
    },

    async buy(element, tagEl) {
      tagEl.disabled = true;
      tagEl.textContent = "obtendo...";
      try {
        const res = await fetch("/api/world/buy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cost: element.cost }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          tagEl.textContent = "não foi possível obter";
          tagEl.disabled = false;
          return;
        }
        this.applyState(data);
        this.showObtido(data.emoji, data.label, data.message);
      } catch (err) {
        tagEl.textContent = "erro de conexão";
        tagEl.disabled = false;
      }
    },

    showObtido(emoji, label, message) {
      const icon = this._iconHtml(emoji, label);
      if (icon) {
        this.obtidoIcon.innerHTML = icon;
      } else {
        this.obtidoIcon.textContent = emoji;
      }
      this.obtidoName.textContent = label;
      this.obtidoMessage.textContent = message;

      this.modal.hidden = true;
      this.obtidoModal.hidden = false;
      this.obtidoModal.querySelector(".world-modal-close").focus();
    },

    close() {
      this.modal.hidden = true;
    },

    closeObtido() {
      this.obtidoModal.hidden = true;
    },
  };

  /* ---------------- WORLD: Resgatar benefício ---------------- */
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
        confirmBtn.textContent = "Resgatar benefício";
        confirmBtn.disabled = currentPoints() < selected.cost;
      }

      function resetSelection() {
        selected = null;
        rewardButtons.forEach((b) => b.classList.remove("selected"));
        costEl.textContent = "—";
        giftEl.textContent = "🎁";
        confirmBtn.textContent = "Resgatar benefício";
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
            confirmBtn.textContent = "Resgatar benefício";
            confirmBtn.disabled = false;
            return;
          }

          feedbackEl.textContent =
            "Solicitação registrada: " + data.benefit.emoji + " " + data.benefit.label + ".";
          confirmBtn.textContent = "Resgatar benefício";
          // o saldo mudou: atualiza ilha, progresso e saldo de uma vez só
          await RastroWorld.refresh();
          confirmBtn.disabled = currentPoints() < selected.cost;
        } catch (err) {
          feedbackEl.textContent = "Erro de conexão. Tenta de novo?";
          confirmBtn.textContent = "Resgatar benefício";
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

  window.RastroWorld = RastroWorld;
  window.RastroTroca = RastroTroca;
})();
