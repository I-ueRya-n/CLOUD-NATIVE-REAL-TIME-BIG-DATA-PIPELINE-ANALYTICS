from flask import request
import json
import spacy

# Download the English NLP model
# python -m spacy download en_core_web_sm
# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

def main():
    """ 
    Function to analyze sentiment of text using VADER Sentiment Analysis.
    
    This function receives a JSON payload with a 'text' field, analyzes the sentiment of the text,
    and returns the sentiment scores in a JSON response.
    
    Example payload:
        {
            "text": "I love programming!"
        }
    
    Returns:
        JSON response with sentiment scores.
    """
    
    # Get the JSON payload from the request
    data = request.get_json()
    
    # Extract the text from the payload
    text = data.get('text', '')

    # Process the text
    doc = nlp(text)

    results = {}
    # Extract named entities
    for ent in doc.ents:
        if ent.label_ not in results:
            results[ent.label_] = []

        results[ent.label_].append(ent.text)

    # Print the named entities
    for result in results:
        print(result)
    
    # Return the sentiment scores as a JSON response
    return json.dumps(results)
    