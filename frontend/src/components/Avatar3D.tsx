import { useEffect, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import type { AvatarState, VisemeFrame } from "../types";
import { visemeAt } from "../lib/viseme";

type Props = {
  state: AvatarState;
  playingRef: MutableRefObject<boolean>;
  timelineRef: MutableRefObject<VisemeFrame[]>;
  clock0Ref: MutableRefObject<number>;
  onMouthInfo: (info: string) => void;
};

export function Avatar3D({ state, playingRef, timelineRef, clock0Ref, onMouthInfo }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  const onMouthRef = useRef(onMouthInfo);
  stateRef.current = state;
  onMouthRef.current = onMouthInfo;

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;

    const R = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
    const sc = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
    cam.position.set(0, 1.45, 5.2);
    cam.lookAt(0, 1.3, 0);
    sc.add(new THREE.HemisphereLight(0xffffff, 0x8899bb, 0.9));
    const dl = new THREE.DirectionalLight(0xffffff, 0.8);
    dl.position.set(2, 3, 4);
    sc.add(dl);

    const mat = (c: number) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.7 });
    const av = new THREE.Group();
    sc.add(av);
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.85, 1.3, 32), mat(0x2f6df6));
    body.position.y = -0.1;
    av.add(body);
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.2, 0.3, 16), mat(0xf2c9a5));
    neck.position.y = 0.6;
    av.add(neck);
    const head = new THREE.Group();
    head.position.y = 1.35;
    av.add(head);
    head.add(new THREE.Mesh(new THREE.SphereGeometry(0.75, 40, 32), mat(0xf6d3b3)));
    const hair = new THREE.Mesh(
      new THREE.SphereGeometry(0.8, 40, 32, 0, Math.PI * 2, 0, Math.PI * 0.55),
      mat(0x2b2230),
    );
    hair.position.set(0, 0.06, -0.03);
    hair.rotation.x = -0.25;
    head.add(hair);
    const eyes = [-1, 1].map((s) => {
      const g = new THREE.Group();
      g.position.set(s * 0.27, 0.1, 0.64);
      g.add(new THREE.Mesh(new THREE.SphereGeometry(0.1, 20, 16), mat(0x1a1a24)));
      head.add(g);
      return g;
    });
    const brow = [-1, 1].map((s) => {
      const b = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.03, 0.04), mat(0x2b2230));
      b.position.set(s * 0.27, 0.27, 0.68);
      head.add(b);
      return b;
    });
    [-1, 1].forEach((s) => {
      const c = new THREE.Mesh(
        new THREE.SphereGeometry(0.09, 16, 12),
        new THREE.MeshStandardMaterial({ color: 0xff9a9a, transparent: true, opacity: 0.5 }),
      );
      c.scale.set(1, 0.6, 0.3);
      c.position.set(s * 0.43, -0.12, 0.58);
      head.add(c);
    });
    const mouth = new THREE.Mesh(new THREE.SphereGeometry(0.12, 24, 16), mat(0x8a2a3a));
    mouth.position.set(0, -0.28, 0.66);
    mouth.scale.set(1, 0.12, 0.4);
    head.add(mouth);

    const size = () => {
      const w = cv.clientWidth;
      const h = cv.clientHeight;
      R.setSize(w, h, false);
      R.setPixelRatio(Math.min(devicePixelRatio, 2));
      cam.aspect = w / h;
      cam.updateProjectionMatrix();
    };
    size();
    addEventListener("resize", size);

    let mo = 0.12;
    let mw = 1;
    let nextBlink = 2;
    let blink = 0;
    let lastMouth = "";
    const clk = new THREE.Clock();
    let raf = 0;

    const frame = () => {
      raf = requestAnimationFrame(frame);
      const t = clk.getElapsedTime();
      let target = { o: 0.1, w: 1 };
      let nm = "nghỉ";
      if (playingRef.current) {
        const v = visemeAt(timelineRef.current, (performance.now() - clock0Ref.current) / 1000);
        if (v) {
          target = v;
          nm = v.name || "đóng";
        }
      }
      mo += (target.o - mo) * 0.45;
      mw += (target.w - mw) * 0.4;
      mouth.scale.set(mw, 0.1 + mo * 0.9, 0.4);
      mouth.position.y = -0.28 - mo * 0.03;
      const info = playingRef.current ? "Viseme: " + nm : "";
      if (info !== lastMouth) {
        lastMouth = info;
        onMouthRef.current(info);
      }

      const sway = Math.sin(t * 1.2) * 0.04;
      let ry = sway;
      let rx = 0;
      const st = stateRef.current;
      if (st === "Nghe") rx = 0.12 + Math.sin(t * 2) * 0.02;
      if (st === "Nghĩ") {
        ry = Math.sin(t * 1.5) * 0.18;
        rx = -0.12;
      }
      if (st === "Nói") {
        ry = Math.sin(t * 2.2) * 0.07;
        rx = Math.sin(t * 3) * 0.03;
      }
      head.rotation.y += (ry - head.rotation.y) * 0.1;
      head.rotation.x += (rx - head.rotation.x) * 0.1;
      av.position.y = Math.sin(t * 1.6) * 0.015;
      if (t > nextBlink) {
        blink = 1;
        nextBlink = t + 2 + Math.random() * 3;
      }
      blink = Math.max(0, blink - 0.12);
      const e = 1 - Math.sin(blink * Math.PI) * 0.95;
      eyes.forEach((g) => {
        g.scale.y = Math.max(0.06, e);
      });
      brow.forEach((b) => {
        b.position.y = 0.27 + (st === "Nghĩ" ? 0.05 : 0) + mo * 0.02;
      });
      R.render(sc, cam);
    };
    frame();

    return () => {
      cancelAnimationFrame(raf);
      removeEventListener("resize", size);
      sc.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach((m) => m.dispose());
        }
      });
      R.dispose();
    };
  }, [playingRef, timelineRef, clock0Ref]);

  return <canvas className="avatar-canvas" ref={canvasRef} />;
}
