import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

# Set DJANGO_DEBUG=False in production (Render/Railway/etc). DEBUG=True
# leaks stack traces to anyone who hits an error -- fine for localhost,
# not fine once this is a public URL a WordPress site is calling.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# In production, set this to your actual host, e.g. "sru-chatbot.onrender.com".
# Render also provides RENDER_EXTERNAL_HOSTNAME automatically.
configured_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
ALLOWED_HOSTS = []
for host in configured_hosts + [render_hostname]:
    normalized_host = host.strip().lower()
    if '://' in normalized_host:
        normalized_host = normalized_host.split('://', 1)[1]
    normalized_host = normalized_host.split('/', 1)[0]
    if normalized_host and normalized_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(normalized_host)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'portal',
    'chatbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'portal' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'portal' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Cross-origin widget support (for embedding on a different site, e.g. the
# real WordPress-hosted university portal, instead of this dummy Django one)
# ---------------------------------------------------------------------------
# Comma-separated list of origins allowed to call /api/chat/widget-message/,
# e.g. "https://www.realuniversitysite.edu,https://staging.realuniversitysite.edu"
# Leave unset only for local testing -- an empty list blocks all cross-origin
# requests by default (safe default; you must opt sites in explicitly).
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = False  # widget auth uses a header key, not cookies

# Shared-secret header key the widget script must send (X-Widget-Key) to
# call /api/chat/widget-message/. Set a real value in production; empty
# string disables the check (fine for local testing only).
WIDGET_API_KEY = os.environ.get('WIDGET_API_KEY', '')

# ---------------------------------------------------------------------------
# Chatbot / Agentic AI configuration
# ---------------------------------------------------------------------------
# Get a free key from https://aistudio.google.com/app/apikey and set it as an
# environment variable before running the server:
#   export GOOGLE_API_KEY="your-key-here"        (Mac/Linux)
#   set GOOGLE_API_KEY=your-key-here              (Windows cmd)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

# Default to the currently available model. Override via env var if Google
# changes model availability again.
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
GEMINI_EMBEDDING_MODEL = os.environ.get('GEMINI_EMBEDDING_MODEL', 'models/text-embedding-004')

# Path to the knowledge source the RAG pipeline retrieves from
STUDENT_HANDBOOK_PATH = BASE_DIR / 'data' / 'student_handbook.txt'

# Epsilon for the epsilon-greedy bandit that learns the best order to ask
# clarifying (slot-filling) questions in.
BANDIT_EPSILON = float(os.environ.get('BANDIT_EPSILON', '0.15'))
