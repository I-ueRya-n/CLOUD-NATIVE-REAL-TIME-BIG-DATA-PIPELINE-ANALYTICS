import spacy

# Load English tokenizer, tagger, parser and NER
nlp = spacy.load("en_core_web_sm")

def location(text):
    doc = nlp(text)

    loc = filter(lambda e: e.label_ == 'GPE', doc.ents)
    return loc
