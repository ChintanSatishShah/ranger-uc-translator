# Git Integration Guide

## Repository Structure

```
ranger-uc-translator/
├── app.yaml                  # Databricks App config
├── app.py                    # Streamlit UI entry point
├── requirements.txt
├── README.md
├── .gitignore
├── src/
│   ├── parser.py             # Ranger JSON parser
│   ├── translator.py         # UC SQL translator
│   ├── validator.py          # JSON + SQL validation
│   ├── applier.py            # SQL executor
│   ├── config.py             # Mappings and settings
│   └── utils.py              # Helpers
├── samples/                  # 12 sample Ranger policy files
├── docs/                     # This folder
└── tests/                    # Test suite and setup SQL
```

---

## Initial Setup

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Name: `ranger-uc-translator`
3. Do **not** initialise with README
4. Click **Create repository**

### 2. Add Remote and Push

```bash
cd ranger-uc-translator

git remote add origin https://github.com/YOUR_USERNAME/ranger-uc-translator.git
git push -u origin main
```

### 3. Link to Databricks Repos (optional)

1. Databricks workspace → **Repos** → **Add Repo**
2. Enter your GitHub URL
3. Work directly in the Repos folder for automatic sync

---

## GitHub Authentication

**Personal Access Token:**
1. GitHub → Settings → Developer Settings → Personal Access Tokens
2. Generate token with `repo` scope
3. Databricks → User Settings → Git Integration → add token

---

## Deploy as Databricks App

**Via UI:**
1. Databricks workspace → **Apps** → **Create App**
2. Source: your Repo path (e.g. `/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator`)
3. App auto-installs from `requirements.txt`
4. Access via generated app URL

**Via CLI:**
```bash
databricks apps deploy ranger-uc-translator \
  --source-code-path /Workspace/Repos/YOUR_USERNAME/ranger-uc-translator
```

**Troubleshooting:** If the app shows "Starting..." or "Not Available", wait 3–5 minutes for dependencies to install, then refresh. Check app logs in the Databricks Apps UI if the issue persists.

**Audit tables (optional):** Run `tests/setup.sql` in Databricks SQL Editor to create audit tables in `main.ranger_migration`. Only needed for compliance tracking — the app works without it.

---

## Branching Strategy

```
main       ← production
develop    ← integration branch
feature/*  ← individual features
hotfix/*   ← emergency fixes
```

```bash
git checkout -b feature/your-feature
git add src/your_file.py
git commit -m "Add: your feature"
git push origin feature/your-feature
# Open PR → develop → main
```
