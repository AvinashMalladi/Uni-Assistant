from django.db import models


class BanditArm(models.Model):
    """Epsilon-greedy multi-armed bandit statistics.

    context = sorted, comma-joined list of slot names still missing at the
              moment a question was asked (e.g. "department,semester,year")
    action  = which slot was asked for next (e.g. "year")

    The bandit learns, over many chat sessions, which slot is most efficient
    to ask for first (i.e. leads to the fewest follow-up turns), and adapts
    its questioning order accordingly. This is the "RL talking point" for
    the demo: a real online-learning feedback loop, not just a canned
    if/else script.
    """
    context = models.CharField(max_length=200)
    action = models.CharField(max_length=50)
    count = models.PositiveIntegerField(default=0)
    avg_reward = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('context', 'action')

    def __str__(self):
        return f"[{self.context}] -> {self.action} (n={self.count}, avg_r={self.avg_reward:.3f})"


class ChatSessionState(models.Model):
    """Dialogue state for cross-origin widget callers (e.g. an embedded
    WordPress widget), keyed by a client-generated session_id instead of
    Django's session cookie -- third-party cookies from an iframe/script on
    another domain are unreliable, so the widget generates its own id
    (stored in localStorage) and sends it explicitly on every request.
    """
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    state_json = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"state for {self.session_id[:8]}"


class ChatLog(models.Model):
    session_key = models.CharField(max_length=64, db_index=True)
    role = models.CharField(max_length=10)  # 'user' or 'bot'
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.session_key[:8]}] {self.role}: {self.message[:40]}"
