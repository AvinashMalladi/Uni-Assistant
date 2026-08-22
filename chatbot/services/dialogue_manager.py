"""
Agentic dialogue manager: detects intent, and for queries that need
structured data (e.g. "pass percentage this semester"), cross-questions the
student for missing slots (year / semester / department) -- similar to how
ChatGPT's research mode clarifies scope before answering -- using the
bandit (services/bandit.py) to learn the most efficient question order.

For open-ended handbook questions, it instead runs a RAG pipeline
(retriever.py + gemini_client.py) over the student handbook.
"""
import re

from . import bandit
from .gemini_client import generate_answer
from .retriever import retrieve_context

RESULT_KEYWORDS = [
    'pass percentage', 'pass %', 'pass rate', 'result', 'results',
    'sgpa', 'cgpa', 'grade distribution', 'how many passed', 'failure rate',
]
REQUIRED_SLOTS = ['department', 'year', 'semester']

DEPARTMENTS = {
    'cse': 'CSE', 'computer science': 'CSE', 'cs': 'CSE', 'ai': 'CSE', 'csai': 'CSE',
    'ece': 'ECE', 'electronics': 'ECE',
    'eee': 'EEE', 'electrical': 'EEE',
    'mech': 'MECH', 'mechanical': 'MECH',
    'civil': 'CIVIL',
}
YEAR_WORDS = {
    'first': 1, '1st': 1, 'one': 1,
    'second': 2, '2nd': 2, 'two': 2,
    'third': 3, '3rd': 3, 'three': 3,
    'fourth': 4, '4th': 4, 'four': 4,
}
SEM_WORDS = {'odd': 1, 'even': 2, 'first': 1, 'second': 2, '1': 1, '2': 2}

SLOT_QUESTIONS = {
    'year': "Sure — which year are you in? (1st / 2nd / 3rd / 4th)",
    'semester': "Got it. Odd semester or even semester? (1 = odd, 2 = even)",
    'department': "And which department — CSE, ECE, EEE, MECH or CIVIL?",
}


def detect_intent(message):
    m = message.lower()
    if any(k in m for k in RESULT_KEYWORDS):
        return 'result_query'
    return 'general_query'


def extract_slots_from_text(text, expected_slot=None):
    t = f" {text.lower()} "
    found = {}

    for word, dept in DEPARTMENTS.items():
        if re.search(rf'\b{re.escape(word)}\b', t):
            found['department'] = dept
            break

    for word, year in YEAR_WORDS.items():
        if re.search(rf'\b{re.escape(word)}\b', t) and ('year' in t or expected_slot == 'year' or word.isdigit()):
            found['year'] = year
            break
    if 'year' not in found:
        m = re.search(r'\b([1-4])(?:st|nd|rd|th)?\s*year\b', t)
        if m:
            found['year'] = int(m.group(1))

    if re.search(r'\bodd\b', t):
        found['semester'] = 1
    elif re.search(r'\beven\b', t):
        found['semester'] = 2
    elif expected_slot == 'semester':
        m = re.search(r'\b([1-2])\b', t)
        if m:
            found['semester'] = int(m.group(1))

    return found


def _answer_result_query(slots):
    from portal.models import SemesterResult  # local import avoids app-loading order issues

    dept, year, sem = slots.get('department'), slots.get('year'), slots.get('semester')
    try:
        rec = SemesterResult.objects.get(department=dept, year=year, semester=sem)
        return (
            f"For {dept}, Year {year}, Semester {sem}: the pass percentage is "
            f"{rec.pass_percentage}% (based on {rec.total_students} students). "
            f"Reminder from the handbook — minimum 45% aggregate is required to pass a UG course, "
            f"and 75% attendance is required just to be eligible to sit the End Semester Exam."
        )
    except SemesterResult.DoesNotExist:
        return (
            f"I don't have published results yet for {dept}, Year {year}, Semester {sem}. "
            f"Once SRAAP publishes them they'll show on the Results page — or you can contact "
            f"the Examination Cell (Mr. K. Kiran Babu, examcell@sru.edu.in)."
        )


def handle_message(session, user_message):
    state = session.get('dialogue_state')

    # --- Mid-slot-filling: this message is (probably) the answer to a pending question ---
    if state and state.get('intent') == 'result_query' and not state.get('resolved'):
        pending = state['pending_slot']
        extracted = extract_slots_from_text(user_message, expected_slot=pending)

        if pending in extracted:
            state['slots'][pending] = extracted[pending]
        else:
            for k, v in extracted.items():
                state['slots'].setdefault(k, v)
            if pending not in state['slots']:
                session['dialogue_state'] = state
                session.modified = True
                return f"Sorry, I didn't quite catch that. {SLOT_QUESTIONS[pending]}"

        state['turns'] += 1
        missing = [s for s in REQUIRED_SLOTS if s not in state['slots']]

        if missing:
            next_slot = bandit.choose_slot(missing)
            state['pending_slot'] = next_slot
            state['bandit_trace'].append({'context': sorted(missing), 'action': next_slot})
            session['dialogue_state'] = state
            session.modified = True
            return SLOT_QUESTIONS[next_slot]

        # all slots filled -> reward the bandit for this session's question order, then answer
        reward = 1.0 / state['turns']
        for step in state['bandit_trace']:
            bandit.update(step['context'], step['action'], reward)
        session['dialogue_state'] = None
        session.modified = True
        return _answer_result_query(state['slots'])

    # --- Fresh message ---
    intent = detect_intent(user_message)

    if intent == 'result_query':
        slots = extract_slots_from_text(user_message)
        missing = [s for s in REQUIRED_SLOTS if s not in slots]
        if not missing:
            return _answer_result_query(slots)

        next_slot = bandit.choose_slot(missing)
        session['dialogue_state'] = {
            'intent': 'result_query',
            'slots': slots,
            'pending_slot': next_slot,
            'turns': 1,
            'resolved': False,
            'bandit_trace': [{'context': sorted(missing), 'action': next_slot}],
        }
        session.modified = True
        return SLOT_QUESTIONS[next_slot]

    # --- General handbook question -> RAG over student_handbook.txt ---
    context_chunks = retrieve_context(user_message)
    return generate_answer(user_message, context_chunks)
