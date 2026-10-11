
from input_and_validation import user_input
from players import setup_players



category,secret_word = user_input('food','burger')
players,imposter = setup_players(secret_word)

