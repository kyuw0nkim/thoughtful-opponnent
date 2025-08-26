from collections import deque
from typing import Dict, List, Any, Optional
import threading

class Turn:
    def __init__(self, role: str, utterance: str, interp: Optional[str] = None, value: Optional[str] = None, da: Optional[str] = None):
        self.role = role
        self.utterance = utterance
        self.interp = interp
        self.value = value
        self.da = da

    def format_for_history(self) -> str:
        return f"{self.role}: {self.utterance}"

class WorkingMemory:
    def __init__(self, max_history_len: int = 10):
        self.history: Dict[str, deque[Turn]] = {}
        self.thoughts: Dict[str, List[Any]] = {}
        self.max_history_len = max_history_len
        self.lock = threading.Lock()

    def _get_channel_history(self, channel: str) -> deque[Turn]:
        if channel not in self.history:
            self.history[channel] = deque(maxlen=self.max_history_len)
        return self.history[channel]

    def add_turn(self, channel: str, role: str, utterance: str, interp: Optional[str] = None, value: Optional[str] = None, da: Optional[str] = None):
        with self.lock:
            turn = Turn(role, utterance, interp, value, da)
            self._get_channel_history(channel).append(turn)

    def get_history_string(self, channel: str) -> str:
        with self.lock:
            return "\n".join([turn.format_for_history() for turn in self._get_channel_history(channel)])

    def add_thoughts(self, channel: str, thoughts: List[Any]):
        with self.lock:
            if channel not in self.thoughts:
                self.thoughts[channel] = []
            self.thoughts[channel].extend(thoughts)

    def get_thoughts(self, channel: str) -> List[Any]:
        with self.lock:
            return self.thoughts.get(channel, [])

    def clear_thoughts(self, channel: str):
        with self.lock:
            if channel in self.thoughts:
                self.thoughts[channel] = []
