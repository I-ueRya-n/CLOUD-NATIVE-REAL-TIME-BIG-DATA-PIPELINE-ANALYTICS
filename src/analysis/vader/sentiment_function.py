from flask import request
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def main():
    """
    Function to analyze sentiment of text using VADER
    Sentiment Analysis. This function receives a JSON
    payload with a 'text' field, analyzes the sentiment
    of the text, and returns the sentiment scores in
    a JSON response.

    Example payload:
        {
            "text": "I love programming!"
        }

    Returns:
        JSON response with sentiment scores.
    """
    # Initialize VADER Sentiment Analyzer
    analyzer = SentimentIntensityAnalyzer()

    # Get the JSON payload from the request
    data = request.get_json()

    # Extract the text from the payload
    text = data.get('text', '')

    # Analyze the sentiment of the text
    sentiment_scores = analyzer.polarity_scores(text)

    # Return the sentiment scores as a JSON response
    return json.dumps(sentiment_scores)
