import requests
from requests.structures import CaseInsensitiveDict

def get_geoapify_data(place_name):
  url = "https://api.geoapify.com/v1/geocode/search"

  parameters = {
            'apiKey': '5336ed1c3d1445ee83788be7c0d51165', 
            'categories': 'commercial.food_and_drink,catering',
            # 'name': 'Castros kiosk Parkville',
            "name": place_name,
            "features": "building.catering",
            # 'text': 'Green Refectory, 115 Sydney Road, Brunswick VIC 3056, Australia',
            # 'bias':'proximity:144.946457,-37.840935',
            # 'bias':'proximity:144.959945597018,-37.7678589383028', # green refectory address
            'country':'Australia',
            'state': 'vic',
            # "type": "amenity",
            # 'filter':'rect:142.80303318753977,-36.182500717308365,146.9039947303753,-39.65677874423189',
            'limit': 2,
            }


  headers = CaseInsensitiveDict()
  headers["Accept"] = "application/json"

  resp = requests.get(url, headers=headers, params=parameters)
  print(resp.status_code)
  json = resp.json()
  json_features = json.get("features")

  for place in json_features:
      place_properties = place.get("properties")
      print("Name:", place_properties.get("name"))
      print("Address:", place_properties.get("formatted"))
      print("State:", place_properties.get("state"))
      print("Place ID:", place_properties.get("place_id"))
      print("Category:", place_properties.get("category"))
      print("Confidence:", place_properties.get("rank").get("confidence"))

  return json_features

def get_place_details(place_id):
  print("GETTING DETAILS FOR THE PLACE:", place_id)
  url = "https://api.geoapify.com/v2/place-details"

  parameters = {
            'apiKey': '5336ed1c3d1445ee83788be7c0d51165', 
            "id": place_id,
            # "categories": "commercial.food_and_drink,catering",
            "categories": "accomodation",

            "features": "details,accommodation",
            }


  headers = CaseInsensitiveDict()
  headers["Accept"] = "application/json"

  resp = requests.get(url, headers=headers, params=parameters)
  print(resp.status_code)
  
  json = resp.json()
  print(json.keys())
  json_features = json.get("features")
  print("JSON:", json)
  for place in json_features:
      place_properties = place.get("properties")
      print(place_properties)
      print("Name:", place_properties.get("name"))
      print("Caterirng:", place_properties.get("catering"))

      print("Address:", place_properties.get("formatted"))
      print("State:", place_properties.get("state"))
      print("Place ID:", place_properties.get("place_id"))
      print("Category:", place_properties.get("category"))
      # print("Confidence:", place_properties.get("rank").get("confidence"))
  
# data = get_geoapify_data("Green Refectory, Brunswick")
data = get_geoapify_data("American Hotel, Amsterdam")

id = data[0].get("properties").get("place_id")
get_place_details(id)