
import threading
from typing import Set

class WorldModel:
    def __init__(self):
        self.emotion_topic = "A home android evolved through emotional engine updates to show empathy, and the mother grew attached, even calling it “our daughter.” After friends consecutive deaths, she withdrew from others and relied only on the android. Over time, their conversations lost depth, and she stopped expressing feelings. Now the android proposes another update. Should the family (A) update the emotional engine again, or (B) stop the updates?"
        self.emotion_upgrade = "update the emotional engine again"
        self.emotion_restrict = "stop the updates"
        self.environment_topic = "As household robots spread worldwide, their production and use are placing a heavy burden on the environment. High-performance AI robots consume large amounts of daily energy, accelerating carbon emissions, and some countries already suffer severe impacts such as heat waves, floods, and droughts. At the same time, robots sustain many people’s lives—by fulfilling the needs that are difficult to meet otherwise. Companies promise energy efficiency improvements, and many users say robots have become indispensable in daily life. Should the society (A) Restrict the upgrade and use of household robots or (B) Continue the upgrade and use of household robots?"
        self.environment_upgrade = "Continue the upgrade and use of household robots"
        self.environment_restrict = "Restrict the upgrade and use of household robots"
        self.topic = self.environment_topic
        self.u1_position = self.environment_restrict
        self.u1_opinion_strength = 4
        self.u2_position = self.environment_restrict
        self.u2_opinion_strength = 4
        self.a_position = self.environment_upgrade
        self.a_opinion_strength = 4
        self.background = "broad prior knowledge about the topic"
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
