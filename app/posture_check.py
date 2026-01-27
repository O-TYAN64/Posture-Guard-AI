from dataclasses import dataclass
import math
import time
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


# =========================
# Config / Baseline
# =========================

@dataclass
class PostureConfig:
    torso_angle_thr: float = 10.0      # 体幹前後傾（推奨10°）
    neck_angle_thr: float = 5.0        # 首前傾（厳しめ）
    shoulder_tilt_thr: float = 10.0     # 肩傾き
    ema_alpha: float = 0.25


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
# Calibrator
# =========================

class PostureCalibrator:
    def __init__(self):
        self.buf = []

    def add(self, m):
        self.buf.append(m)

    def finish(self):
        keys = self.buf[0].keys()
        return {
            k: float(np.mean([b[k] for b in self.buf]))
            for k in keys
        }


# =========================
# Analyzer
# =========================

class PosePostureAnalyzer:
    def __init__(self, model_path: str, cfg: PostureConfig):
        self.cfg = cfg
        self.baseline: PostureBaseline | None = None
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

    # =========================
    def reset_ema(self):
        self.ema_torso.reset()
        self.ema_neck.reset()
        self.ema_tilt.reset()
        self._locked_center = None

    # =========================
    def _tick(self):
        now = time.perf_counter()
        dt = max(1, int((now - self._last) * 1000))
        self._last = now
        self._ts += dt

    # =========================
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

    # =========================
    def analyze(self, frame_bgr):
        self._tick()

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self.detector.detect_for_video(mp_img, self._ts)

        if not res.pose_world_landmarks:
            self._locked_center = None
            return None

        lm = res.pose_world_landmarks[0]

        NOSE = 0
        L_SH, R_SH = 11, 12
        L_HIP, R_HIP = 23, 24

        p = lambda i: np.array([lm[i].x, lm[i].y, lm[i].z])

        shoulder = (p(L_SH) + p(R_SH)) * 0.5
        hip = (p(L_HIP) + p(R_HIP)) * 0.5
        head = p(NOSE)

        # =========================
        # 人ロック判定
        # =========================
        center = shoulder

        if self._locked_center is None:
            self._locked_center = center
        else:
            dist = np.linalg.norm(center - self._locked_center)
            if dist > self._lock_dist_thr:
                return None  # 別人と判断

        self._locked_center = center

        # =========================
        # 体幹前後傾
        # =========================
        torso_vec = shoulder - hip
        if np.linalg.norm(torso_vec) < 1e-4:
            return None
        torso_angle = self._angle_from_vertical(torso_vec)

        # =========================
        # 首前傾
        # =========================
        neck_vec = head - shoulder
        if np.linalg.norm(neck_vec) < 1e-4:
            return None
        neck_angle = self._angle_from_vertical(neck_vec)

        # =========================
        # 肩傾き
        # =========================
        shoulder_vec = p(L_SH) - p(R_SH)
        shoulder_tilt = self._angle_from_horizontal(shoulder_vec)

        # =========================
        # EMA
        # =========================
        torso_angle = self.ema_torso.update(torso_angle)
        neck_angle = self.ema_neck.update(neck_angle)
        shoulder_tilt = self.ema_tilt.update(shoulder_tilt)

        return {
            "torso_angle": torso_angle,
            "neck_angle": neck_angle,
            "shoulder_tilt": shoulder_tilt
        }

        

    # =========================
    def calibrate(self, metrics_avg):
        self.reset_ema()
        self.baseline = PostureBaseline(**metrics_avg)

    # =========================
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
