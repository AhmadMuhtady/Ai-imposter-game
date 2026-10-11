from typing import Type
import gradio as gr


def user_input(category,secret_word):
        try:

            if not isinstance(category,str):
                raise TypeError(f'Category must be a string! recieved: {type(category).__name__}')
            
            
            if not isinstance(secret_word,str):
                raise TypeError(f'Secret word must be a string! recieved: {type(secret_word).__name__}')
            
            
            cleaned_category = category.strip()
            cleaned_sercret_word = secret_word.strip()
            

            if not cleaned_category:
                raise ValueError(f'Invalid Category must be valid words. recieved: {category}.')

            if not cleaned_sercret_word:
                raise ValueError(f'Invalid Secret word must be valid words. recieved: {secret_word}.')
            

            if len(cleaned_category) > 30:
                raise ValueError('Categerory input must be shorter!')

            if len(cleaned_sercret_word) > 30:
                raise ValueError('Secret word input must be shorter!')

        except (ValueError,TypeError) as e:
            raise gr.Error(f'Error: {e}') 
    
        else: 
            return (cleaned_category,cleaned_sercret_word)