import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ChatLog, ChatSessionState
from .services.dialogue_manager import handle_message


@require_POST
def chat_message(request):
    """Same-origin endpoint used by the dummy portal's own chat widget.
    Uses Django's session cookie -- fine because the widget and this API
    are served from the same domain."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    user_message = (payload.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'empty message'}, status=400)

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    ChatLog.objects.create(session_key=session_key, role='user', message=user_message)
    reply = handle_message(request.session, user_message)
    ChatLog.objects.create(session_key=session_key, role='bot', message=reply)

    return JsonResponse({'reply': reply})


class _SessionAdapter:
    """Mimics the small subset of Django's request.session interface that
    dialogue_manager.handle_message() uses (.get / __setitem__ / .modified),
    backed by a plain dict. Lets the exact same dialogue_manager code serve
    both same-origin (Django session, above) and cross-origin (client-
    supplied session_id, below) callers without any changes to the agent
    logic itself."""

    def __init__(self, data):
        self._data = data
        self.modified = False

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __setitem__(self, key, value):
        self._data[key] = value
        self.modified = True

    def as_dict(self):
        return self._data


@csrf_exempt  # safe here: this endpoint only ever reads/writes chat state,
              # never anything sensitive, and is protected by the widget key
              # check below instead of same-site cookies (which cross-origin
              # embeds can't rely on anyway).
@require_POST
def widget_chat_message(request):
    """Cross-origin endpoint for the embeddable widget (sru-chat-widget.js)
    running on a third-party site such as a WordPress-hosted portal."""
    configured_key = settings.WIDGET_API_KEY
    if configured_key:
        provided_key = request.headers.get('X-Widget-Key', '')
        if provided_key != configured_key:
            return JsonResponse({'error': 'invalid or missing widget key'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    user_message = (payload.get('message') or '').strip()
    session_id = (payload.get('session_id') or '').strip()
    if not user_message or not session_id:
        return JsonResponse({'error': 'message and session_id are both required'}, status=400)

    ChatLog.objects.create(session_key=session_id, role='user', message=user_message)

    state_obj, _ = ChatSessionState.objects.get_or_create(session_id=session_id)
    state_dict = json.loads(state_obj.state_json) if state_obj.state_json else {}
    adapter = _SessionAdapter(state_dict)

    reply = handle_message(adapter, user_message)

    if adapter.modified:
        state_obj.state_json = json.dumps(adapter.as_dict())
        state_obj.save(update_fields=['state_json', 'updated_at'])

    ChatLog.objects.create(session_key=session_id, role='bot', message=reply)
    return JsonResponse({'reply': reply})
