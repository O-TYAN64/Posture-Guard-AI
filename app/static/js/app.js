// =========================
// DOM（HTMLに合わせたID）
// =========================
const video       = document.getElementById("camera");
const postureEl   = document.getElementById("posture");
const scoreEl     = document.getElementById("score");
const messageEl   = document.getElementById("message");
const msgEl       = document.getElementById("msg");
const startBtn    = document.getElementById("startBtn");
const toggleBtn   = document.getElementById("toggleCameraBtn");
const privacyBtn  = document.getElementById("privacyBtn");
const skeletonBtn = document.getElementById("skeletonBtn");
const clearBtn    = document.getElementById("clearBtn");
const cameraBox   = document.querySelector(".camera-box");
const cameraIcon  = toggleBtn.querySelector("img");
const cameraText  = toggleBtn.querySelector("span");
const privacyIcon = privacyBtn.querySelector("img");
const privacyText = privacyBtn.querySelector("span");
const startIcon = startBtn.querySelector("img");
const startText = startBtn.querySelector("span");


// =========================
// 状態
// =========================
let stream        = null;
let cameraOn      = false;
let streaming     = false;
let intervalId    = null;
let privacyOn     = true;

// ---- 骨格オーバーレイ ----
let overlay       = null;   // JSで自動生成
let ctx           = null;
let skeletonOn    = false;

// ポーリング周期（骨格ONで高速化）
let POLL_INTERVAL_MS = 1000;
const POLL_SLOW_MS   = 1000;
const POLL_FAST_MS   = 200;

// 代表的な接続（サーバー応答の connections を優先利用。無い場合のフォールバック）
const DEFAULT_POSE_EDGES = [
  [11,13],[13,15], [12,14],[14,16],     // 腕
  [11,12], [11,23],[12,24], [23,24],    // 肩帯〜体幹
  [23,25],[25,27], [24,26],[26,28],     // 脚
  [27,29],[29,31], [28,30],[30,32],     // 足
  [0,11],[0,12]                          // 鼻〜肩（簡易首）
];

// デバッグトグル
const DEBUG = true;
const log   = (...a) => DEBUG && console.log("[PG]", ...a);

// =========================
// 初期化
// =========================
startBtn.style.display = "none";
updatePrivacyUI(true); // 初期＝プライバシーON

// =========================
// ユーティリティ
// =========================
function ensureOverlay() {
  if (!overlay) {
    overlay = document.createElement("canvas");
    overlay.id = "overlay";
    Object.assign(overlay.style, {
      position: "absolute",
      inset: "0",
      width: "100%",
      height: "100%",
      pointerEvents: "none",
      zIndex: "1",
    });
    // video の直上に重ねる：video の親要素に追加
    const parent = video.parentElement;
    if (getComputedStyle(parent).position === "static") {
      parent.style.position = "relative";
    }
    // 念のため video を背面へ
    video.style.zIndex = "0";
    parent.appendChild(overlay);
  }
  ctx = overlay.getContext("2d");
}

function fitCanvasToVideo() {
  if (!overlay) return;
  const w = video.videoWidth;
  const h = video.videoHeight;
  if (w && h) {
    overlay.width  = w;
    overlay.height = h;
    return true;
  }
  return false;
}

function clearOverlay() {
  if (!ctx || !overlay) return;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
}

function updatePrivacyUI(isOn) {
  privacyOn = isOn;
  if (isOn) {
    cameraBox.classList.add("privacy");
    privacyIcon.src = "/static/models/privacy-on.svg";
    privacyText.textContent = "Privacy ON";
    clearOverlay();
  } else {
    cameraBox.classList.remove("privacy");
    privacyIcon.src = "/static/models/privacy-off.svg";
    privacyText.textContent = "Privacy OFF";
  }
}


