"""
Vercel Serverless Function: Extract Flashcards using Claude
"""

import json
from http.server import BaseHTTPRequestHandler
import anthropic


def extract_flashcards(text, api_key, max_cards=25):
    """Use Claude to extract flashcards from text."""
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

    # Extract JSON from response
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Find JSON array
    start = response_text.find('[')
    end = response_text.rfind(']') + 1
    if start != -1 and end > start:
        response_text = response_text[start:end]

    flashcards = json.loads(response_text)
    return flashcards


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        if not data.get('text'):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No text provided'}).encode())
            return

        if not data.get('api_key'):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No API key provided'}).encode())
            return

        try:
            flashcards = extract_flashcards(
                data['text'],
                data['api_key'],
                max_cards=data.get('max_cards', 25)
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'flashcards': flashcards,
                'count': len(flashcards)
            }).encode())

        except anthropic.AuthenticationError:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid API key'}).encode())

        except anthropic.RateLimitError:
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Rate limited. Please try again later.'}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
