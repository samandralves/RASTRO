/* RASTRO — céu animado: estrelas fixas + estrelas cadentes em canvas */

(function () {
  const canvas = document.getElementById("starfield");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let W, H, DPR;
  let stars = [];
  let shootingStars = [];

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    initStars();
  }

  function initStars() {
    const count = Math.floor((W * H) / 9000);
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.3 + 0.3,
      baseAlpha: Math.random() * 0.5 + 0.3,
      twinkleSpeed: Math.random() * 0.015 + 0.005,
      phase: Math.random() * Math.PI * 2,
    }));
  }

  function spawnShootingStar() {
    // entra por cima/esquerda, cruza na diagonal
    const startX = Math.random() * W * 0.6;
    const startY = -20;
    const angle = (Math.random() * 18 + 28) * (Math.PI / 180); // 28–46 graus
    const speed = Math.random() * 5 + 7;
    const len = Math.random() * 90 + 90;

    const colors = [
      { r: 255, g: 255, b: 255 },
      { r: 121, g: 224, b: 191 }, // verde-menta (brand)
      { r: 184, g: 166, b: 239 }, // lilás (dusk)
    ];
    const color = colors[Math.floor(Math.random() * colors.length)];

    shootingStars.push({
      x: startX,
      y: startY,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      len,
      life: 1,
      decay: Math.random() * 0.006 + 0.006,
      color,
      width: Math.random() * 1.2 + 1,
    });
  }

  let lastSpawn = 0;
  function maybeSpawn(t) {
    if (reduceMotion) return;
    if (t - lastSpawn > (Math.random() * 2200 + 1400)) {
      spawnShootingStar();
      lastSpawn = t;
    }
  }

  function draw(t) {
    ctx.clearRect(0, 0, W, H);

    // estrelas fixas, com leve cintilar
    for (const s of stars) {
      const tw = reduceMotion ? 0 : Math.sin(t * s.twinkleSpeed + s.phase) * 0.25;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${Math.max(0, s.baseAlpha + tw)})`;
      ctx.fill();
    }

    // estrelas cadentes
    for (let i = shootingStars.length - 1; i >= 0; i--) {
      const c = shootingStars[i];
      c.x += c.vx;
      c.y += c.vy;
      c.life -= c.decay;

      if (c.life <= 0 || c.x > W + 100 || c.y > H + 100) {
        shootingStars.splice(i, 1);
        continue;
      }

      const dirX = c.vx / Math.hypot(c.vx, c.vy);
      const dirY = c.vy / Math.hypot(c.vx, c.vy);
      const tailX = c.x - dirX * c.len;
      const tailY = c.y - dirY * c.len;

      const grad = ctx.createLinearGradient(c.x, c.y, tailX, tailY);
      const { r, g, b } = c.color;
      grad.addColorStop(0, `rgba(${r},${g},${b},${c.life})`);
      grad.addColorStop(1, `rgba(${r},${g},${b},0)`);

      ctx.beginPath();
      ctx.strokeStyle = grad;
      ctx.lineWidth = c.width;
      ctx.lineCap = "round";
      ctx.moveTo(c.x, c.y);
      ctx.lineTo(tailX, tailY);
      ctx.stroke();

      // núcleo brilhante
      ctx.beginPath();
      ctx.arc(c.x, c.y, c.width * 1.4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${r},${g},${b},${c.life})`;
      ctx.shadowColor = `rgba(${r},${g},${b},0.9)`;
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    maybeSpawn(t);
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(draw);
})();