from app.prompts.loader import load_prompt
from app.schemas import ChatMessage

# The text lives in router.md.
ROUTER_SYSTEM_PROMPT = load_prompt("router.md")

# Enough context to notice a drift between branches without resending the whole chat.
ROUTER_WINDOW = 3


def _strip_tags(text: str) -> str:
    # Remove closing tags from user text so it cannot break out of its block.
    return text.replace("</post>", "").replace("</conversation>", "")


def build_router_input(post: str, history: list[ChatMessage]) -> str:
    lines = [
        f"{'Person' if m.role == 'user' else 'Assistant'}: {_strip_tags(m.text)}"
        for m in history[-ROUTER_WINDOW:]
    ]
    conversation = "\n".join(lines)
    return (
        f"<post>\n{_strip_tags(post)}\n</post>\n"
        f"<conversation>\n{conversation}\n</conversation>"
    )
