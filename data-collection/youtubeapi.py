import os
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
import datetime
import csv
from dotenv import load_dotenv

def get_stock_video_transcripts(api_key, ticker_symbol, max_results=10, published_after=None):
    """
    Fetches transcripts from latest YouTube videos discussing a specific stock ticker.
    
    Args:
        api_key (str): Your YouTube Data API key
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT')
        max_results (int): Maximum number of videos to fetch
        published_after (str): ISO 8601 formatted date (e.g., '2023-01-01T00:00:00Z')
                             to get videos published after this date
    
    Returns:
        list: A list of dictionaries containing video details and transcripts
    """
    # Set up the YouTube API client
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    
    # Set default published_after to 7 days ago if not provided
    if not published_after:
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        published_after = seven_days_ago.isoformat() + 'Z'
    
    # Search for videos related to the ticker symbol
    search_query = f"{ticker_symbol} stock analysis"
    search_response = youtube.search().list(
        q=search_query,
        part='id,snippet',
        maxResults=max_results,
        type='video',
        publishedAfter=published_after,
        relevanceLanguage='en',  # Limit to English videos
        order='date'  # Get most recent videos first
    ).execute()
    
    video_results = []
    
    # Process each video from the search results
    for search_result in search_response.get('items', []):
        video_id = search_result['id']['videoId']
        video_title = search_result['snippet']['title']
        channel_title = search_result['snippet']['channelTitle']
        published_at = search_result['snippet']['publishedAt']
        
        # Get video details to check duration and view count
        video_response = youtube.videos().list(
            part='contentDetails,statistics',
            id=video_id
        ).execute()
        
        if not video_response['items']:
            continue  # Skip if video details not available
        
        video_detail = video_response['items'][0]
        duration = video_detail['contentDetails']['duration']  # In ISO 8601 format
        view_count = video_detail['statistics'].get('viewCount', '0')
        
        # Try to get transcript
        transcript_text = ""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([entry['text'] for entry in transcript_list])
        except Exception as e:
            transcript_text = f"Transcript unavailable: {str(e)}"
        
        video_info = {
            'video_id': video_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'title': video_title,
            'channel': channel_title,
            'published_at': published_at,
            'view_count': view_count,
            'duration': duration,
            'transcript': transcript_text
        }
        
        video_results.append(video_info)
    
    return video_results

def save_results_to_csv(results, ticker_symbol):
    """
    Saves the fetched video information and transcripts to a CSV file.
    
    Args:
        results (list): List of dictionaries with video details and transcripts
        ticker_symbol (str): The stock ticker symbol used in the search
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{ticker_symbol}_youtube_transcripts_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['video_id', 'video_url', 'title', 'channel', 'published_at', 
                     'view_count', 'duration', 'transcript']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results saved to {filename}")

def main():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY') or input("Enter your YouTube API key: ")
    ticker_symbol = input("Enter the stock ticker symbol (e.g., AAPL): ").upper()
    max_results = int(input("Enter maximum number of videos to fetch (default 10): ") or 10)
    days_ago = int(input("Enter how many days back to search (default 7): ") or 7)
    
    published_after = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat() + 'Z'
    
    results = get_stock_video_transcripts(
        api_key=api_key,
        ticker_symbol=ticker_symbol,
        max_results=max_results,
        published_after=published_after
    )
    
    if results:
        print(f"Found {len(results)} videos about {ticker_symbol}")
        save_results_to_csv(results, ticker_symbol)
    else:
        print(f"No videos found for {ticker_symbol} in the last {days_ago} days")

if __name__ == "__main__":
    main()