import requests

def get_place_id(details_list, api_key, num_results=1):
  """
  Takes a list of details (e.g., address, name, etc.) and an API key,
  and returns a list of place IDs, sorted by closest match.
  Triggers the: "Places API Text Search Essentials (IDs Only)" SKU
  which has unlimited usage. yay!
  """
  base_url = "https://places.googleapis.com/v1/places:searchText"
  details = ", ".join(details_list)

  headers = {
    'Content-Type': 'application/json',
    'X-Goog-Api-Key': api_key,
    'X-Goog-FieldMask': 'places.id,places.name',
  }
  json_data = {
    'textQuery' : details,
  }
    
  response = requests.post(base_url, headers=headers, json=json_data)

  if response.status_code == 200:
    ids = []
    for place in response.json()['places']:
      print("Possible place found:", place['id'])
      ids.append(place['id'])
    return ids
  else:
    print("Error:", response.status_code, response.text)
    return None  
  
def get_place_info(place_id, api_key, get_reviews=True):
  """
  Takes a place ID and an API key, and returns place information.

  if get_reviews is True, it will also return reviews and a rating:
  Triggers the: "Places API Place Details Enterprise + Atmosphere" SKU
  (which has a limit of 1000 free requests per month and is ridiculously 
  expensive after that.)

  if get_reviews is False:
  Triggers the: "Places API Place Details Pro" SKU
  (which has a limit of 5000 free requests per month)
  """
  base_url = "https://places.googleapis.com/v1/places/"

  fields = "id,displayName,types"
  if get_reviews:
    fields += ",rating,reviews"
  headers = {
    'Content-Type': 'application/json',
    'X-Goog-Api-Key': api_key,
    'X-Goog-FieldMask': fields,
  }
  response = requests.get(base_url + place_id, headers=headers)

  if response.status_code == 200:
    print("Place found:", response.json()['displayName'])
    if get_reviews:
      print("Rating:", response.json()['rating'])
      print("Reviews:", response.json()['reviews'])
    else:
      print("Food types:", response.json()['types'])
    return response.json()
  else:
    print("Error:", response.status_code, response.text)
    return None
