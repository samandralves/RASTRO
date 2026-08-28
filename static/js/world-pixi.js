/**
 * world-pixi.js
 *
 * Dia 1 do mundo interativo: cena base em PixiJS. A ilha e os elementos
 * decorativos (casa, árvore, banco e lago) vêm de imagens recortadas
 * (fundo removido) em static/img/ — troque os paths abaixo se mudar o
 * nome/local dos arquivos.
 *
 * ISLAND_TARGET_WIDTH controla o tamanho final da ilha. O halo (brilho
 * atrás da ilha) e todos os elementos decorativos escalam junto
 * automaticamente, proporcionais a esse valor, pra não ficar
 * desproporcional quando você mudar o tamanho da ilha.
 *
 * Elementos decorativos (casa, árvore, banco, lago) são interativos:
 *   - hover: dá um leve "zoom" e um brilho na base do elemento
 *   - clique: dá uma pequena animação de "pulo" e mostra um balão de
 *     texto com uma frase curta sobre o elemento
 *   - a árvore balança sutilmente sozinha; a casa solta fumacinha
 *     pela chaminé
 *
 * Paleta reaproveitada das variáveis do projeto (style.css):
 *   --brand:#4fe0b3  --sun:#f7bd6a  --dusk:#b8a6ef  --bg:#03091a
 */

