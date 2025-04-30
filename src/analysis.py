import spacy

# Load English tokenizer, tagger, parser and NER
nlp = spacy.load("en_core_web_sm")


def classifyLocation(text):
    """
    Label the text using spacy and extract the location
    related labels
    """
    doc = nlp(text)

    loc = filter(lambda e: e.label_ == 'GPE', doc.ents)
    return loc
