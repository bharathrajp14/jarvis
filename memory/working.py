# memory/working.py

class WorkingMemory:
    def __init__(self, max_tokens: int = 100_000):
        self.history: list[dict] = []
        self.max_tokens = max_tokens

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._trim()

    def _trim(self):
        # Rough token estimate: 1 token ~ 4 chars
        if not self.history:
            return
        root_msg = self.history[0]
        while sum(len(m["content"]) for m in self.history) / 4 > self.max_tokens:
            self.history.pop(0)
        if root_msg and root_msg not in self.history:
            self.history.insert(0, root_msg)

    def trim(self, max_turns: int = 10):
        """Trim working memory to max_turns while pinning the root user goal turn."""
        if len(self.history) > max_turns:
            root_msg = self.history[0]
            self.history = self.history[-max_turns:]
            if root_msg and root_msg not in self.history:
                self.history.insert(0, root_msg)

    def get(self) -> list[dict]:
        return self.history