(function () {
  "use strict";

  const ISLAND_IMAGE_URL = "/static/img/island.png";
  const ISLAND_TARGET_WIDTH = 480; // largura final da ilha em px na tela
  const ISLAND_BASE_WIDTH = 340; // tamanho original em que halo/elementos foram calibrados

  // Elementos decorativos: cada um tem sua imagem, uma largura-base (calibrada
  // para ISLAND_BASE_WIDTH) e um offset (x, y) a partir do centro da ilha.
  // offsets também calibrados pra ISLAND_BASE_WIDTH — escalam junto com scaleFactor.
  const DECOR_ITEMS = [
    {
      key: "house",
      url: "/static/img/house.png",
      baseWidth: 132,
      offset: { x: -42, y: -86 },
      anchor: { x: 0.5, y: 1 },
      label: "Sua casinha no mundo — cresce junto com você.",
      idle: "smoke",
    },
    {
      key: "tree",
      url: "/static/img/tree.png",
      baseWidth: 108,
      offset: { x: 98, y: -46 },
      anchor: { x: 0.5, y: 1 },
      label: "Uma árvore que cresce a cada meta concluída.",
      idle: "sway",
    },
    {
      key: "pond",
      url: "/static/img/pond.png",
      baseWidth: 132,
      offset: { x: -78, y: 34 },
      anchor: { x: 0.5, y: 0.62 },
      label: "Um lago calmo pra respirar entre uma tarefa e outra.",
      idle: "shimmer",
    },
    {
      key: "bench",
      url: "/static/img/bench.png",
      baseWidth: 104,
      offset: { x: 64, y: 40 },
      anchor: { x: 0.5, y: 0.78 },
      label: "Um banco pra sentar e olhar o quanto você já andou.",
      idle: null,
    },
  ];

  const COLORS = {
    brand: 0x4fe0b3,
    brandDark: 0x159b7e,
    sun: 0xf7bd6a,
    dusk: 0xb8a6ef,
    skyTop: 0x03091a,
    skyBottom: 0x0b2830,
    tooltipBg: 0x0b1830,
    tooltipBorder: 0x4fe0b3,
  };

  class WorldEngine {
    constructor(containerId) {
      this.container = document.getElementById(containerId);
      if (!this.container) return;

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

      this._boot();
    }

    async _boot() {
      this._buildSky();
      this._buildStars();
      this._buildClouds();
      await this._buildIsland();
      await this._buildDecor();

      this.app.ticker.add((delta) => this._tick(delta));

      this._layout();
      window.addEventListener("resize", () => this._layout());

      this._hideLoading();
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

    // ---------------------------------------------------------- clouds --
    _buildClouds() {
      this.clouds = new PIXI.Container();
      this.cloudData = [];

      const CLOUD_COUNT = 4;
      for (let i = 0; i < CLOUD_COUNT; i++) {
        const g = new PIXI.Graphics();
        const puffs = 3 + Math.floor(Math.random() * 2);
        g.beginFill(0xbfe0f0, 0.08);
        for (let p = 0; p < puffs; p++) {
          const px = p * 22 - (puffs * 22) / 2;
          const r = 18 + Math.random() * 10;
          g.drawCircle(px, 0, r);
        }
        g.endFill();

        this.cloudData.push({
          g,
          ry: Math.random() * 0.3 + 0.05,
          speed: (Math.random() * 8 + 4) * (Math.random() < 0.5 ? 1 : -1),
          startX: Math.random(),
        });
        this.clouds.addChild(g);
      }
      this.worldRoot.addChild(this.clouds);
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
      glow.beginFill(COLORS.brand, 0.10);
      glow.drawEllipse(0, 0, 190, 90);
      glow.endFill();
      glow.filters = [new PIXI.BlurFilter(24)];
      glow.scale.set(scaleFactor);
      this.islandRoot.addChild(glow);

      // ilha vinda da imagem
      const texture = await PIXI.Assets.load(ISLAND_IMAGE_URL);
      const island = new PIXI.Sprite(texture);

      // centro da imagem = origem (0,0) do islandRoot, onde tudo mais
      // (casa, árvore, banco, lago) se posiciona em cima
      island.anchor.set(0.5, 0.5);

      const scaleRatio = ISLAND_TARGET_WIDTH / island.texture.width;
      island.scale.set(scaleRatio);

      this.islandRoot.addChild(island);
      this.island = island;
      this.worldRoot.addChild(this.islandRoot);

      // camada onde ficam os elementos decorativos, sempre acima da ilha
      this.decorLayer = new PIXI.Container();
      this.islandRoot.addChild(this.decorLayer);
    }

    // ---------------------------------------------------------- decor --
    async _buildDecor() {
      const scaleFactor = this._islandScaleFactor || 1;

      for (const item of DECOR_ITEMS) {
        const texture = await PIXI.Assets.load(item.url);
        const sprite = new PIXI.Sprite(texture);

        sprite.anchor.set(item.anchor.x, item.anchor.y);

        const ratio = item.baseWidth / sprite.texture.width;
        const baseScale = ratio * scaleFactor;
        sprite.scale.set(baseScale);

        sprite.x = item.offset.x * scaleFactor;
        sprite.y = item.offset.y * scaleFactor;

        // sombra leve embaixo de cada elemento, pra "fixar" ele na grama
        const shadow = new PIXI.Graphics();
        shadow.beginFill(0x03091a, 0.28);
        shadow.drawEllipse(0, 0, (sprite.width / baseScale) * 0.30, (sprite.width / baseScale) * 0.10);
        shadow.endFill();
        shadow.filters = [new PIXI.BlurFilter(6)];
        shadow.x = sprite.x;
        shadow.y = sprite.y - (item.anchor.y === 1 ? 2 : 0);
        shadow.scale.set(baseScale);
        this.decorLayer.addChildAt(shadow, 0);

        this.decorLayer.addChild(sprite);

        this._makeInteractive(sprite, item, baseScale);

        item.sprite = sprite;

        if (item.idle === "smoke") {
          this._initSmoke(sprite, item);
        }
      }
    }

    // ---------------------------------------------------- interatividade --
    _makeInteractive(sprite, item, baseScale) {
      sprite.eventMode = "static";
      sprite.cursor = "pointer";

      const state = {
        sprite,
        item,
        baseScale,
        currentMul: 1,
        targetMul: 1,
        hovering: false,
      };
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
        this._bounce(state);
        this._showTooltip(sprite, item.label);
      });
    }

    _bounce(state) {
      // pequeno "pulo" de clique, além do zoom de hover
      state.targetMul = 1.22;
      setTimeout(() => {
        state.targetMul = state.hovering ? 1.1 : 1;
      }, 140);
    }

    _showTooltip(sprite, text) {
      const container = new PIXI.Container();

      const style = new PIXI.TextStyle({
        fontFamily: "Space Grotesk, sans-serif",
        fontSize: 13,
        fontWeight: "600",
        fill: 0xe9f2ff,
        wordWrap: true,
        wordWrapWidth: 180,
        align: "center",
      });
      const label = new PIXI.Text(text, style);
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

      container.addChild(bg, label);
      container.x = sprite.x;
      container.y = sprite.y - sprite.height - 18;
      container.alpha = 0;
      container.scale.set(0.9);

      this.decorLayer.addChild(container);
      this.tooltips.push({ container, born: this.time, ttl: 210, dying: false });
    }

    // ------------------------------------------------------------ fumaça --
    _initSmoke(sprite, item) {
      // ponto de saída aproximado da chaminé, relativo ao sprite (que tem
      // anchor 0.5,1 — base no chão). Ajuste os valores se trocar a imagem.
      item.smokeOrigin = { x: sprite.width * 0.30, y: -sprite.height * 0.92 };
      item.smokeTimer = 0;
    }

    _spawnSmokePuff(item) {
      const g = new PIXI.Graphics();
      g.beginFill(0xcfd9e8, 0.22);
      g.drawCircle(0, 0, 3 + Math.random() * 2);
      g.endFill();
      g.x = item.sprite.x + item.smokeOrigin.x + (Math.random() * 6 - 3);
      g.y = item.sprite.y + item.smokeOrigin.y;
      this.decorLayer.addChild(g);
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
        s.g.alpha =
          s.baseAlpha * (0.6 + 0.4 * Math.sin(this.time * 0.02 * s.speed + s.phase));
      }

      const w = this.app.renderer.width / this.app.renderer.resolution;
      for (const c of this.cloudData) {
        c.g.x += (c.speed * delta) / 60;
        const half = 90;
        if (c.g.x > w + half) c.g.x = -half;
        if (c.g.x < -half) c.g.x = w + half;
      }

      const bob = Math.sin(this.time * 0.02) * 6;
      if (this.islandRoot) {
        this.islandRoot.y = this._baseIslandY + bob;
        this.islandRoot.rotation = Math.sin(this.time * 0.012) * 0.01;
      }

      this._tickDecor(delta);
    }

    _tickDecor(delta) {
      // hover/clique: aproxima suavemente a escala atual da escala-alvo
      for (const state of this.hoverables) {
        state.currentMul += (state.targetMul - state.currentMul) * Math.min(1, 0.18 * delta);
        state.sprite.scale.set(state.baseScale * state.currentMul);
      }

      // idle: árvore balançando e lago com leve "respiração"
      for (const item of DECOR_ITEMS) {
        if (!item.sprite) continue;
        if (item.idle === "sway") {
          item.sprite.rotation = Math.sin(this.time * 0.02) * 0.045;
        } else if (item.idle === "shimmer") {
          const pulse = 1 + Math.sin(this.time * 0.03) * 0.015;
          item.sprite.alpha = 0.94 + Math.sin(this.time * 0.04) * 0.06;
          void pulse;
        } else if (item.idle === "smoke") {
          item.smokeTimer -= delta;
          if (item.smokeTimer <= 0) {
            this._spawnSmokePuff(item);
            item.smokeTimer = 55 + Math.random() * 25;
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
          this.decorLayer.removeChild(p.g);
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

      for (const c of this.cloudData) {
        c.g.x = c.startX * w;
        c.g.y = c.ry * h;
      }

      if (!this.islandRoot) return;

      this.islandRoot.x = w / 2;
      this._baseIslandY = h * 0.62;
      this.islandRoot.y = this._baseIslandY;

      const scale = Math.min(1, w / 640);
      this.islandRoot.scale.set(Math.max(scale, 0.55));
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("world-stage-pixi") && window.PIXI) {
      window.__worldEngine = new WorldEngine("world-stage-pixi");
    }
  });
})();
