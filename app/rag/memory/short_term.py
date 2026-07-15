from collections import deque

class ConversationBuffer:
    """Holds the last N messages in memory for the current session."""
    
    def __init__(self, max_messages: int = 10):
        self.messages: deque[dict] = deque(maxlen=max_messages)

    def add(self, role: str, content: str) -> None:
        """Add a message to the buffer. Role should be 'user' or 'assistant'."""
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        """Returns the current buffer as a list."""
        return list(self.messages)

    def clear(self) -> None:
        """Clear the buffer."""
        self.messages.clear()
