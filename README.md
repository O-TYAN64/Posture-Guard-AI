<h1 align="center">
  <img src="images/icon.png" width="72">
  <br>
  Posture-Guard-AI
</h1>

<p align="center">
  <b>カメラ映像から姿勢をリアルタイム解析する 姿勢チェックAI</b>
</p>

<p align="center">
  猫背・首の前傾・体の傾きを数値化し、今の姿勢を分かりやすくフィードバック
</p>

---

## 📌 概要

**Posture-Guard-AI** は、PCやWebカメラの映像を使って  
人の姿勢をリアルタイムに解析・評価する **姿勢チェックAIアプリ** です。

MediaPipe Pose による人体推定をベースに、

- 今どんな姿勢か  
- どれくらい姿勢が崩れているか  

を **角度・スコア・メッセージ** として可視化します。

インストール不要で、ブラウザからすぐに利用できます。

---

## ✨ 主な機能

### 📷 リアルタイム姿勢検出
- Webカメラ映像から人体ランドマークを取得
- 上半身を中心に姿勢を解析

### 📐 姿勢の数値化
- 首の前傾角（CVA）
- 上半身の前後傾
- 肩の左右傾き

### 🧠 姿勢スコアリング
- 各角度を総合評価
- 0〜100点などのスコアとして表示

### 💬 フィードバック表示
- 姿勢が崩れるとリアルタイムで注意喚起
- 例：「首が前に出ています」「背筋を伸ばしましょう」

### 🌐 Web UI
- ブラウザ上で動作
- PC / タブレット対応（予定）

※機能に関して、今後変更される可能性があります。

---

## 🖥️ デモ（想定）

<div style="display: flex; align-items: flex-start; gap: 24px;">

<div>

**画面表示内容**
- カメラ映像  
- 姿勢スコア  
- 首・胴体・肩の角度  
- 姿勢コメント  

</div>
<p>
<img src="images/demo.png" width="420">
</P>
</div>

※ 画面のUI/UXは今後変更される可能性があります。


---

## 🧩 姿勢判定ロジック（概要）

### 首の前傾（CVA）
- 肩 → 耳 のベクトルと水平線の角度
- 一定角度以下で「首が前に出ている」と判定

### 上半身の前後傾
- 肩と腰の位置関係から胴体角度を算出

### 肩の傾き
- 左右の肩の高さ差を計算

各値が閾値を超えると「姿勢が悪い」と評価されます。

---

## 📁 ディレクトリ構成



```
Posture-Guard-AI
├─ app/                 # アプリケーションコード
│  ├─ static/           # CSS / JS / 画像
│  ├─ templates/        # HTML テンプレート
│  ├─ app.py            # Flask / FastAPI エントリーポイント
|  ├─ database.db       # SQLite データベース（必要に応じて）
│  ├─ config.py         # SQLiteの設定ファイル
│  ├─ extensions.py     # Flask 拡張機能の初期化
│  └─ posture_check.py  # 姿勢解析ロジック
├─ LICENSE
└─ README.md
```

※ 実際の構成は今後変更される可能性があります。

---

## ⚙️ 使用技術

* **Python 3.10+**
* **MediaPipe Pose**
* **OpenCV**
* **Flask**（または FastAPI）
* **HTML / CSS / JavaScript**

---

## 🚀 セットアップ方法

### 1️⃣ リポジトリをクローン

```bash
git clone https://github.com/O-TYAN64/Posture-Guard-AI.git
cd Posture-Guard-AI
```

### 2️⃣ 仮想環境作成（推奨）

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS / Linux
```

### 4️⃣ アプリ起動

```bash
python app/app.py
```

ブラウザで以下にアクセス：

```
http://localhost:5000
```

---

## 📊 姿勢判定の考え方（例）

* **首前傾（CVA）**
  肩 → 耳 のベクトルと水平線の角度

* **上半身前後傾**
  肩と腰の位置関係から算出

* **肩の傾き**
  左右肩の高さの差

一定の閾値を超えると「姿勢が悪い」と判定します。

---

## 🧪 開発・拡張アイデア

* 🔔 一定時間悪い姿勢が続いたら通知
* 📈 姿勢ログの保存・可視化
* 📱 モバイル対応

---

## 📄 ライセンス

MIT License
See [LICENSE](LICENSE) for details.