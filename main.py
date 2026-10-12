from input_and_validation import user_input
from players import setup_players
from game_logic import add_clue,prepare_player_context
from ai_models import generate_clue

clues = []
category,secret_word = user_input('food','burger')
players,imposter = setup_players(secret_word,category)



for player in players:
    output = prepare_player_context(player,clues)
    if player['name'] == 'Groq':
        clue = generate_clue(output)
        add_clue(clues,player['name'],clue)


print(clues)