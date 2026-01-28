const video = document.getElementById("camera");
const postureEl = document.getElementById("posture");
const scoreEl = document.getElementById("score");
const messageEl = document.getElementById("message");
const startBtn = document.getElementById("startBtn");
const toggleBtn = document.getElementById("toggleCameraBtn");
const privacyBtn = document.getElementById("privacyBtn");
const cameraBox = document.querySelector(".camera-box");


let stream = null;
let cameraOn = false;
let streaming = false;
let intervalId = null;
let privacyOn = true;



// 初期状態
startBtn.style.display = "none";

/* =========================
    カメラ起動
========================= */
async function startCamera() {
    requestNotificationPermission();

    stream = await navigator.mediaDevices.getUserMedia({
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 }
        },
        audio: false
    });

    video.srcObject = stream;

    // 🔥 ここが超重要
    video.onloadedmetadata = () => {
        video.play();

        const w = video.videoWidth;
        const h = video.videoHeight;

        // video要素を実解像度比率に合わせる
        video.style.width = "100%";
        video.style.height = "auto";
        video.parentElement.style.aspectRatio = `${w} / ${h}`;

        console.log(`Camera resolution: ${w} x ${h}`);
    };

    cameraOn = true;
}

/* =========================
    カメラ ON / OFF
========================= */
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

        startBtn.style.display = "none";
        toggleBtn.textContent = "カメラをオン";
        cameraOn = false;

    } else {
        // --- ON ---
        try {
            await startCamera();
            startBtn.style.display = "block";
            toggleBtn.textContent = "カメラをオフ";
        } catch (err) {
            console.error("カメラを開けませんでした:", err);
        }
    }
});

/* =========================
    プライバシーモード切替
========================= */
privacyBtn.addEventListener("click", () => {
    privacyOn = !privacyOn;

    if (privacyOn) {
        cameraBox.classList.add("privacy");
        privacyBtn.textContent = "プライバシーモード ON";
    } else {
        cameraBox.classList.remove("privacy");
        privacyBtn.textContent = "プライバシーモード OFF";
    }
});


/* =========================
    フレーム送信
========================= */
async function sendFrame(url) {
    if (!cameraOn || !video.srcObject) {
        return { posture: "unknown" };
    }

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
    if (!("Notification" in window)) return;
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
    if (now - lastNotify < 10000) return;
    lastNotify = now;

    new Notification("Posture Guard AI", {
        body: message,
        icon: "/static/models/favicon.ico"
    });
}

/* =========================
    UI更新
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
    計測 / キャリブレーション
========================= */
startBtn.onclick = async () => {
    if (!cameraOn) return;

    if (!streaming) {
        streaming = true;
        startBtn.textContent = "キャリブレーション";

        intervalId = setInterval(async () => {
            if (!cameraOn) return;
            const data = await sendFrame("/analyze");
            updateUI(data);
        }, 1000);

    } else {
        // --- キャリブレーション ---
        messageEl.textContent = "正しい姿勢を保存中…";

        const data = await sendFrame("/calibrate");

        messageEl.textContent =
            data.status === "calibrated"
                ? "キャリブレーション完了 ✅"
                : "キャリブレーション失敗 ❌";
    }
};

window.addEventListener("DOMContentLoaded", () => {
    privacyOn = true;
    cameraBox.classList.add("privacy");
    privacyBtn.textContent = "プライバシーモード ON";
});