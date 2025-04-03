import requests
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_stock_news(ticker: str, limit: int = 10) -> List[Dict]:
    """
    Fetch recent news articles for a given stock ticker.
    
    :param ticker: Stock ticker symbol (e.g., 'AAPL')
    :param limit: Maximum number of news articles to retrieve (default 10)
    :return: List of news articles
    """
    # Get API key from environment variables
    api_key = os.getenv('STOCK_NEWS_API_KEY')
    
    if not api_key:
        raise ValueError("No API key found. Make sure STOCK_NEWS_API_KEY is set in your .env file.")
    
    # API endpoint
    url = "https://stocknewsapi.com/api/v1"
    
    # Parameters for the API request
    params = {
        "tickers": ticker,
        "items": limit,
        "token": api_key,
        "fallback": "true"  # This parameter helps ensure text content is included
    }
    
    try:
        # Send GET request to the API
        response = requests.get(url, params=params)
        
        # Raise an exception for bad responses
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Check if the request was successful
        if data.get('status') == 'success':
            return data.get('data', [])
        else:
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return []
    
    except requests.RequestException as e:
        print(f"Error fetching stock news: {e}")
        return []

def display_article(article: Dict, idx: int = None):
    """
    Display a formatted news article with full text.
    
    :param article: News article dictionary
    :param idx: Article index (optional)
    """
    header = f"#{idx}. " if idx else ""
    print(f"{header}{article.get('title')}")
    print(f"Source: {article.get('source_name')}")
    print(f"Published: {article.get('date')}")
    
    # Print sentiment if available
    sentiment = article.get('sentiment')
    if sentiment:
        print(f"Sentiment: {sentiment}")
    
    print(f"URL: {article.get('news_url')}")
    print("\nSUMMARY:")
    print(article.get('description', 'No summary available'))
    
    # Print full text if available
    text = article.get('text')
    if text and text.strip():
        print("\nFULL TEXT:")
        print(text)
    else:
        print("\nFull text not available")
    
    print("-" * 80)

# Example usage
def main():
    # Get news for a specified ticker
    ticker = input("Enter stock ticker symbol (e.g., AAPL): ").strip().upper()
    news_articles = get_stock_news(ticker)
    
    if not news_articles:
        print(f"No news articles found for {ticker}")
        return
    
    # Print out the news articles
    print(f"\nFound {len(news_articles)} articles for {ticker}:\n")
    for idx, article in enumerate(news_articles, 1):
        display_article(article, idx)

if __name__ == "__main__":
    main()