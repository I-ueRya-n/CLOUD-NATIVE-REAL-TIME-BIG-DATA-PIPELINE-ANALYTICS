import datetime
 import requests
 import os
 

 def trigger_fission_function(function_name, params=None):
  """
  Triggers a Fission function.
  """
  url = f'http://router.fission/{function_name}'
  try:
  response = requests.get(url, params=params)
  response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
  return response.text
  except requests.exceptions.RequestException as e:
  print(f"Error triggering function {function_name}: {e}")
  return None
 

 def main():
  """
  Triggers the Reddit data harvester function.
  """
  # Calculate the date for two days ago (or adjust as needed)
  date_str = (datetime.datetime.utcnow() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
 

  # Trigger the Reddit data harvester function
  harvester_params = {
  'subreddits': os.environ.get("REDDIT_SUBREDDITS"),
  'limit': os.environ.get("REDDIT_LIMIT"),
  'keywords': os.environ.get("REDDIT_KEYWORDS"),
  }
  harvester_result = trigger_fission_function('reddit-data-harvester', harvester_params)
 

  if harvester_result:
  print(f"Harvester triggered successfully: {harvester_result}")
 

  #Trigger the Reddit data formatter function
  formatter_result = trigger_fission_function('reddit-data-formatter')
 

  if formatter_result:
  print(f"Formatter triggered successfully: {formatter_result}")
 

  #Trigger the Reddit to ES function
  es_result = trigger_fission_function('reddit-to-elasticsearch')
 

  if es_result:
  print(f"ES triggered successfully: {es_result}")
 

 if __name__ == "__main__":
  main()