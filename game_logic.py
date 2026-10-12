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

def prepare_voting_context(player,clues):
    player_name = player['name']
    player_word = player['secret_word']
    player_category = player['category']

    output  = {
    'name': player_name,
    'secret_word': player_word,
    'category': player_category,
    'clues': clues.copy(),
    'candidates': [p['name'] for p in clues if p['name'] != player_name]
    }

    return output


def add_vote(votes, voter_name, vote_result, candidates):
    if not isinstance(votes, list):
        raise TypeError(f'Votes must be a list! Received: {type(votes).__name__}')
    
    if not isinstance(voter_name, str):
        raise TypeError(f'Voter name must be a string! Received: {type(voter_name).__name__}')
    
    if not isinstance(vote_result, dict):
        raise TypeError(f'Vote result must be a dict! Received: {type(vote_result).__name__}')

    if not isinstance(candidates, list):
        raise TypeError(f'Candidates must be a list! Received: {type(candidates).__name__}')

    cleaned_name = voter_name.strip()
    if not cleaned_name:
        raise ValueError(f'Voter name must be valid! Received: {voter_name}')

    
    for existing in votes:
        if existing.get('name', '').casefold() == cleaned_name.casefold():
            raise ValueError(f'Player {cleaned_name} has already voted!')

    # Safe checking and stripping for vote and reason
    raw_vote = vote_result.get('vote')
    raw_reason = vote_result.get('reason')

    if not isinstance(raw_vote, str):
        raise ValueError(f'Vote must be a string! Received: {type(raw_vote).__name__}')
    if not isinstance(raw_reason, str):
        raise ValueError(f'Reason must be a string! Received: {type(raw_reason).__name__}')

    cleaned_vote = raw_vote.strip()
    cleaned_reason = raw_reason.strip()
    
    if not cleaned_vote:
        raise ValueError('Vote cannot be empty!')
    
    if not cleaned_reason:
        raise ValueError('Reason cannot be empty!')
    

    sentences = [s.strip() for s in cleaned_reason.split('.') if s.strip()]
    if len(sentences) > 1:
        raise ValueError('Reason must be 1 sentence only')
    
  
    if cleaned_name.casefold() == cleaned_vote.casefold():
        raise ValueError('You cannot vote for yourself!')
    

    matched_candidate = None
    for candidate in candidates:
        if candidate.strip().casefold() == cleaned_vote.casefold():
            matched_candidate = candidate.strip()
            break

    if not matched_candidate:
        raise ValueError(f'Invalid vote target "{cleaned_vote}". Must be one of the eligible candidates: {candidates}')


    clean_vote = {
        'name': cleaned_name, 
        'vote': matched_candidate, 
        'reason': cleaned_reason
    }
    
    votes.append(clean_vote)

