"""
Run this BEFORE your demo, not during it:

    python manage.py check_gemini

Verifies GOOGLE_API_KEY is set and the configured Gemini model actually
responds, so a bad key or a deprecated/misspelled model name shows up now
instead of silently degrading to the raw-text fallback live on stage.
"""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify GOOGLE_API_KEY and GEMINI_MODEL actually work before a demo."

    def handle(self, *args, **options):
        self.stdout.write(f"GEMINI_MODEL configured as: {settings.GEMINI_MODEL}")

        if not settings.GOOGLE_API_KEY:
            self.stdout.write(self.style.ERROR(
                "GOOGLE_API_KEY is NOT set in this terminal session.\n"
                "Run:  $env:GOOGLE_API_KEY=\"AIzaSy...\"   (PowerShell)\n"
                "The chatbot will still run without it, but will only return "
                "raw retrieved handbook text instead of a polished answer."
            ))
            return

        masked = settings.GOOGLE_API_KEY[:6] + "..." + settings.GOOGLE_API_KEY[-4:]
        self.stdout.write(f"GOOGLE_API_KEY found: {masked}")

        if not settings.GOOGLE_API_KEY.startswith("AIzaSy"):
            self.stdout.write(self.style.ERROR(
                "GOOGLE_API_KEY does not look like a Google AI Studio API key. "
                "It should start with 'AIzaSy'. Create a new key at "
                "https://aistudio.google.com/app/apikey and set it in PowerShell "
                "with: $env:GOOGLE_API_KEY=\"AIzaSy...\""
            ))
            return

        try:
            from google import genai
        except ImportError:
            self.stdout.write(self.style.ERROR(
                "google-genai is not installed. Run: pip install -r requirements.txt"
            ))
            return

        try:
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents="Reply with exactly: OK",
            )
            text = (response.text or "").strip()
            self.stdout.write(self.style.SUCCESS(
                f"SUCCESS: Gemini responded: '{text}'\n"
                f"Your API key and model ({settings.GEMINI_MODEL}) are working."
            ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f"FAILED to call Gemini: {exc}\n\n"
                f"Common causes:\n"
                f"  - Wrong key format (should start with 'AIzaSy...', get one at "
                f"https://aistudio.google.com/app/apikey)\n"
                f"  - Model name deprecated/misspelled (try 'gemini-3.6-flash')\n"
                f"  - No internet access from this machine right now\n"
                f"The app will still run and demo the slot-filling/bandit logic "
                f"fine, but will fall back to raw handbook text instead of a "
                f"polished LLM answer until this is fixed."
            ))
