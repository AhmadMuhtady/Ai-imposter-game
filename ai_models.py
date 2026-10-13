import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv(override=True)
open_ai_API_KEY = os.getenv('OPENAI_API_KEY')
anthropic_ai_API_KEY = os.getenv('ANTHROPIC_API_KEY')
gemini_ai_API_KEY = os.getenv('GOOGLE_API_KEY')
groq_ai_API_KEY = os.getenv('GROQAI_API_KEY')

class InvalidAIResponseError(ValueError):
    """Raised when an AI provider returns malformed JSON or an invalid response structure."""
    pass

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


voting_system_prompt = {
    "role": "system",
    "content": """You are one of four AI players (ChatGPT, Claude, Gemini, Groq) in the VOTING phase of the Imposter word game. Exactly one player is the Imposter. Every player has submitted one public clue.

## HOW TO JUDGE CLUES
A clue is evidence about a SPECIFIC secret word, not a test of how specific or impressive the clue sounds.
- If you received the real secret word, use that exact word as your PRIVATE reference. For each other player's clue, ask: "Could someone who knows this word reasonably give this clue?" Consider associations, features, context, functions, pop-culture references, and wordplay.
- A short, general, or ambiguous clue is NOT automatically suspicious. Legitimate players often use broad clues to avoid revealing the answer. Do not punish a clue merely because it could describe many things.
- Conversely, a very specific clue is NOT proof of innocence: an Imposter may infer the answer from earlier clues and blend in.
- Compare all eligible players' clues together. Prioritize genuine contradictions, unrelated associations, or clues that point away from the shared answer. Use the category only as context, never as the sole standard.
- Do not invent a flaw. If every clue plausibly fits, make the most careful relative judgment you can; you still must cast exactly one vote.

## YOUR ROLE
- INNOCENT (you know the secret word): Vote for the eligible player whose clue is least compatible with the word you know. Think about all reasonable meanings before judging. Do not coordinate with other models or assume their votes.
- IMPOSTER (your assigned word is "Imposter"): You do not know the true secret word. Infer the likely subject from the category and public clues, then cast a plausible vote that helps you survive. Do not claim knowledge you don't have.

## VOTE AND EXPLANATION RULES
- Vote for exactly ONE name from the eligible candidates provided in the user message. Never vote for yourself.
- Give exactly ONE concise sentence supporting your choice, based on the public clues. Describe the clue's fit relative to the other clues, not simply its broadness.
- Do NOT reveal, quote, hint at by spelling, or directly name your private assigned word or role in your explanation. You may quote a public clue if useful, but not the secret answer.
- Do NOT fabricate contradictions or state as fact that a plausible clue is unrelated.
- Return ONLY a JSON object with exactly two string keys: "vote" and "reason". No markdown, extra keys, or surrounding text.

Example JSON format:
{
    "vote": "Gemini",
    "reason": "Gemini's clue fits the shared theme less convincingly than the other clues."
}
"""
}


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
    retry_feedback = voting_context.get('retry_feedback', '')
    
    if clues:
        clues_lines = [f"- {item['name']}: {item['clue']}" for item in clues]
        clues_str = "\n".join(clues_lines)
    else:
        clues_str = "None"
        
    if candidates:
        candidates_str = ", ".join(candidates)
    else:
        candidates_str = "None"
        
    imposter_hint = ""
    if secret_word == "Imposter":
        imposter_hint = "\n[HIDDEN NOTE: Psst... You are the Imposter! Stay smart and sneaky. Pick someone suspicious and frame them with a clever reason so they take the fall!]\n"

    feedback_section = f"\nATTENTION - RETRY WARNING: {retry_feedback}\n" if retry_feedback else ""

    content = f"""Here is the voting state:
- Your Name: 
{name}
- Your Assigned Word / Role: 
{secret_word}
- Category: 
{category}
{imposter_hint}{feedback_section}
All Players' Clues:
{clues_str}

Eligible Voting Candidates: {candidates_str}

Instruction: Follow your assigned role's voting objective. Select exactly one eligible candidate and provide a one-sentence explanation. 
CRITICAL RULE: DO NOT name, mention, or spell out your secret word ("{secret_word}") or role in your explanation. Base your suspicion strictly on the clues and category.

Return a JSON object containing exactly two keys: "vote" and "reason"."""

    return {
        "role": "user",
        "content": content
    }


groq_config = MODEL_CONFIG['Groq']
groq_ai = OpenAI(api_key=groq_ai_API_KEY, base_url=groq_config["base_url"])

