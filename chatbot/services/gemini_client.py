"""
Thin wrapper around Google AI Studio's Gemini API for the generation step
of the RAG pipeline. Degrades gracefully (returns the raw retrieved
handbook text) if GOOGLE_API_KEY isn't set, so the rest of the demo still
works without a live key.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the SR University Student Assistant, an agentic AI chatbot embedded "
    "in the university's student portal. Answer ONLY using the provided handbook "
    "context below. Be concise (3-5 sentences), warm, and specific -- cite section "
    "names or numbers where helpful. If the context does not contain the answer, "
    "say you're not certain and point the student to the relevant office/contact "
    "mentioned in the handbook instead of guessing."
)


def _fallback_answer(question, context_chunks):
    if not context_chunks:
        return ("I couldn't find that in the student handbook. Try asking about "
                "attendance, grading, promotion rules, hostel rules, fees, or exam policies.")
    return "Here's what the handbook says:\n\n" + "\n\n".join(context_chunks[:2])


def generate_answer(question, context_chunks):
    api_key = settings.GOOGLE_API_KEY
    if not context_chunks:
        return _fallback_answer(question, context_chunks)

    if not api_key:
        logger.info("GOOGLE_API_KEY not set - serving retrieved handbook text directly (no LLM call).")
        return _fallback_answer(question, context_chunks)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no relevant handbook section found)"
        prompt = (
            f"Handbook context:\n{context_text}\n\n"
            f"Student question: {question}\n\n"
            f"Answer using only the context above."
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        return (response.text or "").strip() or _fallback_answer(question, context_chunks)
    except Exception:
        logger.exception("Gemini API call failed - falling back to retrieved text.")
        return _fallback_answer(question, context_chunks)
