import streamlit as st
import sys
import os

# Add the data-collection directory to the Python path


# Import the search_and_extract function from google-latest.py
from data_collection.google_latest import search_and_extract

def main():
    st.title("News Search Application")
    
    # Get user inputs
    user_query = st.text_input("Enter your search query:")
    want_recent = st.checkbox("Do you want only recent news?")
    
    # Create a search button
    search_button = st.button("Search")
    
    # When search button is clicked and query is not empty
    if search_button and user_query:
        with st.spinner("Searching for news..."):
            try:
                # Call the search_and_extract function with user inputs
                results = search_and_extract(user_query, want_recent)
                
                # Display the results
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["URLs Only", "Detailed View"])
                    
                    with tab1:
                        # Display just the URLs
                        st.subheader("URLs")
                        for i, item in enumerate(results, 1):
                            st.write(f"{i}. {item['url']}")
                    
                    with tab2:
                        # Display detailed information
                        st.subheader("Detailed Results")
                        for i, item in enumerate(results, 1):
                            with st.expander(f"Result {i}: {item['url']}"):
                                st.write(f"**URL:** {item['url']}")
                                st.write(f"**Publication Date:** {item['publication_date']}")
                                st.text_area(f"Content {i}", item['content'], height=200)
                else:
                    st.warning("No results found for your query.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    elif search_button and not user_query:
        st.warning("Please enter a search query.")

if __name__ == "__main__":
    main()
