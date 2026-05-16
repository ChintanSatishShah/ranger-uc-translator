# 🚀 Databricks App Deployment Guide

## ✅ Prerequisites (Already Done!)
- [x] App file exists: app.py (27KB)
- [x] Requirements defined: requirements.txt
- [x] Repository: /Repos/chintsinfo@gmail.com/ranger-uc-translator
- [x] Sample data: 12 policy files in samples/

---

## 📱 Deployment Steps

### Step 1: Open Apps Section
1. In Databricks workspace, look at the **left sidebar**
2. Click **"Apps"** (looks like a grid icon 📱)
3. Click **"Create App"** button (top right)

### Step 2: Configure App
Fill in the form:

**Basic Info:**
- **Name:** `Ranger UC Migration Tool`
- **Description (optional):** `Translate Apache Ranger policies to Unity Catalog`

**Source:**
- **Source type:** Select **"Workspace file"**
- **Source path:** 
  ```
  /Repos/chintsinfo@gmail.com/ranger-uc-translator/app.py
  ```

**Compute:**
- **Option A:** Select existing cluster (if you have one)
- **Option B:** Use **Serverless** (recommended - auto-scaling)

### Step 3: Deploy
1. Click **"Create"**
2. Wait ~2-3 minutes for deployment
3. Status will change from "Starting" → "Running"

### Step 4: Access Your App
Once running, you'll see:
- **App URL:** `https://<your-workspace>.databricks.com/apps/<app-id>`
- Click the URL to open the app
- Share this URL with your team!

---

## 🎨 What You'll See

The app has 6 pages:

1. **🏠 Home** - Welcome and overview
2. **📤 Upload & Validate** - Load policies (12 samples available!)
3. **🔄 Translate** - Convert to Unity Catalog
4. **👁️ Review & Compare** - Side-by-side comparison
5. **💾 Export Results** - Download SQL/CSV/JSON
6. **📊 Statistics** - Metrics and charts

---

## 🧪 Quick Test

Once app is running:

1. Go to **"📤 Upload & Validate"**
2. Click **"Sample Policies"** tab
3. Select **"access_simple.json"**
4. Click load → should see ✅ validation success
5. Go to **"🔄 Translate"**
6. Click **"🚀 Start Translation"**
7. Should generate 1 policy with 1 SQL statement
8. Go to **"👁️ Review & Compare"** to see results!

**Expected:** 100% success, 1 SQL GRANT statement generated

---

## 🔧 Troubleshooting

### "Module not found" error
**Solution:** Ensure requirements.txt is in the repo root (it is!)

### "Compute not available"
**Solution:** Choose "Serverless" compute option

### App not starting
**Solution:** Check app logs in Databricks Apps dashboard

### Can't find app.py
**Solution:** Verify path is: `/Repos/chintsinfo@gmail.com/ranger-uc-translator/app.py`

---

## 📞 Need Help?

- Check app logs in Databricks Apps section
- Verify compute is running
- Ensure you have workspace access
- Check APP_USER_GUIDE.md for detailed feature docs

---

**🎉 That's it! Your app should be live and ready to use!**
