
from input_and_validation import user_input
from players import setup_players
from game_logic import add_clue,prepare_player_context


clues = []
outputs = []
category,secret_word = user_input('food','burger')
players,imposter = setup_players(secret_word,category)

test_clues = ["Road","Engine", "Wheels","Speed","Transport"]
print(players)
for player, clue in zip(players, test_clues):
    output = prepare_player_context(player,clues)
    outputs.append(output)
    add_clue(clues,player['name'],clue)




for out in outputs:
    print(out)
    print('**********')