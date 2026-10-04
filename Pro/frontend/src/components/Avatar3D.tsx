import { Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils, type VRM } from "@pixiv/three-vrm";
import type { MutableRefObject } from "react";
import { useLipSync } from "../hooks/useLipSync";

function hasWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl") || c.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function AvatarScene({
  vrmRef,
  analyserRef,
  playing,
  mood,
}: {
  vrmRef: MutableRefObject<VRM | null>;
  analyserRef: MutableRefObject<AnalyserNode | null>;
  playing: boolean;
  mood: "idle" | "think" | "speak" | "listen";
}) {
  const [vrm, setVrm] = useState<VRM | null>(null);
  const [loadError, setLoadError] = useState(false);
  const blink = useRef(0);

  useEffect(() => {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    let cancelled = false;
    loader.load(
      "/models/avatar.vrm",
      (gltf) => {
        if (cancelled) return;
        const loaded = gltf.userData.vrm as VRM;
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.rotateVRM0(loaded);
        loaded.scene.traverse((obj) => {
          obj.frustumCulled = false;
        });
        vrmRef.current = loaded;
        setVrm(loaded);
      },
      undefined,
      () => setLoadError(true)
    );
    return () => {
      cancelled = true;
      vrmRef.current = null;
    };
  }, [vrmRef]);

  useLipSync(vrmRef, analyserRef, true, playing);

  useFrame((_, delta) => {
    const current = vrmRef.current;
    if (!current) return;
    blink.current += delta;
    if (blink.current > 3.2) {
      blink.current = 0;
      current.expressionManager?.setValue("blink", 1);
      window.setTimeout(() => current.expressionManager?.setValue("blink", 0), 120);
    }
    const t = performance.now() / 1000;
    const head = current.humanoid?.getNormalizedBoneNode("head");
    if (head) {
      head.rotation.y = Math.sin(t * 0.6) * 0.04;
      head.rotation.x = Math.sin(t * 1.1) * 0.02 + (mood === "think" ? 0.05 : 0);
    }
    current.update(delta);
  });

  if (loadError) {
    return (
      <mesh position={[0, 1.2, 0]}>
        <sphereGeometry args={[0.35, 24, 24]} />
        <meshStandardMaterial color="#6b8f71" />
      </mesh>
    );
  }

  return vrm ? <primitive object={vrm.scene} /> : null;
}

interface Props {
  analyserRef: MutableRefObject<AnalyserNode | null>;
  playing: boolean;
  mood: "idle" | "think" | "speak" | "listen";
}

export function Avatar3D({ analyserRef, playing, mood }: Props) {
  const vrmRef = useRef<VRM | null>(null);
  const [webgl, setWebgl] = useState(true);

  useEffect(() => {
    setWebgl(hasWebGL());
  }, []);

  if (!webgl) {
    return (
      <div className="avatar-fallback">
        Thiết bị không hỗ trợ WebGL — đã ẩn nhân vật 3D.
      </div>
    );
  }

  return (
    <div className="avatar-wrap">
      <Canvas camera={{ position: [0, 1.4, 1.6], fov: 28 }} shadows={false}>
        <color attach="background" args={["#e7efe8"]} />
        <ambientLight intensity={0.85} />
        <directionalLight position={[1.5, 2.5, 2]} intensity={1.1} />
        <Suspense fallback={null}>
          <AvatarScene
            vrmRef={vrmRef}
            analyserRef={analyserRef}
            playing={playing}
            mood={mood}
          />
        </Suspense>
        <OrbitControls enablePan={false} enableZoom={false} target={[0, 1.35, 0]} />
      </Canvas>
      <p className="avatar-hint">
        Đặt file VRM tại <code>frontend/public/models/avatar.vrm</code>
      </p>
    </div>
  );
}
