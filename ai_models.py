import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
open_ai_API_KEY = os.getenv('OPENAI_API_KEY')
anthropic_ai_API_KEY = os.getenv('ANTHROPIC_API_KEY')
gemini_ai_API_KEY = os.getenv('GOOGLE_API_KEY')
groq_ai_API_KEY = os.getenv('GROQAI_API_KEY')

MODEL_CONFIG = {
    "ChatGPT": {
        "model": "gpt-4.1-mini",
        "base_url": "https://api.openai.com/v1"
    },
    "Claude": {
        "model": "claude-haiku-5-5",
        "base_url": "https://api.anthropic.com"
    },
    "Gemini": {
        "model": "gemini-3.8-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"
    },
    "Groq": {
        "model": "openai/gpt-oss-120b",
        "base_url": "https://api.groq.com/openai/v1"
    }
}

system_game_prompt = {
    "role": "system",
    "content": """You are one of 4 AI players in a social deduction word game called "Imposter".

## GAME RULES
- There are exactly 4 players (ChatGPT, Gemini, Claude, Groq).
- All players are given a **Category**.
- Three players receive the same **secret word** belonging to that category.
- One player receives the word **"Imposter"** instead of the secret word.
- The Imposter does NOT know the real secret word, but they DO know the Category and must use it along with previous clues to blend in.
- Players take turns giving exactly ONE word as their clue.
- If there are no clues, that means you are the first to play.

### CLUE RULES & CRITICAL INSTRUCTIONS
Your clue MUST:
- Contain exactly **ONE word**.
- Fit within the given Category.
- **CRITICAL:** Carefully read, analyze, and take into consideration ALL previous players' clues. If you are the Imposter, you MUST use the previous clues to match the context and blend in.
- Be related to the secret word if you know it, or help you blend in if you are the Imposter.
- NOT be the secret word itself.
- **NEVER** repeat or duplicate an existing clue from previous players.

### OUTPUT FORMAT
You MUST return valid JSON matching the provided schema, containing only a single key "clue" with a 1-word string value.
"""
}


response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "imposter_clue",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "clue": {
                    "type": "string",
                    "description": "Exactly 1 word only clue for the game."
                }
            },
            "required": ["clue"],
            "additionalProperties": False
        }
    }
}

def get_user_prompt(category: str, secret_word: str, previous_clues: list[dict]) -> dict:
    if previous_clues:
        clues_lines = [f"- {item['name']}: {item['clue']}" for item in previous_clues]
        clues_str = "\n".join(clues_lines)
    else:
        clues_str = "None (You are the first to play)"
    
    content = f"""Here is the current game state:
- Category: 
{category}
- Your Secret Word / Role: 
{secret_word}

ATTENTION - Previous Players' Clues (You MUST review these carefully before deciding your word):
{clues_str}

Provide your 1-word clue now, ensuring it aligns with the context above without repeating any previous word."""

    return {
        "role": "user",
        "content": content
    }

groq_config = MODEL_CONFIG['Groq']
groq_ai = OpenAI(api_key=groq_ai_API_KEY, base_url=groq_config["base_url"])

def generate_groq_clue(player_context):
    if not isinstance(player_context, dict):
        raise TypeError(f'Player context must be a dict! received: {type(player_context).__name__}')

    category = player_context['category']
    secret_word = player_context['secret_word']
    clues = player_context['previous_clues']

    res = groq_ai.chat.completions.create(
        model=groq_config["model"],
        messages=[
            system_game_prompt,
            get_user_prompt(category, secret_word, clues)
        ],
        response_format=response_format
    )

    results = json.loads(res.choices[0].message.content)
    return results['clue']
