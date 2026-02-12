from dataclasses import dataclass
import math
import time
import numpy as np
import cv2
import mediapipe as mp
from flask_login import current_user
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from models.posture import PostureLog  # ← これは「関数（モデル取得）」として使う
from extensions import db

# =========================
# Config / Baseline
# =========================

POSE_CONNECTIONS = [
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 12),
    (11, 23), (12, 24),
    (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
    (27, 29), (29, 31),
    (28, 30), (30, 32),
    (0, 11), (0, 12),
]

@dataclass
class PostureConfig:
    torso_angle_thr: float = 8.0
    neck_angle_thr: float = 2.0
    shoulder_tilt_thr: float = 3.0
    ema_alpha: float = 0.23

@dataclass
class PostureBaseline:
    torso_angle: float
    neck_angle: float
    shoulder_tilt: float

# =========================
# EMA
# =========================

class EMA:
    def __init__(self, a: float):
        self.a = a
        self.v = None

    def reset(self):
        self.v = None

    def update(self, x):
        if self.v is None:
            self.v = x
        else:
            self.v = self.a * x + (1 - self.a) * self.v
        return self.v

# =========================
# Utils: 動的モデル取得
# =========================

def get_log_model_for_current_user():
    
    """
    current_user.username から動的な PostureLog モデルクラスを取得する。
    ※ current_user が使えるのはリクエスト中のみ
    """
    if not current_user.is_authenticated:
        raise RuntimeError("User is not authenticated.")

    LogModel = PostureLog(current_user.username)  # ← 動的生成（クラスが返る）

    # 動的テーブル運用の場合、初回だけ create_all が必要になることがある
    # ただし毎フレーム呼ぶのは重いので、必要なら「初回だけ」等の仕組みにすること推奨
    db.create_all()

    return LogModel

# =========================
# Recorder
# =========================

class PostureRecorder:
    def save(self, metrics, judge, posture_type):
        LogModel = get_log_model_for_current_user()

        log = LogModel(
            user_id=current_user.id,
            posture=judge,  # ← judge ではなく posture カラム
            posture_type=posture_type,
            torso_angle=metrics["torso_angle"],
            neck_angle=metrics["neck_angle"],
            shoulder_tilt=metrics["shoulder_tilt"]
        )
        db.session.add(log)
        db.session.commit()

def classify_posture(m, cfg: PostureConfig):
    if abs(m["torso_angle"]) > cfg.torso_angle_thr * 2:
        return "severe_slouch"
    if abs(m["torso_angle"]) > cfg.torso_angle_thr:
        return "slouch"
    if abs(m["neck_angle"]) > cfg.neck_angle_thr:
        return "forward_head"
    if abs(m["shoulder_tilt"]) > cfg.shoulder_tilt_thr:
        return "shoulder_tilt"
    return "normal"

# =========================
# Calibrator
# =========================

class PostureCalibrator:
    def __init__(self):
        self.buf = []

    def add(self, m):
        self.buf.append(m)

    def finish(self):
        if not self.buf:
            raise ValueError("No calibration samples.")
        keys = self.buf[0].keys()
        return {k: float(np.mean([b[k] for b in self.buf])) for k in keys}

# =========================
# Analyzer
# =========================

