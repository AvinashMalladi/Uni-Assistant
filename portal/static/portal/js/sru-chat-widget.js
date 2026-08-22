/**
 * SRU Chatbot -- embeddable widget script.
 *
 * Drop this ONE line into any website (WordPress "Custom HTML" block,
 * theme footer.php, Google Tag Manager, etc.):
 *
 *   <script src="https://YOUR-BACKEND-DOMAIN/static/portal/js/sru-chat-widget.js"
 *           data-api-base="https://YOUR-BACKEND-DOMAIN"
 *           data-widget-key="YOUR_WIDGET_KEY"></script>
 *
 * It injects its own floating chat bubble + window, needs no other markup
 * or CSS on the host page, and talks to the Django backend's
 * /api/chat/widget-message/ endpoint over CORS.
 *
 * Config is read from the <script> tag's data-* attributes so a
 * non-technical site owner can configure it without touching JS.
 */
(function () {
  var thisScript = document.currentScript;
  var API_BASE = (thisScript && thisScript.dataset.apiBase) || '';
  var WIDGET_KEY = (thisScript && thisScript.dataset.widgetKey) || '';
  var TITLE = (thisScript && thisScript.dataset.title) || 'SRU Assistant';

  if (!API_BASE) {
    console.error('[sru-chat-widget] Missing data-api-base attribute on the <script> tag.');
    return;
  }

  // ---- session id, persisted per-browser so conversations survive reloads ----
  function getSessionId() {
    var key = 'sru_chat_session_id';
    var existing = window.localStorage.getItem(key);
    if (existing) return existing;
    var id = (window.crypto && window.crypto.randomUUID)
      ? window.crypto.randomUUID()
      : 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2);
    window.localStorage.setItem(key, id);
    return id;
  }
  var sessionId = getSessionId();

  // ---- inject CSS ----
  var style = document.createElement('style');
  style.textContent = `
    #sru-w-launcher { position: fixed; bottom: 24px; right: 24px; width: 56px; height: 56px;
      border-radius: 50%; background: #123a6b; color: #fff; display: flex; align-items: center;
      justify-content: center; font-size: 26px; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.25);
      z-index: 999999; border: none; }
    #sru-w-window { position: fixed; bottom: 92px; right: 24px; width: 340px; max-width: 92vw;
      height: 460px; background: #fff; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.25);
      display: none; flex-direction: column; overflow: hidden; z-index: 999999;
      font-family: 'Segoe UI', Arial, sans-serif; }
    #sru-w-window.open { display: flex; }
    #sru-w-header { background: #123a6b; color: #fff; padding: 12px 16px; display: flex;
      justify-content: space-between; align-items: center; font-weight: 600; }
    #sru-w-header button { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; }
    #sru-w-messages { flex: 1; overflow-y: auto; padding: 12px; background: #f7f9fc; }
    .sru-w-msg { margin-bottom: 10px; padding: 8px 12px; border-radius: 10px; max-width: 85%;
      font-size: 0.9rem; line-height: 1.4; white-space: pre-wrap; }
    .sru-w-msg.bot { background: #e7edf7; color: #123a6b; border-bottom-left-radius: 2px; }
    .sru-w-msg.user { background: #1c5aa6; color: #fff; margin-left: auto; border-bottom-right-radius: 2px; }
    #sru-w-input-row { display: flex; border-top: 1px solid #eee; }
    #sru-w-input { flex: 1; border: none; padding: 12px; font-size: 0.9rem; }
    #sru-w-input:focus { outline: none; }
    #sru-w-send { border: none; background: #d4a017; color: #123a6b; font-weight: 700;
      padding: 0 16px; cursor: pointer; }
  `;
  document.head.appendChild(style);

  // ---- inject DOM ----
  var launcher = document.createElement('button');
  launcher.id = 'sru-w-launcher';
  launcher.innerText = '🤖';
  document.body.appendChild(launcher);

  var win = document.createElement('div');
  win.id = 'sru-w-window';
  win.innerHTML =
    '<div id="sru-w-header"><span>' + TITLE + '</span><button id="sru-w-close">&times;</button></div>' +
    '<div id="sru-w-messages"></div>' +
    '<div id="sru-w-input-row">' +
      '<input type="text" id="sru-w-input" placeholder="Ask about results, attendance, fees...">' +
      '<button id="sru-w-send">Send</button>' +
    '</div>';
  document.body.appendChild(win);

  var messagesEl = win.querySelector('#sru-w-messages');
  var inputEl = win.querySelector('#sru-w-input');
  var sendBtn = win.querySelector('#sru-w-send');
  var closeBtn = win.querySelector('#sru-w-close');
  var greeted = false;

  function addMessage(text, who) {
    var div = document.createElement('div');
    div.className = 'sru-w-msg ' + who;
    div.innerText = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    var div = document.createElement('div');
    div.className = 'sru-w-msg bot';
    div.id = 'sru-w-typing';
    div.innerText = '...';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function hideTyping() {
    var el = document.getElementById('sru-w-typing');
    if (el) el.remove();
  }

  function toggle(show) {
    win.classList.toggle('open', show);
    if (show && !greeted) {
      greeted = true;
      addMessage("Hi! I'm the SRU Assistant 🤖. Ask me about pass percentages, attendance, grading, hostel rules, fees and more.", 'bot');
    }
  }
  launcher.addEventListener('click', function () { toggle(!win.classList.contains('open')); });
  closeBtn.addEventListener('click', function () { toggle(false); });

  async function sendMessage() {
    var text = inputEl.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    inputEl.value = '';
    sendBtn.disabled = true;
    showTyping();

    try {
      var resp = await fetch(API_BASE.replace(/\/$/, '') + '/api/chat/widget-message/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Widget-Key': WIDGET_KEY,
        },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      var data = await resp.json();
      hideTyping();
      if (!resp.ok) {
        addMessage(data.error || 'Sorry, something went wrong on the server.', 'bot');
      } else {
        addMessage(data.reply || 'Sorry, something went wrong.', 'bot');
      }
    } catch (err) {
      hideTyping();
      addMessage('Network error reaching the assistant. Please try again shortly.', 'bot');
    } finally {
      sendBtn.disabled = false;
    }
  }
  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') sendMessage(); });
})();
