def add_clue(clues,player_name,clue):
    if not isinstance(clues,list):
        raise TypeError(f'Clues Must be a List! recieved: {type(clues).__name__}')
    
    if not isinstance(player_name,str):
        raise TypeError(f'Player Name must be a string! recieved: {type(player_name).__name__}')
    
    if not isinstance(clue,str):
        raise TypeError(f'Clue must be a string! recieved: {type(clue).__name__}')
    
    if not player_name.strip():
        raise ValueError(f'Player Name must be valid! recieved: {player_name}')
    
    if not clue.strip():
        raise ValueError(f'Clue must be valid! recieved: {clue}')
    
    cleaned = {'name': player_name.strip(), 'clue': clue.strip()}
    
    clues.append(cleaned)

