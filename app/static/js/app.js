const video = document.getElementById("camera");
const postureEl = document.getElementById("posture");
const scoreEl = document.getElementById("score");
const messageEl = document.getElementById("message");
const startBtn = document.getElementById("startBtn");

let streaming = false;
let intervalId = null;

/* =========================
    カメラ起動
========================= */
async function startCamera() {
    requestNotificationPermission(); // ←追加
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
    });
    video.srcObject = stream;
}


/* =========================
    フレームを Flask に送信
========================= */
async function sendFrame(url) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    const blob = await new Promise(resolve =>
        canvas.toBlob(resolve, "image/jpeg", 0.8)
    );

    const formData = new FormData();
    formData.append("image", blob, "frame.jpg");

    const res = await fetch(url, {
        method: "POST",
        body: formData
    });

    return res.json();
}

/* =========================
    通知許可
========================= */
function requestNotificationPermission() {
    if (!("Notification" in window)) {
        console.log("このブラウザは通知に対応していません");
        return;
    }

    if (Notification.permission === "default") {
        Notification.requestPermission();
    }
}


/* =========================
    Web通知
========================= */
let lastNotify = 0;

function notifyPosture(message) {
    if (Notification.permission !== "granted") return;

    const now = Date.now();

    // 連続通知防止（10秒に1回）
    if (now - lastNotify < 10000) return;
    lastNotify = now;

    new Notification("Posture Guard AI", {
        body: message,
        icon: "/static/icon.png" // あれば
    });
}



/* =========================
    姿勢表示更新
========================= */
function updateUI(data) {
    if (data.posture === "unknown") {
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

        // 🔔 通知
        notifyPosture("姿勢が崩れています。気をつけてください！");
    }

    if (data.metrics) {
        scoreEl.textContent =
            `Torso:${Math.floor(data.metrics.torso_angle)}  ` +
            `Neck:${Math.floor(data.metrics.neck_angle)}  ` +
            `Tilt:${Math.floor(data.metrics.shoulder_tilt)}`;
    }
}

/* =========================
    計測開始
========================= */
startBtn.onclick = async () => {
    if (!streaming) {
        await startCamera();
        streaming = true;
        startBtn.textContent = "キャリブレーション";

        intervalId = setInterval(async () => {
            const data = await sendFrame("/analyze");
            updateUI(data);
        }, 1000);
    } else {
    // キャリブレーション
    messageEl.textContent = "正しい姿勢を保存中…";

    const data = await sendFrame("/calibrate");

    if (data.status === "calibrated") {
        messageEl.textContent = "キャリブレーション完了 ✅";
    } else {
        messageEl.textContent = "キャリブレーション失敗 ❌";
    }
    }
};
