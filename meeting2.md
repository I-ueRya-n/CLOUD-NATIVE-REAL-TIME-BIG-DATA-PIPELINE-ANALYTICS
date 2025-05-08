# Meeting 2 Notes: Thursday the 8th May 2025
1PM - ERC basement.
Attendees:
Molly
Josh
Ryan
Enzo

### From here
- set up bluesky search for past things?
- comments from OA - Molly
- extracting named entities - Enzo
- start processing sentiment into an es index (key as aggregation of source index + id?) - Josh
- thinking about frontend setup - Molly
- reddit api scraper - Ryan


### Calculating sentiment
- put all {ids: , sentiment:} into elasticsearch 
- when want to query e.g. on topic a:
  fission function which:
  - queries es posts for topic a, gets ids
  - searches for their sentiment of ids in the sentiment index
  - adds if they arent into the table using sentiment function
      STORE AS NEEDED! NOT ALL AT THE START! YAY!
  - aggregates 


### Ideas for frontend
- word cloud for auspol named entities across posts
- comparison accross all 3 for topics and stuff for sentiment
- top 10 and bottom 10 topics / people maybe?
- comparison of negativity between what people talk about + the actual debate?
- which politicial talks the most about controversial stuff?
    does this affect how people talk about them?