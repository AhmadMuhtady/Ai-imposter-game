import random


def setup_players(secret_word):
    players = [{'name': 'ChatGPT'},{'name': 'Claude'},{'name': 'Gemini'},{'name': 'Groq'},{'name': 'Cerebras'}]
    imposter = random.choice(players)
    imposter_name = imposter['name']
    for player in players:
        if player['name'] == imposter['name']:
            player['secret_word'] = 'Imposter'
        else:
            player['secret_word'] = secret_word

    random.shuffle(players)


    return players,imposter_name