function restartStreamingLoop() {
  if (!streaming) return;
  clearInterval(intervalId);
  intervalId = setInterval(async () => {
    if (!cameraOn) return;
    const data = await sendFrame("/analyze");
    updateUI(data);

    // 骨格描画（プライバシーOFF かつ 骨格ON）
    const canDraw = !privacyOn && skeletonOn && data && Array.isArray(data.landmarks);
    if (canDraw) {
      ensureOverlay();
      // canvas サイズ未確定（videoWidth=0）時のリトライ
      if (!fitCanvasToVideo()) {
        setTimeout(() => {
          fitCanvasToVideo();
          drawSkeletonFromServer(data.landmarks, data.connections, data.posture);
        }, 50);
      } else {
        drawSkeletonFromServer(data.landmarks, data.connections, data.posture);
      }
    } else {
      clearOverlay();
      if (DEBUG) {
        log("skip draw:", { privacyOn, skeletonOn, hasLm: !!(data && data.landmarks) });
      }
    }
  }, POLL_INTERVAL_MS);
}

// =========================
// カメラ起動
// =========================
async function startCamera() {
  requestNotificationPermission();

  stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 } },
    audio: false
  });

  video.srcObject = stream;

  video.onloadedmetadata = () => {
    video.play();

    // 見た目サイズを実比率に
    const w = video.videoWidth;
    const h = video.videoHeight;
    video.style.width = "100%";
    video.style.height = "auto";
    const parent = video.parentElement;
    parent.style.position = "relative";
    parent.style.aspectRatio = `${w} / ${h}`;

    ensureOverlay();
    fitCanvasToVideo();

    log(`Camera resolution: ${w} x ${h}`);
  };

  cameraOn = true;
}

// =========================
// カメラ ON / OFF
// =========================
toggleBtn.addEventListener("click", async () => {
  if (cameraOn) {
    // --- OFF ---
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
    video.srcObject = null;

    postureEl.textContent = "OFF";
    messageEl.textContent = "カメラはオフです";
    scoreEl.textContent = "-";

    streaming = false;

    startBtn.style.display = "none";
    cameraIcon.src = "/static/models/camera-on.svg";
    cameraText.textContent = "Camera ON";
    cameraOn = false;

    // 計測ループも停止
    if (streaming) {
      clearInterval(intervalId);
      streaming = false;
      startBtn.textContent = "計測開始";
    }
  } else {
    // --- ON ---
    try {
      await startCamera();
      
      startBtn.style.display = "inline-block";
      cameraIcon.src = "/static/models/camera-off.svg";
      cameraText.textContent = "Camera OFF";
      // 骨格ON かつ プライバシーOFF なら、計測が未開始でも案内
      if (skeletonOn && !streaming) {
        msgEl.textContent = "骨格表示には『計測開始』が必要です";
      }
    } catch (err) {
      console.error("カメラを開けませんでした:", err);
      setTimeout(() => {
          msgEl.textContent = "カメラを開けませんでした。設定や権限を確認してください。";
          alert("カメラを開けませんでした。設定や権限を確認してください。");
      }, 300);
        
    }
  }
});

// =========================
// プライバシーモード切替
// OFF → 骨格描画可能、ON → 骨格抑止
// =========================
privacyBtn.addEventListener("click", async () => {
  const next = !privacyOn;
  updatePrivacyUI(next);
  if (privacyOn) {
    // ON：描画は消す
    clearOverlay();
  } else {
    // OFF：カメラがON & 骨格ON & 計測中なら直ちに描画が走る（ループに任せる）
    if (cameraOn && skeletonOn && streaming) {
      ensureOverlay();
      fitCanvasToVideo();
    }
  }
});


// =========================
// 計測 / キャリブレーション
// =========================
startBtn.onclick = async () => {
  if (!cameraOn) return;

  if (!streaming) {
    // ===== 計測開始 =====
    streaming = true;

    // startIcon.src = "/static/models/calibrate.svg";
    startText.textContent = "キャリブレーション";

    POLL_INTERVAL_MS = skeletonOn ? POLL_FAST_MS : POLL_SLOW_MS;
    restartStreamingLoop();

  } else {
    // ===== キャリブレーション =====
    messageEl.textContent = "正しい姿勢を保存中…";

    startIcon.src = "/static/models/loading.svg";
    startText.textContent = "保存中…";

    const data = await sendFrame("/calibrate");

    messageEl.textContent =
      data.status === "calibrated"
        ? "キャリブレーション完了 ✅"
        : "キャリブレーション失敗 ❌";

    // 戻す
    // startIcon.src = "/static/models/calibrate.svg";
    startText.textContent = "キャリブレーション";
  }
};

