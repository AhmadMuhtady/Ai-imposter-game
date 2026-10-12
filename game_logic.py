def add_clue(clues,player_name,clue,secret_word):
    if not isinstance(clues,list):
        raise TypeError(f'Clues Must be a List! recieved: {type(clues).__name__}')
    
    if not isinstance(player_name,str):
        raise TypeError(f'Player Name must be a string! recieved: {type(player_name).__name__}')
    
    if not isinstance(clue,str):
        raise TypeError(f'Clue must be a string! recieved: {type(clue).__name__}')

    if not isinstance(secret_word,str):
        raise TypeError(f'Secret word must be string! recieved: {type(secret_word).__name__}')

    cleaned_name = player_name.strip()
    cleaned_clue = clue.strip()
    cleaned_secret_word = secret_word.strip().casefold()
    
    if not cleaned_name:
        raise ValueError(f'Player Name must be valid! recieved: {player_name}')
    
    if not cleaned_clue:
        raise ValueError(f'Clue must be valid! recieved: {clue}')
    
    if len(cleaned_clue.split()) > 1:
        raise ValueError('Clue Must be 1 word only')
    
    if not cleaned_secret_word:
        raise ValueError(f'Secret word must be valid! recieved: {secret_word}')
    
    if cleaned_secret_word == cleaned_clue.casefold():
        raise ValueError('AI revealed the secret word!')
    
    prev_clues = [c['clue'].casefold() for c in clues]
    
    if cleaned_clue.casefold() in prev_clues:
        raise ValueError('same Clue already been given by another player!')
    
    cleaned = {'name': cleaned_name, 'clue': cleaned_clue}
    
    clues.append(cleaned)



def prepare_player_context(player,clues,rejected_clues):
    player_name = player['name']
    player_word = player['secret_word']
    player_category = player['category']

    output  = {
    'name': player_name,
    'secret_word': player_word,
    'category': player_category,
    'previous_clues': clues.copy(),
    'retry_feedback': ''
    }

    if rejected_clues:
        output['retry_feedback'] = 'Your previous clue was rejected. Choose a different, valid one-word clue. Do not repeat your previous response.'

    return output





