# DeepShield AI — Deepfake Detection System

A full-stack deepfake detection system powered by Vision Transformer (ViT-Base/16) with attention-based explainability heatmaps.

## Features

- **Image Analysis** — Upload images for instant deepfake detection with attention heatmap overlay
- **Video Analysis** — Frame-by-frame analysis with majority vote aggregation
- **Real-Time Webcam** — Live deepfake detection from your camera feed
- **Attention Rollout Explainability** — Visual heatmaps showing which facial regions the model focused on
- **Human-Readable Explanations** — AI-generated text explaining the detection rationale
- **Admin Panel** — User management, statistics, and activity monitoring
- **JWT Authentication** — Secure signup/login with role-based access

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ML Model | ViT-Base/16 (PyTorch + HuggingFace Transformers) |
| Model Format | SafeTensors (HuggingFace) |
| Face Detection | MTCNN (primary) + Haarcascade fallback |
| Explainability | Attention Rollout (ViT-native) |
| Backend | Flask + SQLAlchemy + Flask-JWT-Extended |
| Frontend | Vanilla HTML/CSS/JS (dark theme, glassmorphism) |
| Database | SQLite (dev) / PostgreSQL (prod) |

## Quick Start

### 1. Clone & Setup Virtual Environment

```bash
git clone <repo-url>
cd DeepFake
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (JWT secret, admin credentials, etc.)
```

### 4. Ensure Model Files Exist

The trained ViT model should be in `models/vit-deepfake/` with these files:
```
models/vit-deepfake/
├── config.json              # Model architecture config
├── model.safetensors        # Trained weights (~343MB)
└── preprocessor_config.json # Image preprocessing config
```
You can download the model from hugging face spaces link- https://huggingface.co/Satvik078/models

### 5. Run the Server

```bash
source venv/bin/activate   # if not already active
python3 run.py
```

Visit `http://localhost:5003` in your browser.

> ⚠️ Change these in `.env` for production!

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/auth/logout` | Invalidate token |
| GET | `/api/auth/me` | Current user info |

### Prediction (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict/image` | Upload image for analysis |
| POST | `/api/predict/video` | Upload video for analysis |
| POST | `/api/predict/webcam` | Send base64 frame |

### Admin (admin role required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users |
| POST | `/api/admin/disable_user` | Toggle user status |
| GET | `/api/admin/stats` | Dashboard statistics |

## Project Structure

```
DeepFake/
├── run.py                  # Flask entry point
├── config.py               # Configuration (env-based)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .env.example            # Env template
├── train_colab.py          # Colab training script (standalone)
├── models/
│   └── vit-deepfake/       # Trained ViT model
│       ├── config.json
│       ├── model.safetensors
│       └── preprocessor_config.json
├── app/
│   ├── __init__.py          # App factory
│   ├── extensions.py        # DB, JWT, CORS
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py          # User account model
│   │   └── activity.py      # Activity tracking model
│   ├── auth/                # Auth routes
│   │   └── routes.py        # signup, login, logout, me
│   ├── prediction/          # Prediction routes
│   │   └── routes.py        # image, video, webcam
│   ├── admin/               # Admin routes
│   │   └── routes.py        # users, stats, disable_user
│   └── utils/               # ML utilities
│       ├── inference.py     # ViT model loading & prediction
│       ├── face_detector.py # MTCNN + Haarcascade face detection
│       ├── gradcam.py       # Attention rollout heatmaps
│       ├── explainer.py     # Region-based text explanations
│       ├── video_processor.py # Frame extraction & batch prediction
│       └── preprocessing.py # Image transforms & normalization
└── frontend/
    ├── index.html           # Home page
    ├── login.html           # Login page
    ├── signup.html          # Signup page
    ├── dashboard.html       # User dashboard
    ├── admin.html           # Admin panel
    ├── css/styles.css       # Design system
    └── js/
        ├── api.js           # Centralized API helper
        ├── auth.js          # Auth logic & route guards
        ├── dashboard.js     # Upload, webcam, results
        └── admin.js         # User management
```

## How It Works

1. **Face Detection** — MTCNN detects and crops faces from the uploaded image
2. **ViT Inference** — The cropped face is preprocessed (224×224, normalized to [0.5, 0.5, 0.5]) and passed through the ViT-Base/16 classifier
3. **Classification** — The model outputs 2-class softmax probabilities (Fake vs Real)
4. **Attention Rollout** — Attention weights from all 12 transformer layers are aggregated to produce a spatial heatmap showing which regions the model focused on
5. **Explanation** — The heatmap is analyzed region-by-region (eyes, mouth, nose, forehead, etc.) to generate human-readable explanations


## License
