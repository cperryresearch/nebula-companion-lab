# 🚀 Sanctuary Prime - Streamlit Cloud Deployment Guide

## ✅ What Changed
- API key now loads from `st.secrets` instead of hardcoded value
- Works locally AND on Streamlit Cloud
- Added better error messages if API key is missing

## 📋 Pre-Deployment Checklist

### 1. Update your local secrets.toml
Open `.streamlit/secrets.toml` and ensure it contains:
```toml
GEMINI_API_KEY = "AIzaSyCgSdRpBH8b4k080OJ6VymC-2__-K6pC5Y"
```

### 2. Test Locally First
```bash
streamlit run app.py
```
✅ Verify everything works exactly as before
✅ Check that Nebula responds to messages
✅ Test audio playback
✅ Verify all UI elements display correctly

---

## 🌐 Streamlit Cloud Deployment

### Step 1: Create GitHub Repository
1. Go to https://github.com and create a new repository
2. Name it: `sanctuary-prime` (or whatever you prefer)
3. Make it **Private** (recommended for now)
4. Do NOT initialize with README (we have files already)

### Step 2: Upload Your Code to GitHub
**Option A - Using GitHub Desktop (Easier):**
1. Download GitHub Desktop: https://desktop.github.com/
2. Clone your new empty repository
3. Copy all your project files into the cloned folder
4. Commit and push

**Option B - Using Command Line:**
```bash
cd "C:\Users\YourName\Desktop\AI Companion Pet"
git init
git add .
git commit -m "Initial commit - Sanctuary Prime"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/sanctuary-prime.git
git push -u origin main
```

### Step 3: Deploy to Streamlit Cloud
1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select:
   - Repository: `sanctuary-prime`
   - Branch: `main`
   - Main file path: `app.py`
5. Click "Advanced settings"
6. In "Secrets" section, paste:
   ```toml
   GEMINI_API_KEY = "AIzaSyCgSdRpBH8b4k080OJ6VymC-2__-K6pC5Y"
   ```
7. Click "Deploy!"

### Step 4: Wait for Deployment
- First deployment takes 2-5 minutes
- You'll get a URL like: `https://sanctuary-prime-xyz123.streamlit.app`
- Bookmark this URL!

---

## 🔐 Security: Regenerate Your API Key

**IMPORTANT:** Your API key was exposed in our chat. After deployment works:

1. Go to https://aistudio.google.com/app/apikey
2. Find your key ending in `...C5Y`
3. Click "Delete" or "Revoke"
4. Create a new API key
5. Update both:
   - Local: `.streamlit/secrets.toml`
   - Cloud: Streamlit Cloud → Your App → Settings → Secrets

---

## 📱 Android App Creation (Next Step)

Once your Streamlit app is live:

### Option 1: Webtonative ($29 one-time)
1. Go to https://webtonative.com/
2. Enter your Streamlit app URL
3. Customize app name, icon, splash screen
4. Download APK
5. Install on Android phone

### Option 2: Free Alternative (AppsGeyser)
1. Go to https://appsgeyser.com/
2. Choose "Website"
3. Enter your Streamlit app URL
4. Customize appearance
5. Download APK (may have ads)

---

## 🐛 Troubleshooting

### "Module not found" error
- Check `requirements.txt` includes all packages
- Common missing ones: `google-genai`, `pyttsx3`

### Audio not working on cloud
- `pyttsx3` won't work on cloud (it's a local TTS engine)
- Your Google Cloud TTS fallback should kick in
- This is expected behavior

### Images not showing
- Make sure `images/` folder is in your GitHub repo
- Check file paths are relative, not absolute

### State resets unexpectedly
- Streamlit Cloud restarts apps after inactivity
- This is normal for free tier
- User data in `nebula_data.json` will persist between sessions

---

## 📊 Monitoring Your App

**Streamlit Cloud Dashboard:**
- https://share.streamlit.io/
- View logs, analytics, and usage
- Monitor app health

**Free Tier Limits:**
- 1 GB RAM
- Sleeps after inactivity
- Wakes up when someone visits
- Perfect for hobby projects!

---

## 🎉 Success Checklist

- [ ] Local app works with new secrets system
- [ ] Code pushed to GitHub
- [ ] App deployed to Streamlit Cloud
- [ ] Streamlit Cloud secrets configured
- [ ] App accessible via public URL
- [ ] API key regenerated (security)
- [ ] Android APK created via Webtonative
- [ ] APK installed and tested on phone

---

## 🆘 Need Help?

If anything goes wrong:
1. Check Streamlit Cloud logs (very helpful!)
2. Verify secrets are copy-pasted correctly (no extra spaces)
3. Make sure all files are in GitHub repo
4. Test locally first - if it works locally, it should work on cloud

Good luck with deployment! 🚀
