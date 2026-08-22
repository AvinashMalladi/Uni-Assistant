# Deploying the chatbot + embedding it into another (non-Django) website

Since the target site is WordPress/PHP, the chatbot can't be copy-pasted into
their codebase the way it could with another Django project. Instead:

1. **You deploy this Django project** somewhere with a public URL (it becomes
   a small API service).
2. **You hand the other person exactly one thing**: an embed snippet
   (one `<script>` tag) that points at your deployed URL. They paste it into
   WordPress. That's it on their end.

No Python, no server code, nothing WordPress-specific to install on their side.

---

## Part 1 — Deploy the backend (you do this)

### Option A: Render.com (recommended — free tier, simplest)

1. Push this project to a GitHub repo (private is fine).
2. Go to https://render.com → **New +** → **Web Service** → connect your repo.
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn config.wsgi --log-file -`
   - **Instance type:** Free
4. Add environment variables (Render dashboard → Environment):
   ```
   GOOGLE_API_KEY=AIzaSy...your-real-key
  GEMINI_MODEL=gemini-3.6-flash
   DJANGO_SECRET_KEY=<any long random string>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=your-app-name.onrender.com
   CORS_ALLOWED_ORIGINS=https://the-wordpress-site.com
   WIDGET_API_KEY=<any long random string — this is your shared secret>
   ```
5. Deploy. Once live, open the Render **Shell** tab and run once:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   python manage.py collectstatic --noinput
   python manage.py check_gemini
   ```
6. Confirm it works: visit `https://your-app-name.onrender.com/` — you should
   see the dummy portal load with the chat widget.

### Option B: Railway, PythonAnywhere, or any VPS

Same environment variables and commands apply — `Procfile` and
`requirements.txt` are already set up for platforms that use them
(Railway reads `Procfile` the same way).

---

## Part 2 — What to send the other person

Just this snippet, filled in with your real deployed values:

```html
<script src="https://your-app-name.onrender.com/static/portal/js/sru-chat-widget.js"
        data-api-base="https://your-app-name.onrender.com"
        data-widget-key="THE_SAME_WIDGET_API_KEY_YOU_SET_ON_RENDER"
        data-title="SRU Assistant"></script>
```

### Where they paste it in WordPress

Any of these work — pick whichever their site already uses:

- **Block editor:** Add a "Custom HTML" block anywhere on the page (footer
  template, a template part, or a specific page) and paste the snippet in.
- **Classic editor / theme file:** Paste it just before `</body>` in
  `footer.php` (Appearance → Theme File Editor), so it loads on every page.
- **No-code plugin route:** Install "Insert Headers and Footers" (or
  similar), paste the snippet into the **Footer** box, save.

The widget bubble appears bottom-right on every page it's loaded on — no
other markup or CSS needed on their end, it injects its own.

---

## Notes on what changed to make this possible

- **New endpoint** `/api/chat/widget-message/` — separate from the original
  `/api/chat/message/` used by the dummy portal's own widget, so nothing
  about the original localhost demo changed.
- **Session handling**: the original endpoint relies on Django's session
  cookie, which only works same-origin. The widget instead generates its
  own random session ID (stored in the visitor's browser via
  `localStorage`) and sends it explicitly on every request; the backend
  persists dialogue state (the slot-filling progress) against that ID in
  a small `ChatSessionState` table instead of Django sessions.
- **CORS**: `django-cors-headers` is now installed and configured to allow
  only the origins you list in `CORS_ALLOWED_ORIGINS` — not "allow
  everyone," so random sites can't quietly start calling your API.
- **Widget key**: a simple shared-secret header (`X-Widget-Key`) checked
  server-side, mainly to stop the endpoint being spammed/scraped by anyone
  who finds the URL — not full auth, but appropriate for a free-tier
  informational chatbot with no sensitive data behind it.
- **Static files in production**: `whitenoise` now serves `sru-chat-widget.js`
  (and the rest of `/static/`) directly from Django/gunicorn, so you don't
  need a separate CDN or nginx just to host one JS file.

## Before you hand it off — test the exact flow they'll get

```bash
curl -X POST https://your-app-name.onrender.com/api/chat/widget-message/ \
  -H "Content-Type: application/json" \
  -H "X-Widget-Key: THE_SAME_WIDGET_API_KEY" \
  -d '{"message": "What is the minimum attendance required?", "session_id": "test-123"}'
```

You should get back `{"reply": "..."}`. If you get a 403, the widget key
doesn't match. If you get a CORS error only in the browser (curl won't show
it), double check `CORS_ALLOWED_ORIGINS` matches the WordPress site's exact
domain (including `https://`, no trailing slash).