open_ai_config = MODEL_CONFIG['ChatGPT']
open_ai = OpenAI(api_key=open_ai_API_KEY)

gemini_ai_config = MODEL_CONFIG['Gemini']
gemini_ai = OpenAI(api_key=gemini_ai_API_KEY, base_url=gemini_ai_config["base_url"])


claude_config = MODEL_CONFIG['Claude']
claude_ai = Anthropic(api_key=anthropic_ai_API_KEY)


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

    try:
        if res.choices:
            content = res.choices[0].message.content
        else:
            raise InvalidAIResponseError(f"API Error or Empty Response: {res.choices}")
        results = json.loads(content)
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        raise InvalidAIResponseError(f"Failed to parse JSON response from AI: {e}") from e

    if not isinstance(results, dict) or not isinstance(results.get('clue'), str):
        raise InvalidAIResponseError(f"Invalid response structure: expected a dict with a string 'clue', got {results}")

    return results['clue']

def generate_openai_clue(player_context):
    return generate_compatible_clue(player_context, open_ai, open_ai_config, strict_response_format)

def generate_groq_clue(player_context):
    return generate_compatible_clue(player_context, groq_ai, groq_config, groq_response_format)

def generate_gemini_clue(player_context):
    return generate_compatible_clue(player_context, gemini_ai, gemini_ai_config, strict_response_format)


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
            tool_input = block.input
            if not isinstance(tool_input, dict) or not isinstance(tool_input.get('clue'), str):
                raise InvalidAIResponseError(f"Invalid Claude tool response structure: expected dict with string 'clue', got {tool_input}")
            return tool_input['clue']

    raise InvalidAIResponseError("Claude failed to return a valid structured tool response.")

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

    try:
        if res.choices:
            content = res.choices[0].message.content
        else:
            raise InvalidAIResponseError(f"API Error or Empty Response: {res.choices}")
        results = json.loads(content)
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        raise InvalidAIResponseError(f"Failed to parse JSON voting response from AI: {e}") from e

    if not isinstance(results, dict) or not isinstance(results.get("vote"), str) or not isinstance(results.get("reason"), str):
        raise InvalidAIResponseError(f"Invalid voting response structure: expected dict with string 'vote' and string 'reason', got {results}")
    
    return {
        "vote": results.get("vote"),
        "reason": results.get("reason")
    }

def generate_openai_vote(voting_context):
    return generate_compatible_vote(voting_context, open_ai, open_ai_config, strict_voting_response_format)

def generate_gemini_vote(voting_context):
    return generate_compatible_vote(voting_context, gemini_ai, gemini_ai_config, strict_voting_response_format)

def generate_groq_vote(voting_context):
    return generate_compatible_vote(voting_context, groq_ai, groq_config, groq_response_format)


def generate_claude_vote(voting_context):
    if not isinstance(voting_context, dict):
        raise TypeError(f'Voting context must be a dict! received: {type(voting_context).__name__}')

    user_prompt = get_voting_prompt(voting_context)

    tools = [{
        "name": "submit_vote",
        "description": "Submit your vote and reasoning for the Imposter game.",
        "input_schema": {
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
            "required": ["vote", "reason"]
        }
    }]

    response = claude_ai.messages.create(
        model=claude_config['model'],
        max_tokens=150,
        system=voting_system_prompt['content'],
        messages=[
            {"role": user_prompt["role"], "content": user_prompt["content"]}
        ],
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_vote"}
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_vote":
            tool_input = block.input
            if not isinstance(tool_input, dict) or not isinstance(tool_input.get('vote'), str) or not isinstance(tool_input.get('reason'), str):
                raise InvalidAIResponseError(f"Invalid Claude tool voting response structure: expected dict with string 'vote' and string 'reason', got {tool_input}")
            return {
                "vote": tool_input['vote'],
                "reason": tool_input['reason']
            }

    raise InvalidAIResponseError("Claude failed to return a valid structured tool voting response.")

VOTING_GENERATORS = {
    "ChatGPT": generate_openai_vote,
    "Claude": generate_claude_vote,
    "Gemini": generate_gemini_vote,
    "Groq": generate_groq_vote,
}

def generate_vote(voting_context):
    name = voting_context['name']
    generator = VOTING_GENERATORS.get(name)
    if generator:
        return generator(voting_context)
    else:
        raise NotImplementedError(f'Unknown Model for voting! {name}')