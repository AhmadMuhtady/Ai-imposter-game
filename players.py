import random


def setup_players(secret_word,category):
    players = [{'name': 'ChatGPT'},{'name': 'Claude'},{'name': 'Gemini'},{'name': 'Groq'}]
    imposter = random.choice(players)
    imposter_name = imposter['name']
    for player in players:
        player['category'] = category
        if player['name'] == imposter['name']:
            player['secret_word'] = 'Imposter'
        else:
            player['secret_word'] = secret_word

    random.shuffle(players)


    return players,imposter_name