import os
import requests
import json
import re
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")  # Custom Search Engine ID

def enhance_query_with_llm(user_query):
    """
    Use OpenAI API to enhance the user query into a more effective search prompt
    """
    # Updated to use OpenAI API v1.0.0+
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        Convert the following user query into an effective Google search query. 
        Make it more specific and targeted to get relevant results:
        
        User Query: {user_query}
        
        Enhanced Search Query:
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that converts user queries into effective search queries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        enhanced_query = response.choices[0].message.content.strip()
        print(f"Original query: {user_query}")
        print(f"Enhanced query: {enhanced_query}")
        return enhanced_query
    except Exception as e:
        print(f"Error in enhancing query: {e}")
        # For debugging, print the exact error
        import traceback
        traceback.print_exc()
        return user_query  # Fallback to original query if enhancement fails

def google_api_search(query, num_results=2):
    """
    Perform a Google search using the Custom Search JSON API via direct HTTP request
    """
    try:
        # API endpoint
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Parameters
        params = {
            'q': query,
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'num': num_results
        }
        
        # Make the request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        
        # Parse results
        result = response.json()
        
        # For debugging - print first part of response
        print("API Response Preview:")
        print(json.dumps(result, indent=2)[:500] + "..." if len(json.dumps(result)) > 500 else json.dumps(result, indent=2))
        
        # Extract URLs from search results
        search_results = []
        if "items" in result:
            for item in result["items"]:
                search_results.append(item["link"])
        
        return search_results
    except Exception as e:
        print(f"Error in Google API search: {e}")
        # For debugging, print the detailed error
        if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        return []

def clean_text(text):
    """
    Clean the extracted text by removing excessive whitespace and newlines
    """
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n+', '\n', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    
    # Remove empty lines
    lines = [line for line in lines if line]
    
    # Join lines with a space instead of newline
    return ' '.join(lines)

def extract_content(url):
    """
    Extract main content from a webpage with improved error handling
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Improved request handling with explicit timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and navigational elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            element.extract()
        
        # Get text
        text = soup.get_text()
        
        # Clean the text
        clean_content = clean_text(text)
        
        # Truncate if too long
        if len(clean_content) > 10000:
            clean_content = clean_content[:10000] + "... [content truncated]"
            
        return clean_content
        
    except requests.exceptions.Timeout:
        return f"Error: Request timed out for {url}"
    except requests.exceptions.ConnectionError:
        return f"Error: Connection error for {url}"
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP error {e} for {url}"
    except requests.exceptions.RequestException as e:
        return f"Error: Request exception {e} for {url}"
    except Exception as e:
        return f"Error extracting content: {str(e)} for {url}"

def search_and_extract(user_query):
    """
    Main function that enhances query, searches Google, and extracts content from top results
    """
    # Enhance the query using LLM
    enhanced_query = enhance_query_with_llm(user_query)
    
    # Perform Google search using Google API
    urls = google_api_search(enhanced_query)
    
    if not urls:
        return ["No results found for the query."]
    
    # Extract content from each URL
    results = []
    for i, url in enumerate(urls):
        print(f"Processing {i+1}/{len(urls)}: {url}")
        content = extract_content(url)
        results.append({
            "url": url,
            "content": content
        })
        # Add a small delay to avoid overloading servers
        if i < len(urls) - 1:
            time.sleep(1)
    
    return results

if __name__ == "__main__":
    # Check if required API keys are set
    if not GOOGLE_API_KEY:
        print("ERROR: Please set GOOGLE_API_KEY in your .env file")
        print("You can get this from the Google Cloud Console")
        exit(1)
    
    if not GOOGLE_CSE_ID:
        print("ERROR: Please set GOOGLE_CSE_ID in your .env file")
        print("You can get this from the Google Programmable Search Engine")
        exit(1)
    
    if not OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY not set. Query enhancement will be skipped.")
        
    # Example usage
    user_query = input("Enter your search query: ")
    results = search_and_extract(user_query)
    
    if isinstance(results, list) and isinstance(results[0], str):
        # Handle the case where results contains error messages
        for result in results:
            print(result)
    else:
        # Normal case - results contains dictionaries
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"URL: {result['url']}")
            print(f"Content preview: {result['content'][:200]}...")
            
        # Save results to a file
        with open('search_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to search_results.json")