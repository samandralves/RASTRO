/**
 * world-pixi.js
 *
 * Dia 1 do mundo interativo: cena base em PixiJS, sem nenhum item
 * comprado ainda (isso entra no Dia 2/3). Já deixa pronta:
 *   - céu com gradiente + estrelas piscando + nuvens passando
 *   - ilha flutuante desenhada em código (sem depender de imagem externa)
 *   - casa simples sobre a ilha
 *   - flutuação suave contínua da ilha (mundo nunca parece parado)
 *
 * Paleta reaproveitada das variáveis do projeto (style.css):
 *   --brand:#4fe0b3  --sun:#f7bd6a  --dusk:#b8a6ef  --bg:#03091a
 */

(function () {
  "use strict";

  const COLORS = {
    brand: 0x4fe0b3,
    brandDark: 0x159b7e,
    sun: 0xf7bd6a,
    dusk: 0xb8a6ef,
    skyTop: 0x03091a,
    skyBottom: 0x0b2830,
    islandTop: 0x1c4a52,
    islandTopLight: 0x2f6f6a,
    islandBottom: 0x0e2a33,
    houseWall: 0xf0d9b5,
    houseRoof: 0xc0554a,
    houseDoor: 0x5b3a29,
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

      this._buildSky();
      this._buildStars();
      this._buildClouds();
      this._buildIsland();
      this._buildHouse();

      this.app.ticker.add((delta) => this._tick(delta));

      // primeiro layout + reposiciona quando a tela muda de tamanho
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
      const w = 32, h = 480; // textura vertical fina, esticada na largura toda
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
          // posição relativa (0..1) — recalculada no _layout()
          rx: Math.random(),
          ry: Math.random() * 0.7, // estrelas só na parte de cima do céu
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
    _buildIsland() {
      this.islandRoot = new PIXI.Container();

      // brilho suave atrás da ilha (halo)
      const glow = new PIXI.Graphics();
      glow.beginFill(COLORS.brand, 0.10);
      glow.drawEllipse(0, 0, 190, 90);
      glow.endFill();
      glow.filters = [new PIXI.BlurFilter(24)];
      this.islandRoot.addChild(glow);

      // corpo da ilha (formato orgânico com bezier)
      const island = new PIXI.Graphics();

      island.beginFill(COLORS.islandBottom);
      island.moveTo(-150, 10);
      island.bezierCurveTo(-160, 70, -60, 110, 0, 108);
      island.bezierCurveTo(70, 106, 165, 65, 150, 5);
      island.bezierCurveTo(150, -6, -150, -6, -150, 10);
      island.endFill();

      island.beginFill(COLORS.islandTop);
      island.moveTo(-150, 6);
      island.bezierCurveTo(-155, -30, -80, -46, 0, -46);
      island.bezierCurveTo(85, -46, 158, -28, 150, 6);
      island.bezierCurveTo(150, 16, -150, 16, -150, 6);
      island.endFill();

      island.beginFill(COLORS.islandTopLight, 0.55);
      island.drawEllipse(-30, -30, 70, 14);
      island.endFill();

      island.filters = [new PIXI.DropShadowFilter
        ? new PIXI.filters.DropShadowFilter({ blur: 6, distance: 12, alpha: 0.35, rotation: 90 })
        : null].filter(Boolean);

      this.islandRoot.addChild(island);
      this.island = island;
      this.worldRoot.addChild(this.islandRoot);
    }

    // ----------------------------------------------------------- house --
    _buildHouse() {
      const house = new PIXI.Container();

      const wall = new PIXI.Graphics();
      wall.beginFill(COLORS.houseWall);
      wall.drawRoundedRect(-26, -6, 52, 40, 3);
      wall.endFill();
      house.addChild(wall);

      const roof = new PIXI.Graphics();
      roof.beginFill(COLORS.houseRoof);
      roof.moveTo(-34, -6);
      roof.lineTo(0, -38);
      roof.lineTo(34, -6);
      roof.lineTo(-34, -6);
      roof.endFill();
      house.addChild(roof);

      const door = new PIXI.Graphics();
      door.beginFill(COLORS.houseDoor);
      door.drawRoundedRect(-7, 14, 14, 20, 2);
      door.endFill();
      house.addChild(door);

      const window1 = new PIXI.Graphics();
      window1.beginFill(COLORS.sun, 0.85);
      window1.drawRoundedRect(-20, 2, 10, 10, 2);
      window1.drawRoundedRect(10, 2, 10, 10, 2);
      window1.endFill();
      house.addChild(window1);

      house.y = -46; // assenta em cima do topo da ilha
      this.islandRoot.addChild(house);
      this.house = house;
    }

    // ------------------------------------------------------------ tick --
    _tick(delta) {
      this.time += delta;

      // estrelas piscando
      for (const s of this.starData) {
        s.g.alpha =
          s.baseAlpha * (0.6 + 0.4 * Math.sin(this.time * 0.02 * s.speed + s.phase));
      }

      // nuvens deslizando devagar (com wrap na largura da tela)
      const w = this.app.renderer.width / this.app.renderer.resolution;
      for (const c of this.cloudData) {
        c.g.x += (c.speed * delta) / 60;
        const half = 90;
        if (c.g.x > w + half) c.g.x = -half;
        if (c.g.x < -half) c.g.x = w + half;
      }

      // ilha flutuando suavemente (bob) + leve giro
      const bob = Math.sin(this.time * 0.02) * 6;
      this.islandRoot.y = this._baseIslandY + bob;
      this.islandRoot.rotation = Math.sin(this.time * 0.012) * 0.01;
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
