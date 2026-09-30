from app.prompts.loader import load_prompt

# The text lives in classifier.md.
CLASSIFIER_SYSTEM_PROMPT = load_prompt("classifier.md")
