import os
import requests
import json
import re
from bs4 import BeautifulSoup
import openai
import time
from dotenv import load_dotenv
from googlesearch import search

# Load environment variables from .env file
load_dotenv()

# Set API keys
openai.api_key = os.getenv("OPENAI_API_KEY")

def enhance_query_with_llm(user_query):
    """
    Use ChatGPT to enhance the user query into a more effective search prompt
    """
    prompt = f"""
    Convert the following user query into an effective Google search query. 
    Make it more specific and targeted to get relevant results:
    
    User Query: {user_query}
    
    Enhanced Search Query:
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Using the lightweight model
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
        return user_query  # Fallback to original query if enhancement fails

def google_search(query, num_results=2):
    """
    Perform a Google search using the googlesearch-python library
    """
    try:
        search_results = list(search(query, num_results=num_results))
        return search_results
    except Exception as e:
        print(f"Error in Google search: {e}")
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
    
    # Perform Google search
    urls = google_search(enhanced_query)
    
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
    # Example usage
    user_query = input("Enter your search query: ")
    results = search_and_extract(user_query)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"URL: {result['url']}")
        print(f"Content preview: {result['content'][:200]}...")
        
    # Save results to a file
    with open('search_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to search_results.json")