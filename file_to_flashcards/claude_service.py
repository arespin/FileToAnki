"""
Claude API integration for extracting flashcards from text.
"""

import json

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False


def check_anthropic_available():
    """Check if the anthropic package is installed."""
    if not ANTHROPIC_AVAILABLE:
        raise ImportError(
            "The anthropic package is not installed.\n"
            "Install it with: pip install anthropic"
        )


def extract_flashcards(text, api_key, max_cards=25):
    """
    Use Claude to extract flashcards from text.

    Args:
        text: The source text to analyze
        api_key: Anthropic API key
        max_cards: Maximum number of flashcards to generate

    Returns:
        List of dicts with 'front' and 'back' keys
    """
    check_anthropic_available()

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate if too long
    max_length = 50000
    if len(text) > max_length:
        text = text[:max_length] + "\n[Text truncated...]"

    prompt = f"""Analyze the following text and extract the {max_cards} most important facts, concepts, and pieces of information worth memorizing.

For each fact, create a flashcard with:
- "front": A clear, specific question or prompt
- "back": A concise, accurate answer

Guidelines:
- Focus on key concepts, definitions, important facts, dates, formulas, and relationships
- Questions should be specific and unambiguous
- Answers should be concise but complete
- Avoid trivial or obvious information
- Each card should test ONE concept

Return ONLY a valid JSON array of flashcard objects. No other text or explanation.
Format: [{{"front": "question", "back": "answer"}}, ...]

TEXT TO ANALYZE:
---
{text}
---

JSON flashcards:"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response (handle markdown code blocks)
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Find JSON array
    start = response_text.find('[')
    end = response_text.rfind(']') + 1
    if start != -1 and end > start:
        response_text = response_text[start:end]

    try:
        flashcards = json.loads(response_text)
        # Validate structure
        validated = []
        for card in flashcards:
            if isinstance(card, dict) and 'front' in card and 'back' in card:
                validated.append({
                    'front': str(card['front']),
                    'back': str(card['back'])
                })
        return validated
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Claude response: {str(e)}")
