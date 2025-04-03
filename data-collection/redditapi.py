import os
import praw
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Load environment variables
load_dotenv()

# Initialize NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Set up Reddit API connection
def get_reddit_instance():
    load_dotenv()
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT', 'StockTrendsBot/1.0')
    
    if not client_id or not client_secret:
        raise ValueError("Missing Reddit API credentials in .env file")
    
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

# Subreddits to search
STOCK_SUBREDDITS = [
    'wallstreetbets', 'stocks', 'investing', 'stockmarket', 
    'finance', 'options', 'SecurityAnalysis', 'DayTrading'
]

# Stock-related keywords to filter posts
STOCK_KEYWORDS = [
    'stock', 'market', 'index', 'etf', 'fund', 'share', 'bull', 'bear', 
    'rally', 'crash', 'correction', 'recession', 'inflation', 'fed', 
    'interest rate', 'dividend', 'earnings', 'nasdaq', 'dow', 's&p', 
    'sp500', 'nyse', 'ipo', 'spac'
]

# Company tickers and names to track
MAJOR_TICKERS = {
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Google',
    'GOOG': 'Google',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'TSLA': 'Tesla',
    'NVDA': 'NVIDIA',
    'JPM': 'JPMorgan',
    'BAC': 'Bank of America',
    'SPY': 'S&P 500 ETF',
    'QQQ': 'Nasdaq ETF',
    'DIA': 'Dow Jones ETF',
    'VTI': 'Vanguard Total Market ETF'
}

def get_stock_trends(time_period=1):
    """
    Scrape Reddit for stock market trends
    
    Args:
        time_period (int): Number of days to look back
        
    Returns:
        dict: Dictionary containing trends and popular mentions
    """
    reddit = get_reddit_instance()
    cutoff_date = datetime.utcnow() - timedelta(days=time_period)
    
    all_posts = []
    all_comments = []
    ticker_mentions = Counter()
    
    # Process each subreddit
    for subreddit_name in STOCK_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            
            # Get top and hot posts from the subreddit
            for post in subreddit.hot(limit=50):
                post_date = datetime.fromtimestamp(post.created_utc)
                if post_date >= cutoff_date:
                    # Check if post contains stock-related keywords
                    if any(keyword.lower() in post.title.lower() or 
                           (post.selftext and keyword.lower() in post.selftext.lower()) 
                           for keyword in STOCK_KEYWORDS):
                        
                        # Extract post data
                        post_data = {
                            'subreddit': subreddit_name,
                            'title': post.title,
                            'text': post.selftext,
                            'score': post.score,
                            'date': post_date,
                            'url': post.url,
                            'id': post.id,
                            'type': 'post'
                        }
                        all_posts.append(post_data)
                        
                        # Count ticker mentions in title and text
                        count_ticker_mentions(post.title + " " + post.selftext, ticker_mentions)
                        
                        # Get comments for the post
                        post.comments.replace_more(limit=3)
                        for comment in post.comments.list():
                            if comment.created_utc >= cutoff_date.timestamp():
                                comment_data = {
                                    'subreddit': subreddit_name,
                                    'post_title': post.title,
                                    'text': comment.body,
                                    'score': comment.score,
                                    'date': datetime.fromtimestamp(comment.created_utc),
                                    'id': comment.id,
                                    'type': 'comment'
                                }
                                all_comments.append(comment_data)
                                
                                # Count ticker mentions in comments
                                count_ticker_mentions(comment.body, ticker_mentions)
        
        except Exception as e:
            print(f"Error processing subreddit {subreddit_name}: {e}")
            continue
    
    # Convert to dataframes
    posts_df = pd.DataFrame(all_posts) if all_posts else pd.DataFrame()
    comments_df = pd.DataFrame(all_comments) if all_comments else pd.DataFrame()
    
    # Extract trends
    trends = extract_trends(posts_df, comments_df)
    
    return {
        'trends': trends,
        'popular_tickers': ticker_mentions.most_common(20)
    }

def count_ticker_mentions(text, counter):
    """Count mentions of stock tickers in text"""
    if not text:
        return
    
    # Look for ticker patterns ($AAPL or just AAPL)
    ticker_pattern = r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b'
    
    matches = re.findall(ticker_pattern, text)
    for match in matches:
        ticker = match[0] if match[0] else match[1]
        if ticker in MAJOR_TICKERS.keys() or is_valid_ticker(ticker):
            counter[ticker] += 1
            
    # Also count company name mentions
    for ticker, company in MAJOR_TICKERS.items():
        if company.lower() in text.lower():
            counter[ticker] += 1

def is_valid_ticker(ticker):
    """Basic validation of ticker symbols"""
    # Ignore common abbreviations and words that might be captured
    invalid_tickers = {'A', 'I', 'AT', 'IT', 'ON', 'OR', 'FOR', 'ALL', 'ARE', 'CEO', 'CFO', 'ETF', 'IPO', 'USA', 'GDP'}
    return ticker not in invalid_tickers and len(ticker) >= 2 and len(ticker) <= 5

def extract_trends(posts_df, comments_df):
    """Extract trends from posts and comments"""
    trends = []
    
    if posts_df.empty:
        return trends
    
    # Sort by popularity
    top_posts = posts_df.sort_values('score', ascending=False).head(20)
    
    # Extract key themes
    for _, post in top_posts.iterrows():
        theme = {
            'title': post['title'],
            'text': summarize_text(post['text']) if post['text'] else "",
            'subreddit': post['subreddit'],
            'score': post['score'],
            'url': post['url']
        }
        trends.append(theme)
    
    return trends

def summarize_text(text, max_length=300):
    """Create a brief summary of text"""
    if not text or len(text) <= max_length:
        return text
    
    # Simple extractive summarization - take first few sentences
    sentences = text.split('.')
    summary = ""
    for sentence in sentences:
        if len(summary) + len(sentence) <= max_length:
            summary += sentence + "."
        else:
            break
    
    return summary

def main():
    """Main function to run the scraper"""
    print("Fetching stock market trends from Reddit...")
    
    # Get trends from the last 3 days
    results = get_stock_trends(time_period=3)
    
    # Display trends
    print("\n=== STOCK MARKET TRENDS FROM REDDIT ===\n")
    
    if not results['trends']:
        print("No significant stock market trends found.")
    else:
        for i, trend in enumerate(results['trends'], 1):
            print(f"{i}. {trend['title']} (r/{trend['subreddit']}, {trend['score']} upvotes)")
            if trend['text']:
                print(f"   {trend['text']}")
            print("")
    
    # Display popular tickers
    print("\n=== POPULAR STOCK MENTIONS ===\n")
    
    for ticker, count in results['popular_tickers']:
        company_name = MAJOR_TICKERS.get(ticker, "")
        name_display = f" ({company_name})" if company_name else ""
        print(f"{ticker}{name_display}: {count} mentions")

if __name__ == "__main__":
    main()