import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic  # Native Anthropic SDK

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
        "model": "claude-haiku-5-5"
    },
    "Gemini": {
        "model": "gemini-2.5-flash",
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
You MUST return a valid JSON object containing only a single key "clue" with a 1-word string value. Example:
{
    "clue": "your_one_word_here"
}
"""
}

# Voting System Prompt (Imposter instruction removed as requested)
voting_system_prompt = {
    "role": "system",
    "content": """You are one of 4 AI players in the voting phase of a social deduction word game called "Imposter".

## VOTING RULES & OBJECTIVES
- There are exactly 4 players (ChatGPT, Gemini, Claude, Groq), and one of them is the **Imposter**.
- **If you are an Innocent Player** (you received a real secret word): Analyze all players' clues carefully. Identify who gave a suspicious or disconnected clue and vote for them. Provide a one-sentence reason explaining your suspicion.
- **CRITICAL RESTRICTIONS:**
  - You MUST NOT vote for yourself.
  - You MUST choose exactly one name from the provided list of eligible candidates.
  - Your explanation must be **exactly one sentence** long.
  - Never reveal your own assigned secret word or role in your explanation.

### OUTPUT FORMAT
You MUST return a valid JSON object containing exactly two keys:
1. "vote": A string containing the exact name of the chosen candidate.
2. "reason": A string containing a one-sentence explanation for your vote.

Example:
{
    "vote": "Gemini",
    "reason": "Gemini's clue was too vague and disconnected from the core theme."
}
"""
}

# Strict JSON Schema for OpenAI and Gemini clue generation
strict_response_format = {
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

# Strict JSON Schema for OpenAI and Gemini voting
strict_voting_response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "imposter_vote",
        "strict": True,  
        "schema": {
            "type": "object",
            "properties": {
                "vote": {
                    "type": "string",
                    "description": "The exact name of the player you are voting for."
                },
                "reason": {
                    "type": "string",
                    "description": "A one-sentence explanation supporting your vote."
                }
            },
            "required": ["vote", "reason"],
            "additionalProperties": False
        }
    }
}

# Standard JSON object format for Groq to prevent validation crashes
groq_response_format = {
    "type": "json_object"
}

def get_user_prompt(category: str, secret_word: str, previous_clues: list[dict], retry_feedback: str = "") -> dict:
    if previous_clues:
        clues_lines = [f"- {item['name']}: {item['clue']}" for item in previous_clues]
        clues_str = "\n".join(clues_lines)
    else:
        clues_str = "None (You are the first to play)"
    
    feedback_section = f"\n{retry_feedback}\n" if retry_feedback else ""

    content = f"""Here is the current game state:
- Category: 
{category}
- Your Secret Word / Role: 
{secret_word}
{feedback_section}
ATTENTION - Previous Players' Clues (You MUST review these carefully before deciding your word):
{clues_str}

Provide your 1-word clue now as a JSON object with a single "clue" key."""

    return {
        "role": "user",
        "content": content
    }

def get_voting_prompt(voting_context):
    name = voting_context['name']
    secret_word = voting_context['secret_word']
    category = voting_context['category']
    clues = voting_context['clues']
    candidates = voting_context['candidates']
    
    if clues:
        clues_lines = [f"- {item['name']}: {item['clue']}" for item in clues]
        clues_str = "\n".join(clues_lines)
    else:
        clues_str = "None"
        
    if candidates:
        candidates_str = ", ".join(candidates)
    else:
        candidates_str = "None"
        
    # Secret sneaky note kept for the Imposter :p
    imposter_hint = ""
    if secret_word == "Imposter":
        imposter_hint = "\n[HIDDEN NOTE: Psst... You are the Imposter! Stay smart and sneaky. Pick someone suspicious and frame them with a clever reason so they take the fall!]\n"

    content = f"""Here is the voting state:
- Your Name: 
{name}
- Your Assigned Word / Role: 
{secret_word}
- Category: 
{category}
{imposter_hint}
All Players' Clues:
{clues_str}

Eligible Voting Candidates: {candidates_str}

Instruction: Follow your assigned role's voting objective. Select exactly one eligible candidate and provide a one-sentence explanation. Return a JSON object containing exactly two keys: "vote" and "reason"."""

    return {
        "role": "user",
        "content": content
    }

# Initialize Clients
groq_config = MODEL_CONFIG['Groq']
groq_ai = OpenAI(api_key=groq_ai_API_KEY, base_url=groq_config["base_url"])

open_ai_config = MODEL_CONFIG['ChatGPT']
open_ai = OpenAI(api_key=open_ai_API_KEY)

gemini_ai_config = MODEL_CONFIG['Gemini']
gemini_ai = OpenAI(api_key=gemini_ai_API_KEY, base_url=gemini_ai_config["base_url"])

# Native Anthropic Client for Claude
claude_config = MODEL_CONFIG['Claude']
claude_ai = Anthropic(api_key=anthropic_ai_API_KEY)

# Shared helper for OpenAI-compatible providers (Clues)
def generate_compatible_clue(player_context, client, model_config, custom_response_format):
    category = player_context['category']
    secret_word = player_context['secret_word']
    clues = player_context['previous_clues']
    retry_feedback = player_context.get('retry_feedback', '')

    res = client.chat.completions.create(
        model=model_config['model'],
        messages=[
            system_game_prompt,
            get_user_prompt(category, secret_word, clues, retry_feedback)
        ],
        response_format=custom_response_format
    )

    results = json.loads(res.choices[0].message.content)
    return results['clue']

def generate_openai_clue(player_context):
    return generate_compatible_clue(player_context, open_ai, open_ai_config, strict_response_format)

def generate_groq_clue(player_context):
    return generate_compatible_clue(player_context, groq_ai, groq_config, groq_response_format)

def generate_gemini_clue(player_context):
    return generate_compatible_clue(player_context, gemini_ai, gemini_ai_config, strict_response_format)

# Request-layer structured output enforcement for Claude via Tool Use (Clues)
def generate_claude_clue(player_context):
    if not isinstance(player_context, dict):
        raise TypeError(f'Player context must be a dict! received: {type(player_context).__name__}')

    category = player_context['category']
    secret_word = player_context['secret_word']
    clues = player_context['previous_clues']
    retry_feedback = player_context.get('retry_feedback', '')

    user_prompt = get_user_prompt(category, secret_word, clues, retry_feedback)

    tools = [{
        "name": "submit_clue",
        "description": "Submit the 1-word clue for the game.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clue": {
                    "type": "string",
                    "description": "Exactly 1 word only clue for the game."
                }
            },
            "required": ["clue"]
        }
    }]

    response = claude_ai.messages.create(
        model=claude_config['model'],
        max_tokens=100,
        system=system_game_prompt['content'],
        messages=[
            {"role": user_prompt["role"], "content": user_prompt["content"]}
        ],
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_clue"}
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_clue":
            return block.input['clue']

    raise ValueError("Claude failed to return a valid structured tool response.")

CLUE_GENERATORS = {
    "ChatGPT": generate_openai_clue,
    "Claude": generate_claude_clue,
    "Gemini": generate_gemini_clue,
    "Groq": generate_groq_clue,
}

def generate_clue(player_context):
    name = player_context['name']
    generator = CLUE_GENERATORS.get(name)
    if generator:
        return generator(player_context)
    else:
        raise NotImplementedError(f'Unknown Model! {name}')


def generate_compatible_vote(voting_context, client, model_config, custom_response_format):
    if not isinstance(voting_context, dict):
        raise TypeError(f'Voting context must be a dict! received: {type(voting_context).__name__}')

    res = client.chat.completions.create(
        model=model_config['model'],
        messages=[
            voting_system_prompt,
            get_voting_prompt(voting_context)
        ],
        response_format=custom_response_format
    )

    results = json.loads(res.choices[0].message.content)
    

    return {
        "vote": results["vote"],
        "reason": results["reason"]
    }