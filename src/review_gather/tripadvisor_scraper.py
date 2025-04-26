import requests
from bs4 import BeautifulSoup


def scrape_tripadvisor_reviews(url):
  """
  Scrapes reviews from a TripAdvisor page.
  DONT RUN THIS TOO MANY TIMES OR YOU WILL GET BLOCKED
  THIS IS PROBABLY A BAD IDEA  
  only sees the first page of reviews too
  and only the first bit of each review (not the "read more" button)
  yeah this is a bad idea
  """
  HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36"
  }

  response = requests.get(url, headers=HEADERS)

  print(f"Response status code: {response.status_code}")

  if response.status_code == 200:
      soup = BeautifulSoup(response.text, 'html.parser')
      
      # review cards yay
      reviews = soup.find_all('div', attrs={'data-automation': 'reviewCard'})
      review_list = []
      # ok the names of sections are really weird
      # and im not sure if they will change
      for review in reviews:
          title_tag = review.find('div', attrs={'data-test-target': 'review-title'})
          title = title_tag.get_text(strip=True) if title_tag else 'No Title'
          reviewer_tag = review.find('span', class_='biGQs _P fiohW fOtGX')
          reviewer_name = reviewer_tag.get_text(strip=True) if reviewer_tag else 'No Reviewer'
          
          date_tag = review.find('div', class_='biGQs _P pZUbB xUqsL ncFvv osNWb')
          review_date = date_tag.get_text(strip=True) if date_tag else 'No Date'
          
          body_tag = review.find('div', attrs={'data-test-target': 'review-body'})
          if body_tag:
              review_text_span = body_tag.find('span', class_='ThzWO')
              review_text = review_text_span.get_text(strip=True) if review_text_span else 'No content'
          else:
              review_text = 'No Review Text'
          
          rating_div = review.find('div', class_='MyMKp u')
          rating = 'No Rating'
          if rating_div:
              svg = rating_div.find('svg')
              if svg:
                  title_attr = svg.find('title')
                  if title_attr:
                      rating = title_attr.get_text(strip=True)
          print('Title:', title)
          print('Reviewer:', reviewer_name)
          print('Date:', review_date)
          print('Rating:', rating)
          print('Review:', review_text)
          print('-' * 80)

          review_list.append({
            'title': title,
            'reviewer_name': reviewer_name,
            'review_date': review_date,
            'rating': rating,
            'review_text': review_text
          })
      return review_list
  else:
      print(f"oh no youve probably been blocked: {response.status_code}")

page_url = 'https://www.tripadvisor.com.au/Restaurant_Review-g947958-d1925490-Reviews-The_Green_Refectory-Brunswick_Moreland_Greater_Melbourne_Victoria.html'
reviews = scrape_tripadvisor_reviews(page_url)
# --------------------------------------------------------------------------------
# Title: Delicious brunch
# Reviewer: Mrs-Diedre
# Date: No Date
# Rating: 4 of 5 bubbles
# Review: Great selection of food reasonably priced. Food delicious and tasty, with lots of hidden spots to eat. Service good just needed reminding to bring out all food ordered.Read more
# --------------------------------------------------------------------------------
# Title: Lovely breakfast post run!
# Reviewer: Georgina W
# Date: No Date
# Rating: 5 of 5 bubbles
# Review: Me and some friends had breakfast here after ParkRun - it was very cheap and quick friendly service! The fresh pressed juice was delicious - definitely will come back.Read more
# --------------------------------------------------------------------------------