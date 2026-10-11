def add_clue(clues,player_name,clue):
    if not isinstance(clues,list):
        raise TypeError(f'Clues Must be a List! recieved: {type(clues).__name__}')
    
    if not isinstance(player_name,str):
        raise TypeError(f'Player Name must be a string! recieved: {type(player_name).__name__}')
    
    if not isinstance(clue,str):
        raise TypeError(f'Clue must be a string! recieved: {type(clue).__name__}')

    cleaned_name = player_name.strip()
    cleaned_clue = clue.strip()
    
    if not cleaned_name:
        raise ValueError(f'Player Name must be valid! recieved: {player_name}')
    
    if not cleaned_clue:
        raise ValueError(f'Clue must be valid! recieved: {clue}')
    
    if len(cleaned_clue.split()) > 1:
        raise ValueError('Clue Must be 1 word only')
    
    prev_clues = [c['clue'].casefold() for c in clues]
    
    if cleaned_clue.casefold() in prev_clues:
        raise ValueError('same Clue already been given by another player!')
    
    cleaned = {'name': cleaned_name, 'clue': cleaned_clue}
    
    clues.append(cleaned)

