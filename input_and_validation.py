def user_input(category,secret_word):
    if not isinstance(category,str):
        raise TypeError(f'Category must be a string! received: {type(category).__name__}')
    
    
    if not isinstance(secret_word,str):
        raise TypeError(f'Secret word must be a string! received: {type(secret_word).__name__}')
    
    
    cleaned_Category = category.strip()
    cleaned_secret_word = secret_word.strip()
    

    if not cleaned_Category:
        raise ValueError(f'Invalid Category must be valid words. received: {category}.')

    if not cleaned_secret_word:
        raise ValueError(f'Invalid Secret word must be valid words. received: {secret_word}.')
    

    if len(cleaned_Category) > 30:
        raise ValueError('Categerory input must be shorter!')

    if len(cleaned_secret_word) > 30:
        raise ValueError('Secret word input must be shorter!')




    return (cleaned_Category,cleaned_secret_word)