class PosePostureAnalyzer:
    def __init__(self, model_path: str, cfg: PostureConfig):
        self.cfg = cfg
        self.baseline: PostureBaseline | None = None
        self.recorder = PostureRecorder()

        self._locked_center = None
        self._lock_dist_thr = 0.6

        self.ema_torso = EMA(cfg.ema_alpha)
        self.ema_neck = EMA(cfg.ema_alpha)
        self.ema_tilt = EMA(cfg.ema_alpha)

        self._ts = 0
        self._last = time.perf_counter()

        base = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1
        )
        self.detector = mp_vision.PoseLandmarker.create_from_options(options)

    def reset_ema(self):
        self.ema_torso.reset()
        self.ema_neck.reset()
        self.ema_tilt.reset()
        self._locked_center = None

    def _tick(self):
        now = time.perf_counter()
        dt = max(1, int((now - self._last) * 1000))
        self._last = now
        self._ts += dt

    @staticmethod
    def _angle_from_vertical(v):
        n = np.linalg.norm(v)
        if n < 1e-6:
            return 0.0
        v = v / n
        return math.degrees(math.atan2(v[2], -v[1]))  # Z vs -Y

    @staticmethod
    def _angle_from_horizontal(v):
        return math.degrees(math.atan2(v[1], v[0]))  # Y vs X

    @staticmethod
    def _lm_list_to_dicts(lms):
        out = []
        for lm in lms:
            out.append({
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(getattr(lm, "visibility", 0.0)),
                "presence": float(getattr(lm, "presence", 0.0))
            })
        return out

    def analyze(self, frame_bgr):
        self._tick()

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self.detector.detect_for_video(mp_img, self._ts)

        if not res.pose_world_landmarks:
            self._locked_center = None
            return None

        lm_world = res.pose_world_landmarks[0]
        lm_image = res.pose_landmarks[0] if res.pose_landmarks else None

        NOSE = 0
        L_SH, R_SH = 11, 12
        L_HIP, R_HIP = 23, 24

        p = lambda i: np.array([lm_world[i].x, lm_world[i].y, lm_world[i].z])

        shoulder = (p(L_SH) + p(R_SH)) * 0.5
        hip = (p(L_HIP) + p(R_HIP)) * 0.5
        head = p(NOSE)

        # ---- 人ロック判定 ----
        center = shoulder
        if self._locked_center is None:
            self._locked_center = center
        else:
            dist = np.linalg.norm(center - self._locked_center)
            if dist > self._lock_dist_thr:
                return None
        self._locked_center = center

        # ---- 角度計算 ----
        torso_vec = shoulder - hip
        if np.linalg.norm(torso_vec) < 1e-4:
            return None
        torso_angle = self._angle_from_vertical(torso_vec)

        neck_vec = head - shoulder
        if np.linalg.norm(neck_vec) < 1e-4:
            return None
        neck_angle = self._angle_from_vertical(neck_vec)

        shoulder_vec = p(L_SH) - p(R_SH)
        shoulder_tilt = self._angle_from_horizontal(shoulder_vec)

        # ---- EMA ----
        torso_angle = self.ema_torso.update(torso_angle)
        neck_angle = self.ema_neck.update(neck_angle)
        shoulder_tilt = self.ema_tilt.update(shoulder_tilt)

        metrics = {
            "torso_angle": float(torso_angle),
            "neck_angle": float(neck_angle),
            "shoulder_tilt": float(shoulder_tilt)
        }

        landmarks_2d = self._lm_list_to_dicts(lm_image) if lm_image else None
        landmarks_3d = self._lm_list_to_dicts(lm_world)

        return {
            "metrics": metrics,
            "landmarks": landmarks_2d,
            "world_landmarks": landmarks_3d,
            "connections": POSE_CONNECTIONS,
            "raw_result": res,  # ← 描画したい時用に生のresも返す（任意）
        }

    def calibrate(self, metrics_avg):
        self.reset_ema()
        self.baseline = PostureBaseline(**metrics_avg)

    @staticmethod
    def draw_skeleton_on_frame(frame_bgr, res, landmark_color=(0, 255, 0), connection_color=(0, 200, 255)):
        if not res.pose_landmarks:
            return frame_bgr

        h, w = frame_bgr.shape[:2]
        lm = res.pose_landmarks[0]

        def to_px(pt):
            return int(pt.x * w), int(pt.y * h)

        C = POSE_CONNECTIONS

        for pt in lm:
            x, y = to_px(pt)
            cv2.circle(frame_bgr, (x, y), 3, landmark_color, thickness=-1, lineType=cv2.LINE_AA)

        for a, b in C:
            xa, ya = to_px(lm[a])
            xb, yb = to_px(lm[b])
            cv2.line(frame_bgr, (xa, ya), (xb, yb), connection_color, thickness=2, lineType=cv2.LINE_AA)

        return frame_bgr

    def judge(self, m):
        if self.baseline is None:
            bad = (
                abs(m["torso_angle"]) > self.cfg.torso_angle_thr or
                abs(m["neck_angle"]) > self.cfg.neck_angle_thr or
                abs(m["shoulder_tilt"]) > self.cfg.shoulder_tilt_thr
            )
        else:
            bad = (
                abs(m["torso_angle"] - self.baseline.torso_angle) > self.cfg.torso_angle_thr or
                abs(m["neck_angle"] - self.baseline.neck_angle) > self.cfg.neck_angle_thr or
                abs(m["shoulder_tilt"] - self.baseline.shoulder_tilt) > self.cfg.shoulder_tilt_thr
            )
        return "bad" if bad else "good"

    def analyze_and_save(self, frame_bgr):
        out = self.analyze(frame_bgr)
        if out is None:
            return None

        metrics = out["metrics"]
        judge = self.judge(metrics)

        # 姿勢タイプ判定（例）
        if metrics["neck_angle"] > 15:
            posture_type = "bad_slouch"
        elif metrics["neck_angle"] > 8:
            posture_type = "slouch"
        else:
            posture_type = "normal"

        # 保存（動的モデルで）
        self.recorder.save(metrics=metrics, judge=judge, posture_type=posture_type)

        return {
            **out,
            "judge": judge,
            "posture_type": posture_type
        }
