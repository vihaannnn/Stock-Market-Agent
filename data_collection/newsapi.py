import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import time

# Load environment variables from .env file
load_dotenv()

def get_stock_news(company_name: str, days_back: int = 7, language: str = "en", page_size: int = 15) -> List[Dict]:
    """
    Fetch news articles about a specific stock/company using NewsAPI.org.
    
    Args:
        company_name: The company or stock name to search for (e.g., "Apple" or "Tesla")
        days_back: How many days back to fetch news (default: 7)
        language: Language of articles (default: "en" for English)
        page_size: Number of articles to return (default: 15)
    
    Returns:
        A list of news article dictionaries
    """
    # Get API key from environment variables
    api_key = os.getenv('NEWS_API_KEY')
    
    if not api_key:
        raise ValueError("No API key found. Make sure NEWS_API_KEY is set in your .env file.")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Format dates for the API
    from_date = start_date.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')
    
    # API endpoint for everything endpoint
    url = "https://newsapi.org/v2/everything"
    
    # Parameters for the API request
    params = {
        "q": company_name,
        "from": from_date,
        "to": to_date,
        "language": language,
        "sortBy": "relevancy",
        "pageSize": page_size,
        "page": 1,
        "apiKey": api_key
    }
    
    try:
        # Send GET request to the API
        response = requests.get(url, params=params)
        
        # Raise an exception for bad responses
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Check if the request was successful
        if data.get('status') == 'ok':
            return data.get('articles', [])
        else:
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return []
    
    except requests.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

def fetch_article_content(url: str) -> str:
    """
    Fetch the full content of an article using its URL.
    
    Args:
        url: The URL of the article
    
    Returns:
        The article text if available, or an empty string
    """
    try:
        # Some news sites block simple requests, so we use a User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
            element.extract()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Break into lines and remove leading/trailing whitespace
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Remove blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    except Exception as e:
        return f"[Error fetching article content: {e}]"

def main():
    # Get company name from user
    company_name = input("Enter company or stock name to search for (e.g., Apple): ").strip()
    days = input("How many days back to search? (default: 7): ").strip()
    days = int(days) if days.isdigit() else 7
    
    print(f"\nFetching top 15 news articles about '{company_name}' from the past {days} days...")
    
    # Get news articles
    articles = get_stock_news(company_name, days_back=days, page_size=15)
    
    if not articles:
        print(f"No news articles found for '{company_name}'")
        return
    
    print(f"\nFound {len(articles)} articles. Retrieving full text for each article...\n")
    
    # Process each article
    for idx, article in enumerate(articles, 1):
        title = article.get('title', 'No title')
        source = article.get('source', {}).get('name', 'Unknown source')
        date = article.get('publishedAt', 'Unknown date')
        url = article.get('url', '')
        
        print(f"\n{'=' * 80}")
        print(f"ARTICLE #{idx}: {title}")
        print(f"SOURCE: {source}")
        print(f"DATE: {date}")
        print(f"URL: {url}")
        print(f"{'-' * 80}")
        
        # Fetch and display full article text
        print("ARTICLE TEXT:")
        if url:
            print("Fetching full article text, please wait...")
            full_text = fetch_article_content(url)
            if full_text and not full_text.startswith('[Error'):
                print(f"\n{full_text[:5000]}")
                if len(full_text) > 5000:
                    print("\n... (text truncated) ...")
            else:
                print(f"\n{full_text}")
                # If full text extraction failed, show the description and content from the API
                description = article.get('description', '')
                content = article.get('content', '')
                if description or content:
                    print("\nAPI-provided preview:")
                    if description:
                        print(f"\nDescription: {description}")
                    if content:
                        print(f"\nContent: {content}")
        else:
            print("No URL available to fetch the article.")
        
        # Add a small delay between requests to avoid hammering servers
        if idx < len(articles):
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")