import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.150.0/build/three.module.js";
import { GLTFLoader } from "https://cdn.jsdelivr.net/npm/three@0.150.0/examples/jsm/loaders/GLTFLoader.js";
import { VRM } from "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@2.0.0/lib/three-vrm.module.js";

console.log("vrm.js loaded");

let scene, camera, renderer, vrm;

window.onload = () => {
  console.log("AUTO START");
  init();   // ← ★ これが無かった
};

function init() {
  // --- scene ---
  scene = new THREE.Scene();

  // --- camera ---
  camera = new THREE.PerspectiveCamera(
    45,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
  camera.position.set(0, 1.4, 2);

  // --- renderer ---
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  // --- light ---
  const light = new THREE.DirectionalLight(0xffffff, 1);
  light.position.set(1, 1, 1);
  scene.add(light);

  // --- VRM load ---
  const loader = new GLTFLoader();
  loader.load(
    "/static/models/sample.vrm",
    (gltf) => {
      VRM.from(gltf).then((v) => {
        vrm = v;
        scene.add(vrm.scene);
        animate();
      });
    },
    undefined,
    (err) => {
      console.error("VRM load error", err);
    }
  );
}

function animate() {
  requestAnimationFrame(animate);
  if (vrm) vrm.update(1 / 60);
  renderer.render(scene, camera);
}
