from flask import request
import json
import spacy

# Download the English NLP model
# python -m spacy download en_core_web_sm
# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

def extract_named_entities(text):
    doc = nlp(text)
    results = {}
    for ent in doc.ents:
        results.setdefault(ent.label_, []).append(ent.text)
    return results

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
    
    data = request.get_json()

    text = data.get('text', '')

    results = extract_named_entities(text)

    return json.dumps(results)