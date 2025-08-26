
import threading
from typing import Set

class WorldModel:
    def __init__(self):
        self.u1_position = "update the emotional engine again"
        self.u1_opinion_strength = 1
        self.u2_position = "update the emotional engine again"
        self.u2_opinion_strength = 5
        self.a_position = "stop the updates"
        self.a_opinion_strength = 5
        self.background = "background information"
        self.topic = "A home android evolved through emotional engine updates to show empathy, and the mother grew attached, even calling it “our daughter.” After friends consecutive deaths, she withdrew from others and relied only on the android. Over time, their conversations lost depth, and she stopped expressing feelings. Now the android proposes another update. Should the family (A) update the emotional engine again, or (B) stop the updates?"
        self.value_space_set: Set[str] = set()
        self.lock = threading.Lock()

        self.ALL_VALUES = {
            "self-direction", "stimulation", "hedonism", "achievement", 
            "power", "security", "conformity", "tradition", 
            "benevolence", "universalism"
        }

    def add_value(self, value: str):
        with self.lock:
            self.value_space_set.add(value)

    def get_mentioned_values(self) -> str:
        with self.lock:
            return ", ".join(sorted(self.value_space_set)) if self.value_space_set else ""

    def get_unmentioned_values(self) -> str:
        with self.lock:
            unmentioned = self.ALL_VALUES - self.value_space_set
            return ", ".join(sorted(unmentioned)) if unmentioned else ""

    def update_agent_opinion_strength(self, new_strength: float):
        with self.lock:
            self.a_opinion_strength = new_strength
