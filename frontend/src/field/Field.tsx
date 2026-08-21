import { useEffect, useRef } from "react";
import { fieldBus } from "./bus";
import "./field.css";

type Dot = { x: number; y: number; r: number; a: number; phase: number };
type Wave = { x: number; y: number; t0: number; dur: number; maxR: number };

function bezierEase(t: number): number {
  // cubic-bezier(0.16, 1, 0.3, 1)
  const cy = 3 * 1;
  const by = 3 * (1 - 1) - cy;
  const ay = 1 - cy - by;
  return ((ay * t + by) * t + cy) * t;
}

function seedDots(w: number, h: number): Dot[] {
  const target = Math.min(Math.max(Math.floor((w * h) / 11000), 48), 180);
  const dots: Dot[] = [];
  const minD = 18;
  let guard = 0;
  while (dots.length < target && guard < target * 18) {
    guard += 1;
    const x = Math.random() * w;
    const y = Math.random() * h;
    if (dots.some((d) => (d.x - x) ** 2 + (d.y - y) ** 2 < minD * minD)) continue;
    dots.push({
      x,
      y,
      r: 1 + Math.random() * 0.6,
      a: 0.06 + Math.random() * 0.06,
      phase: Math.random() * Math.PI * 2,
    });
  }
  return dots;
}

export function Field() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const node = ref.current;
    const gfx = node?.getContext("2d") ?? null;
    if (!node || !gfx) return;
    const canvas: HTMLCanvasElement = node;
    const ctx: CanvasRenderingContext2D = gfx;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let w = 0;
    let h = 0;
    let dots: Dot[] = [];
    const waves: Wave[] = [];
    let raf = 0;
    let alive = true;

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dots = seedDots(w, h);
    }

    function drawDots(t: number) {
      ctx.clearRect(0, 0, w, h);
      for (const d of dots) {
        const drift = reduce.matches ? 0 : Math.sin(t / 40000 + d.phase) * 0.45;
        ctx.beginPath();
        ctx.fillStyle = `rgba(216, 214, 208, ${d.a})`;
        ctx.arc(d.x + drift, d.y + drift * 0.4, d.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function drawWaves(now: number) {
      for (let i = waves.length - 1; i >= 0; i -= 1) {
        const wave = waves[i];
        if (!wave) continue;
        const t = (now - wave.t0) / wave.dur;
        if (t >= 1) {
          waves.splice(i, 1);
          continue;
        }
        const e = bezierEase(Math.min(Math.max(t, 0), 1));
        const r = 24 + e * wave.maxR;
        const alpha = (1 - t) * 0.28;
        ctx.beginPath();
        ctx.strokeStyle = `rgba(201, 208, 196, ${alpha})`;
        ctx.lineWidth = 0.5 + (1 - t) * 0.5;
        ctx.arc(wave.x, wave.y, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    function frame(now: number) {
      if (!alive) return;
      drawDots(now);
      if (!reduce.matches) drawWaves(now);
      raf = requestAnimationFrame(frame);
    }

    function onWave(ev: Event) {
      if (reduce.matches) return;
      const detail = (ev as CustomEvent<{ x?: number; y?: number }>).detail;
      if (waves.length >= 2) waves.shift();
      waves.push({
        x: detail?.x ?? w * 0.5,
        y: detail?.y ?? h * 0.48,
        t0: performance.now(),
        dur: 1400 + Math.random() * 1200,
        maxR: Math.min(w, h) * (0.22 + Math.random() * 0.12),
      });
    }

    resize();
    if (reduce.matches) {
      drawDots(0);
    } else {
      raf = requestAnimationFrame(frame);
    }

    fieldBus.addEventListener("wave", onWave);
    window.addEventListener("resize", resize);
    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      fieldBus.removeEventListener("wave", onWave);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={ref} className="field" aria-hidden="true" />;
}
