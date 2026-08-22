"""
Lightweight epsilon-greedy multi-armed bandit that learns the best ORDER to
ask clarifying (slot-filling) questions in, so the agent converges on the
fewest number of turns needed to resolve an ambiguous query like
"what's the pass percentage this semester?".

This is intentionally simple (no deep RL / PPO) but is a genuine online
reinforcement-learning feedback loop: state = set of missing slots,
action = which slot to ask for next, reward = 1 / turns_taken (higher for
faster resolutions), and Q-values (avg_reward) are updated incrementally
after every completed conversation.
"""
import random

from django.conf import settings

from ..models import BanditArm


def _context_key(missing_slots):
    return ",".join(sorted(missing_slots))


def choose_slot(missing_slots):
    """Pick which missing slot to ask for next."""
    if not missing_slots:
        return None
    if len(missing_slots) == 1:
        return missing_slots[0]

    epsilon = settings.BANDIT_EPSILON
    if random.random() < epsilon:
        return random.choice(missing_slots)

    context = _context_key(missing_slots)
    arms = {a.action: a for a in BanditArm.objects.filter(context=context, action__in=missing_slots)}

    best_slot, best_score = None, None
    for slot in missing_slots:
        arm = arms.get(slot)
        score = arm.avg_reward if arm else 0.0  # unseen slots default to 0 (neutral)
        if best_score is None or score > best_score:
            best_score, best_slot = score, slot
    return best_slot


def update(missing_slots_at_decision_time, action, reward):
    """Incrementally update the running average reward for (context, action)."""
    context = _context_key(missing_slots_at_decision_time)
    arm, _ = BanditArm.objects.get_or_create(context=context, action=action)
    arm.count += 1
    arm.avg_reward += (reward - arm.avg_reward) / arm.count
    arm.save(update_fields=['count', 'avg_reward'])
