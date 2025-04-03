import os
from dotenv import load_dotenv
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
import datetime

# Load environment variables from .env file
load_dotenv()

def get_stock_video_transcripts(ticker_symbol):
    """
    Fetches transcripts from latest YouTube videos discussing a specific stock ticker.
    
    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        list: A list of transcripts as strings
    """
    # Get API key from .env file
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in .env file")
        return []
    
    # Set up the YouTube API client
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    
    # Set search parameters
    max_results = 10
    fourteen_days_ago = datetime.datetime.now() - datetime.timedelta(days=14)
    published_after = fourteen_days_ago.isoformat() + 'Z'
    
    # Search for videos related to the ticker symbol
    search_query = f"{ticker_symbol} stock analysis"
    search_response = youtube.search().list(
        q=search_query,
        part='id',
        maxResults=max_results,
        type='video',
        publishedAfter=published_after,
        relevanceLanguage='en',
        order='date'
    ).execute()
    
    transcripts = []
    
    # Process each video from the search results
    for search_result in search_response.get('items', []):
        video_id = search_result['id']['videoId']
        
        # Try to get transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([entry['text'] for entry in transcript_list])
            transcripts.append(transcript_text)
        except:
            # Skip videos without available transcripts
            continue
    
    return transcripts

def main():
    ticker_symbol = input("Enter the stock ticker symbol (e.g., AAPL): ").upper()
    
    transcripts = get_stock_video_transcripts(ticker_symbol)
    
    if transcripts:
        print(f"Found {len(transcripts)} transcripts about {ticker_symbol}")
        for i, transcript in enumerate(transcripts, 1):
            print(f"\nTranscript {i}:")
            print(transcript[:200] + "..." if len(transcript) > 200 else transcript)
            print("--------------------------------------------------")
    else:
        print(f"No transcripts found for {ticker_symbol} in the last 14 days")

if __name__ == "__main__":
    main()