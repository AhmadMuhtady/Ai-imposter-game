from input_and_validation import user_input
from players import setup_players
from game_logic import add_clue,prepare_player_context
from ai_models import generate_clue

clues = []

category,secret_word = user_input('food','burger')
players,imposter = setup_players(secret_word,category)



for player in players:
    rejected_clues = []
    name = player['name']
    
    for _ in range(3):
        clue = generate_clue(output)
        try:
            output = prepare_player_context(player,clues,rejected_clues)
            add_clue(clues,name,clue,secret_word)
            break
        except ValueError as e:
            rejected_clues.append({'rejected_clue': clue,'Error': str(e)})
            print(f"Error: {e}")
    else:
        raise RuntimeError(f'{name} failed to generate a valid clue after 3 attempts')


print(clues)
