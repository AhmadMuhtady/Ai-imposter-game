import json
import openai
import anthropic
from input_and_validation import user_input
from players import setup_players
from game_logic import add_clue, prepare_player_context, prepare_voting_context, add_vote, resolve_game
from ai_models import generate_clue, generate_vote

def run_clue_phase(players, secret_word):
    clues = []
    for player in players:
        rejected_clues = []
        name = player['name']
        
        for attempt in range(3):
            output = prepare_player_context(player, clues, rejected_clues)
            
            try:
                clue = generate_clue(output)
            except (openai.APIConnectionError, anthropic.APIConnectionError) as e:
                print(f"Connection Error for {name} on attempt {attempt + 1}: {e}")
                continue
            except (openai.AuthenticationError, anthropic.AuthenticationError) as e:
                raise RuntimeError(f"Authentication failed for {name}. Please verify your API keys.") from e
            except (openai.RateLimitError, anthropic.RateLimitError) as e:
                raise RuntimeError(f"Rate limit reached for {name}. Please check your quota or try again later.") from e
            except json.JSONDecodeError as e:
                print(f"Malformed JSON Error for {name} on attempt {attempt + 1}: {e}")
                continue
            
            try:
                add_clue(clues, name, clue, secret_word)
                break
            except ValueError as e:
                rejected_clues.append({'rejected_clue': clue, 'Error': str(e)})
                print(f"Validation Error for {name}: {e}")
        else:
            raise RuntimeError(f'{name} failed to generate a valid clue after 3 attempts')

    return clues
    
def run_voting_phase(players, clues):
    votes = []
    for player in players:
        name = player['name']
        for attempt in range(3):
            output = prepare_voting_context(player, clues)
            
            try:
                vote = generate_vote(output)
            except (openai.APIConnectionError, anthropic.APIConnectionError) as e:
                print(f"Connection Error for {name} on vote attempt {attempt + 1}: {e}")
                continue
            except (openai.AuthenticationError, anthropic.AuthenticationError) as e:
                raise RuntimeError(f"Authentication failed for {name}. Please verify your API keys.") from e
            except (openai.RateLimitError, anthropic.RateLimitError) as e:
                raise RuntimeError(f"Rate limit reached for {name}. Please check your quota or try again later.") from e
            except json.JSONDecodeError as e:
                print(f"Malformed JSON Error for {name} on vote attempt {attempt + 1}: {e}")
                continue

            try:
                add_vote(votes, name, vote, output['candidates'])
                break
            except ValueError as e:
                print(f"Error: {e}")
        else:
            raise RuntimeError(f'{name} failed to generate a valid vote after 3 attempts')
    
    return votes

def run_game(category, secret_word):
    category, secret_word = user_input(category, secret_word)
    players, imposter = setup_players(secret_word, category)
    clues = run_clue_phase(players, secret_word)
    votes = run_voting_phase(players, clues)
    results = resolve_game(players, votes, imposter)

    return {
        'category': category,
        'secret_word': secret_word,
        'players': players,
        'clues': clues,
        'votes': votes,
        'imposter': imposter,
        'results': results
    }