def user_input(category, secret_word):
    if not isinstance(category, str):
        raise TypeError(f'Category must be a string! received: {type(category).__name__}')
    
    if not isinstance(secret_word, str):
        raise TypeError(f'Secret word must be a string! received: {type(secret_word).__name__}')
    
    cleaned_category = category.strip()
    cleaned_secret_word = secret_word.strip()


    if not cleaned_category:
        raise ValueError(f'Invalid Category must be valid words. received: {category}.')

    if not cleaned_secret_word:
        raise ValueError(f'Invalid Secret word must be valid words. received: {secret_word}.')
    
    if len(cleaned_secret_word.split()) > 1:
        raise ValueError('Secret word must be 1 word!')

    if len(cleaned_category) > 30:
        raise ValueError('Category input must be shorter!')

    if len(cleaned_secret_word) > 30:
        raise ValueError('Secret word input must be shorter!')




    if cleaned_secret_word.casefold() in {'imposter', 'impostor'}:
        raise ValueError('Secret word cannot be "Imposter" as it is reserved for the role marker.')

    return (cleaned_category, cleaned_secret_word)