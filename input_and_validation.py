import gradio as gr


def user_input(category,secret_word):
        try:
            
            if not category or not category.isalpha():
                raise ValueError(f'Invalid Category must be word must contain letters only. recieved: {category}.')

            if not secret_word or not secret_word.isalpha():
                raise ValueError(f'Invalid Secret word must be word must contain letters only. recieved: {secret_word}.')
                

        except ValueError as e:
            gr.Error(f'Error: {e}') 
    
        else: 
            return (category,secret_word)



user_input()