// =========================
// 1フレーム送信（静止画のみ送る）
// =========================
async function sendFrame(url) {
  if (!cameraOn || !video.srcObject) {
    return { posture: "unknown" };
  }

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const c = canvas.getContext("2d");
  c.drawImage(video, 0, 0);

  const blob = await new Promise(resolve =>
    canvas.toBlob(resolve, "image/jpeg", 0.8)
  );

  const formData = new FormData();
  formData.append("image", blob, "frame.jpg");

  try {
    const res = await fetch(url, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    log("sendFrame error:", e);
    return { posture: "unknown" };
  }
}

// =========================
// UI更新（姿勢結果）
// =========================
function updateUI(data) {
  if (!data || data.posture === "unknown") {
    postureEl.textContent = "UNKNOWN";
    postureEl.className = "posture";
    messageEl.textContent = "姿勢を検出できません";
    return;
  }

  postureEl.textContent = data.posture.toUpperCase();
  postureEl.className = "posture " + data.posture;

  if (data.posture === "good") {
    messageEl.textContent = "良い姿勢です 👍";
  } else {
    messageEl.textContent = "姿勢が崩れています ⚠️";
    notifyPosture("姿勢が崩れています。気をつけてください！");
  }

  if (data.metrics) {
    scoreEl.textContent =
      `Torso:${Math.floor(data.metrics.torso_angle)}  ` +
      `Neck:${Math.floor(data.metrics.neck_angle)}  ` +
      `Tilt:${Math.floor(data.metrics.shoulder_tilt)}`;
  }
}

// =========================
// サーバー返却のランドマークを描画
// landmarks: [{x,y,z,visibility,presence}...] (x,yは0..1)
// connections: [[a,b], ...]
// posture: "good"|"bad" → 色分け
// =========================
function drawSkeletonFromServer(landmarks, connections, posture) {
  if (!overlay || !ctx || !landmarks || landmarks.length === 0) return;

  // overlay のサイズが0だと見えない
  if (!overlay.width || !overlay.height) {
    log("overlay size 0 → fit & retry");
    fitCanvasToVideo();
  }

  clearOverlay();
  const W = overlay.width, H = overlay.height;
  const edges = (connections && connections.length) ? connections : DEFAULT_POSE_EDGES;

  // 色分け（姿勢が悪いと赤）
  const stroke = posture === "bad" ? "rgba(255,80,80,0.95)" : "rgba(0,200,255,0.9)";
  const fill   = posture === "bad" ? "#FFA500" : "#00FF7F";

  // 接続線
  ctx.lineWidth = 3;
  ctx.strokeStyle = stroke;
  edges.forEach(([a,b]) => {
    const pa = landmarks[a], pb = landmarks[b];
    if (!pa || !pb) return;
    ctx.beginPath();
    ctx.moveTo(pa.x * W, pa.y * H);
    ctx.lineTo(pb.x * W, pb.y * H);
    ctx.stroke();
  });

  // ランドマーク点
  ctx.fillStyle = fill;
  for (const p of landmarks) {
    ctx.beginPath();
    ctx.arc(p.x * W, p.y * H, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  if (DEBUG) {

  }
}

// =========================
// 通知
// =========================
function requestNotificationPermission() {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    Notification.requestPermission();
  }
}

let lastNotify = 0;
function notifyPosture(message) {
  if (Notification.permission !== "granted") return;
  const now = Date.now();
  if (now - lastNotify < 10000) return;
  lastNotify = now;

  new Notification("Posture Guard AI", {
    body: message,
    icon: "/static/models/favicon.ico"
  });
}

// =========================
// 画面サイズ変化
// =========================
window.addEventListener("resize", () => {
  if (video.videoWidth) fitCanvasToVideo();
});


// =========================
// 起動時の初期表示
// =========================
window.addEventListener("DOMContentLoaded", () => {
  updatePrivacyUI(true);
  postureEl.textContent = "OFF";
  messageEl.textContent = "カメラはオフです";
  scoreEl.textContent = "-";

  cameraIcon.src = "/static/models/camera-on.svg";
  cameraText.textContent = "Camera ON";
});




