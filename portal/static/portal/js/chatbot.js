// SRU Chat Widget - talks to /api/chat/message/
(function () {
  const launcher = document.getElementById('sru-chat-launcher');
  const win = document.getElementById('sru-chat-window');
  const closeBtn = document.getElementById('sru-chat-close');
  const messages = document.getElementById('sru-chat-messages');
  const input = document.getElementById('sru-chat-input');
  const sendBtn = document.getElementById('sru-chat-send');

  let greeted = false;

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function addMessage(text, who) {
    const div = document.createElement('div');
    div.className = `msg ${who}`;
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function toggleWindow(show) {
    win.classList.toggle('hidden', !show);
    if (show && !greeted) {
      greeted = true;
      addMessage("Hi! I'm the SRU Assistant 🤖. Ask me about pass percentages, attendance, grading, hostel rules, fees and more.", 'bot');
    }
  }

  launcher.addEventListener('click', () => toggleWindow(win.classList.contains('hidden')));
  closeBtn.addEventListener('click', () => toggleWindow(false));

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'msg bot typing';
    div.id = 'sru-typing-indicator';
    div.innerText = '...';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('sru-typing-indicator');
    if (el) el.remove();
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    sendBtn.disabled = true;
    showTyping();

    try {
      const resp = await fetch('/api/chat/message/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ message: text }),
      });
      const data = await resp.json();
      hideTyping();
      addMessage(data.reply || 'Sorry, something went wrong.', 'bot');
    } catch (err) {
      hideTyping();
      addMessage('Network error talking to the assistant. Is the Django server running?', 'bot');
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });
})();
