# Git Integration Guide for ranger_uc_translator

## 📦 Package Structure

```
ranger_uc_translator/          (← Git repository root)
├── .git/                      (Git metadata)
├── .gitignore                 (Git ignore rules)
├── README.md                  (Project documentation)
├── requirements.txt           (Python dependencies)
├── setup.sql                  (Database setup)
├── __init__.py               (Package initialization)
├── app.py                    (Streamlit UI - entry point)
├── parser.py                 (Ranger JSON parser)
├── translator.py             (Translation engine)
├── applier.py                (Policy executor)
├── config.py                 (Configuration)
├── utils.py                  (Helper functions)
└── samples/                  (Sample policy files)
    ├── README.md
    ├── access_*.json         (3 files)
    ├── rowfilter_*.json      (3 files)
    ├── masking_*.json        (3 files)
    └── tag_*.json            (3 files)
```

## 🚀 Option 1: Using Databricks Repos (Recommended)

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `ranger-uc-translator`
3. Description: "Apache Ranger to Unity Catalog Policy Translation Engine"
4. Choose Public or Private
5. **Do NOT initialize with README** (we already have one)
6. Click "Create repository"

### Step 2: Link via Databricks Repos

1. In Databricks workspace, click **Repos** in the left sidebar
2. Click **Add Repo**
3. Enter your GitHub URL: `https://github.com/YOUR_USERNAME/ranger-uc-translator.git`
4. Click **Create Repo**

This will create: `/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator`

### Step 3: Copy Files to Databricks Repo

```python
import shutil
import os

source = '/Workspace/Users/chintsinfo@gmail.com/Ranger Policy Translator/ranger_uc_translator'
destination = '/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator'

# Copy all files
for item in os.listdir(source):
    src_path = os.path.join(source, item)
    dst_path = os.path.join(destination, item)
    
    # Skip .git directory
    if item == '.git':
        continue
        
    if os.path.isfile(src_path):
        shutil.copy2(src_path, dst_path)
    elif os.path.isdir(src_path):
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path)

print("✅ Files copied to Databricks Repo")
```

### Step 4: Commit and Push

1. In Databricks, navigate to the Repo folder
2. Click the **branch dropdown** (top right)
3. Click **"Commit & Push"**
4. Commit message: `Initial commit: Ranger to UC Translation Engine`
5. Click **"Commit & Push"**

## 🔧 Option 2: Manual Git Push (Alternative)

If you prefer to push directly from the workspace:

### Step 1: Configure Git Authentication

```bash
# Set up Git credentials in Databricks
# Go to User Settings → Git Integration → Add your GitHub token
```

### Step 2: Add Remote and Push

Since git is already initialized, just add remote:

```bash
cd "/Workspace/Users/chintsinfo@gmail.com/Ranger Policy Translator/ranger_uc_translator"

# Add remote (replace with your GitHub URL)
git remote add origin https://github.com/YOUR_USERNAME/ranger-uc-translator.git

# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: Ranger to UC Translation Engine

- Core translation engine (parser, translator, applier)
- Streamlit UI with 6 pages
- Support for 4 policy types (ACL, Row Filters, Column Masks, Tags)
- 12 comprehensive sample files
- Complete documentation"

# Push to GitHub
git push -u origin main
```

## 🔐 GitHub Authentication

### Personal Access Token (Classic)

1. GitHub → Settings → Developer Settings → Personal Access Tokens
2. Generate new token (classic)
3. Scopes: `repo` (full control of private repositories)
4. Copy token
5. Databricks → User Settings → Git Integration → Add token

### SSH Key (Alternative)

1. Generate: `ssh-keygen -t ed25519 -C "chintsinfo@gmail.com"`
2. Add public key to GitHub: Settings → SSH and GPG keys
3. Databricks → User Settings → Git Integration → Add SSH key

## 📋 After Initial Push

### Clone to Databricks Repos

Once pushed to GitHub, you can:

1. **Repos** → **Add Repo**
2. Enter: `https://github.com/YOUR_USERNAME/ranger-uc-translator.git`
3. Work directly in the Repos folder

### Deploy as Databricks App

1. **Apps** → **Create App**
2. **Source**: Choose your Repo or workspace folder
3. **Entry point**: `app.py`
4. **Deploy**

## 🌿 Recommended Branching Strategy

```
main          ← Production-ready code
├── develop   ← Development branch
│   ├── feature/row-filters
│   ├── feature/tag-policies
│   └── feature/ui-improvements
└── hotfix/   ← Emergency fixes
```

## 📊 Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and commit
git add .
git commit -m "Add: your feature description"

# Push feature branch
git push origin feature/your-feature

# Create Pull Request on GitHub
# After review, merge to develop → main
```

## ✅ Verification

After setup, verify:

```bash
cd "/Workspace/Users/chintsinfo@gmail.com/Ranger Policy Translator/ranger_uc_translator"

# Check status
git status

# Check remote
git remote -v

# Check branch
git branch

# Check commit history
git log --oneline
```

## 🎯 Next Steps

1. ✅ Push code to GitHub
2. ✅ Set up Databricks Repos
3. ✅ Deploy as Databricks App
4. ✅ Add collaborators
5. ✅ Set up branch protection
6. ✅ Enable GitHub Actions (optional)

---

**Current Status:**
- ✅ Git initialized in `ranger_uc_translator/`
- ✅ All files organized in package structure
- ✅ .gitignore configured
- ⏳ Waiting for GitHub repo creation
- ⏳ Waiting for initial push
