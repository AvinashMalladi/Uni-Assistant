# SR University Agentic AI Chatbot — Django + Google AI Studio (Gemini)

An agentic, RAG-powered chatbot embedded in a dummy SR University student portal.
It cross-questions students for missing details (year / semester / department)
before answering data-style queries, using a genuine **epsilon-greedy
reinforcement-learning bandit** to learn the most efficient question order over
time — and answers open-ended policy questions via **RAG over the real SR
University Student Handbook**, using **Google AI Studio's Gemini API**.

---

## 1. Architecture

```
Browser (dummy portal + chat widget)
        |
        v
Django views (portal app)  <-- static HTML/CSS/JS portal pages
        |
        v
/api/chat/message/  (chatbot app)
        |
        v
dialogue_manager.py
   |-- intent detection (result query vs. general question)
   |-- slot-filling state machine (year / semester / department)
   |     |--> bandit.py  (epsilon-greedy: learns best slot-asking order)
   |--> SemesterResult DB lookup (dummy pass-percentage data)
   |
   `-- RAG pipeline for open-ended handbook questions
         |-- retriever.py   (keyword TF overlap, or Gemini embeddings if API key set)
         `-- gemini_client.py  (Google AI Studio Gemini generation)
```

  ```mermaid
  flowchart TB
    external["SR University Portal / External Site"] -->|"embed-widget.js"| widget["Chat Widget"]
    widget -->|"CORS + X-Widget-Key"| api["Django Backend /api/chat/widget-message/"]
    portal["Django Dummy Portal"] -->|"/api/chat/message/"| api

    api --> dialogue["Agentic Dialogue Manager\nSlot filling: department / year / semester"]
    dialogue --> bandit["Multi-Armed Bandit\nEpsilon-greedy question order"]
    dialogue --> results["SemesterResult\nDummy pass-percentage lookup"]
    dialogue --> rag["RAG Pipeline\nHandbook retrieval"]
    rag --> retriever["retriever.py\nKeyword overlap or embeddings"]
    rag --> gemini["gemini_client.py\nAnswer generation"]
    gemini -->|"Google AI Studio API"| model["Gemini model"]
  ```

  ### Request pipelines

  ```mermaid
  flowchart LR
    question["Student question"] --> intent{"Intent"}
    intent -->|"Result query"| slots["Extract department, year, semester"]
    slots --> missing{"Missing slots?"}
    missing -->|"Yes"| ask["Bandit selects next follow-up question"]
    ask --> question
    missing -->|"No"| lookup["Query SemesterResult"]
    lookup --> answer["Return result answer"]

    intent -->|"Handbook question"| search["Retrieve handbook chunks"]
    search --> context["Build grounded prompt"]
    context --> generate["Gemini generation"]
    generate --> answer
  ```

  ### Deployment pipeline

  ```mermaid
  flowchart LR
    code["GitHub repository"] --> build["Render build\npip install -r requirements.txt"]
    build --> migrate["Deploy service\nrun migrations and seed data"]
    migrate --> health["check_gemini"]
    health --> live["gunicorn config.wsgi\nLive Django API + widget"]
  ```

## 2. Why this counts as "RL", honestly

A full RL agent (PPO/Q-learning trained over thousands of episodes) is not
feasible to train overnight on a single handbook — that's a fair thing to say
if a judge pushes on it. What **is** genuinely implemented here is an
**epsilon-greedy multi-armed bandit** (`chatbot/services/bandit.py`):

- **State** = the set of slots still missing (department / year / semester)
- **Action** = which slot to ask for next
- **Reward** = `1 / turns_taken` once the conversation resolves (faster
  resolution = higher reward)
- **Learning**: after every completed chat session, the Q-value
  (`avg_reward`) for the (state, action) pair is updated incrementally,
  stored in the `BanditArm` model (visible in Django admin at `/admin/`)

Over many conversations, the bot's question order adapts based on real
usage data — that's online reinforcement learning, just scoped appropriately
for an overnight build instead of faked.

## 3. Setup

```bash
cd university_portal
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

# Get a free key from https://aistudio.google.com/app/apikey
export GOOGLE_API_KEY="your-key-here"     # or `set` on Windows cmd

python manage.py migrate
python manage.py seed_data              # populates dummy departments + pass %
python manage.py check_gemini           # IMPORTANT: verify your key/model works
python manage.py createsuperuser        # optional, for /admin/
python manage.py runserver
```

**Run `check_gemini` before your demo, every time you open a new terminal.**
It calls the real Gemini API once and tells you plainly whether your key and
model are working, instead of finding out mid-demo when the bot silently
falls back to dumping raw handbook text. Google deprecates model names
often (gemini-2.0-flash was shut down June 1, 2026) — if `check_gemini`
fails on the configured model, try `gemini-3.6-flash` as an
alternative:
```powershell
$env:GEMINI_MODEL="gemini-3.6-flash"
python manage.py check_gemini
```

Visit **http://127.0.0.1:8000/** — the dummy portal — and click the 🤖 icon
bottom-right to chat.

> **No API key?** The app still runs. `gemini_client.py` and
> `retriever.py` both degrade gracefully to a keyword-search fallback so the
> slot-filling / bandit demo still works end-to-end without a live key —
> only the final "polished natural-language answer" step is skipped in
> favor of returning the raw retrieved handbook text.

## 4. Demo script (suggested)

1. Open the portal home page — show it's a real (dummy) university site,
   not just a chat window.
2. Click the chatbot, ask: **"What is the pass percentage this semester?"**
   → bot asks department → year → semester (or a different order — that's
   the bandit) → gives the dummy pass % + cites the handbook's 45%
   minimum-pass rule.
3. Ask the same style of question again in a new session — point out the
   bot may ask in a different order, and explain the bandit is optimizing
   this over time.
4. Open `/admin/` → `Bandit arms` — show the learned Q-values updating.
5. Ask an open-ended policy question: **"What happens if my attendance is
   68%?"** → RAG pulls the condonation-fee clause from the real handbook →
   Gemini answers using only that context.
6. Ask something NOT in the handbook (e.g. "What's the WiFi password?") →
   show it honestly says it doesn't know and points to the right contact,
   instead of hallucinating — a good responsible-AI talking point.

## 5. Project layout

```
university_portal/
  config/                  Django project settings/urls
  portal/                  Dummy university website (home, academics, results, about)
    models.py              Department, SemesterResult (dummy), Notice
    management/commands/seed_data.py
  chatbot/                 Agentic chatbot app
    models.py              BanditArm, ChatLog
    services/
      dialogue_manager.py  Intent detection + slot-filling state machine
      bandit.py            Epsilon-greedy RL bandit
      retriever.py         RAG retrieval (keyword fallback / Gemini embeddings)
      gemini_client.py     Google AI Studio Gemini generation call
    views.py                POST /api/chat/message/
  data/student_handbook.txt Real SR University handbook, cleaned for RAG
```

## 6. Known limitations (be upfront about these if asked)

- Slot extraction from free text is regex/keyword-based, not a full NLU
  model — good enough for a live demo, but a production version would use
  Gemini function-calling for extraction too.
- The RL bandit optimizes question *order*, not the underlying NLU or
  answer quality — that's a deliberately scoped, honest claim.
- `SemesterResult` data is randomly seeded dummy data, not real SRAAP data.
