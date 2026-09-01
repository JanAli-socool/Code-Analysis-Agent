# Vercel Deployment Setup

## 1. Create Vercel Project

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "Add New..." → "Project"
3. Import your GitHub repo: `JanAli-socool/Code-Analysis-Agent`
3. Configure:
   - **Framework Preset**: Create React App
   - **Root Directory**: `dashboard/frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
4. Click "Deploy"

## 2. Get Vercel Credentials

After first deploy, get these from Vercel Dashboard → Settings:

| Secret | Where to find |
|--------|---------------|
| `VERCEL_TOKEN` | Settings → Tokens → Create |
| `VERCEL_ORG_ID` | Settings → General → Organization ID |
| `VERCEL_PROJECT_ID` | Settings → General → Project ID |

## 3. Add GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `VERCEL_TOKEN` | Your Vercel token |
| `VERCEL_ORG_ID` | Your org ID |
| `VERCEL_PROJECT_ID` | Your project ID |
| `REACT_APP_API_URL` | Your backend URL (e.g., `https://your-backend.onrender.com`) |

## 4. Auto-Deploy

The workflow `.github/workflows/deploy-vercel.yml` will:
- ✅ Run on every push to `main` (when `dashboard/frontend/` changes)
- ✅ Run tests
- ✅ Build the React app
- ✅ Deploy to Vercel production
- ✅ Show preview URL on PRs

## Local Development

```bash
cd dashboard/frontend
npm install
npm start  # Runs on http://localhost:3000
```

## Backend API (Not on Vercel)

Vercel only hosts static/Next.js. For the Python FastAPI backend, deploy separately:

| Platform | Quick Start |
|----------|-------------|
| **Render** | `render.yaml` + connect GitHub |
| **Railway** | `railway.json` + `railway up` |
| **Fly.io** | `fly.toml` + `fly deploy` |
| **Google Cloud Run** | `gcloud run deploy` |
| **AWS ECS/Fargate** | `aws ecs create-service` |

The frontend expects `REACT_APP_API_URL` to point to your backend.