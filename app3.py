import streamlit as st
import sys
import os
from openai import OpenAI
from fpdf import FPDF
import io
import base64
import datetime
import requests
from requests.exceptions import RequestException

# Import the search_and_extract function from google-latest.py
from data_collection.google_latest import search_and_extract

# Initialize OpenAI client
client = OpenAI()

def check_url_accessibility(url):
    """
    Check if a URL returns a 403 Forbidden error
    """
    try:
        response = requests.head(url, timeout=5)
        return response.status_code != 403
    except RequestException:
        # If there's any request error, we'll consider it inaccessible
        return False

def filter_accessible_content(content_list):
    """
    Filter out content items with URLs that return 403 Forbidden errors
    """
    accessible_content = []
    
    for item in content_list:
        if check_url_accessibility(item['url']):
            accessible_content.append(item)
    
    return accessible_content

def analyze_with_chatgpt(content_list, user_query):
    """
    Send content to ChatGPT and get analysis based on user query
    """
    # Prepare content for ChatGPT
    content_text = "\n\n".join([f"Source: {item['url']}\nDate: {item['publication_date']}\n{item['content']}" 
                               for item in content_list])
    
    # Create prompt for ChatGPT
    prompt = f"""
    Analyze the following content and provide a detailed report based on this query: {user_query}
    
    CONTENT:
    {content_text}
    
    Please structure your report with clear sections, bullet points where appropriate, 
    and highlight key insights. Format your response in markdown.
    """
    
    # Call ChatGPT API with a model that supports larger context window
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # Using gpt-4-turbo for larger context window
            messages=[
                {"role": "system", "content": "You are an expert analyst who creates detailed, well-structured reports."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error in ChatGPT analysis: {str(e)}"

def generate_pdf(report_content, query):
    """
    Generate a PDF from the report content
    """
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'Analysis Report', 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    pdf = PDF()
    pdf.add_page()
    
    # Add title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Report: {query}", 0, 1)
    pdf.ln(5)
    
    # Add date
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(10)
    
    # Add a Unicode font
    pdf.set_font('helvetica', '', 12)
    
    # Handle the content carefully
    lines = report_content.split('\n')
    for line in lines:
        try:
            if line.startswith('# '):
                pdf.set_font('helvetica', 'B', 14)
                pdf.cell(0, 10, line[2:], 0, 1)
                pdf.ln(5)
            elif line.startswith('## '):
                pdf.set_font('helvetica', 'B', 12)
                pdf.cell(0, 10, line[3:], 0, 1)
            elif line.startswith('- '):
                pdf.set_font('helvetica', '', 12)
                pdf.cell(10, 10, '-', 0, 0)  # Using hyphen instead of bullet
                pdf.cell(0, 10, line[2:], 0, 1)
            else:
                pdf.set_font('helvetica', '', 12)
                pdf.multi_cell(0, 10, line)
        except Exception as e:
            # If there's an error with a specific line, skip it
            print(f"Error processing line: {line}")
            print(f"Error: {e}")
            continue
    
    # Return PDF as base64 string
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_base64 = base64.b64encode(pdf_output.getvalue()).decode('utf-8')
    
    return pdf_base64


def main():
    st.title("News Search and Analysis Application")
    
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
                all_results = search_and_extract(user_query, want_recent)
                
                # Filter out URLs that return 403 Forbidden errors
                with st.spinner("Filtering out inaccessible URLs..."):
                    results = filter_accessible_content(all_results)
                    
                    if len(results) < len(all_results):
                        st.info(f"Filtered out {len(all_results) - len(results)} URLs that returned access errors.")
                
                # Store results in session state for later use
                st.session_state.search_results = results
                st.session_state.user_query = user_query
                
                # Display the results
                if results:
                    st.success(f"Found {len(results)} accessible results")
                    
                    # Create tabs for different views
                    tab1, tab2, tab3 = st.tabs(["URLs Only", "Detailed View", "Generate Report"])
                    
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
                    
                    with tab3:
                        st.subheader("Generate Analysis Report")
                        st.write("Generate a detailed analysis report based on the search results.")
                        analysis_query = st.text_area("Specify what you want to analyze about these results:", 
                                                     value=user_query, height=100)
                        
                        if st.button("Generate Analysis"):
                            with st.spinner("Analyzing content and generating report..."):
                                # Analyze with ChatGPT
                                report_content = analyze_with_chatgpt(results, analysis_query)
                                
                                # Display the report in Streamlit
                                st.subheader("Generated Report")
                                st.markdown(report_content)
                                
                                # Generate PDF
                                pdf_base64 = generate_pdf(report_content, analysis_query)
                                
                                # Create download link
                                href = f'<a href="data:application/pdf;base64,{pdf_base64}" download="analysis_report.pdf">Download PDF Report</a>'
                                st.markdown(href, unsafe_allow_html=True)
                else:
                    st.warning("No accessible results found for your query.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    elif search_button and not user_query:
        st.warning("Please enter a search query.")
    
    # Check if there are already results in the session state (for when users switch tabs)
    elif hasattr(st.session_state, 'search_results') and st.session_state.search_results:
        results = st.session_state.search_results
        user_query = st.session_state.user_query if hasattr(st.session_state, 'user_query') else ""
        
        st.success(f"Found {len(results)} accessible results")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["URLs Only", "Detailed View", "Generate Report"])
        
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
        
        with tab3:
            st.subheader("Generate Analysis Report")
            st.write("Generate a detailed analysis report based on the search results.")
            analysis_query = st.text_area("Specify what you want to analyze about these results:", 
                                         value=user_query, height=100)
            
            if st.button("Generate Analysis"):
                with st.spinner("Analyzing content and generating report..."):
                    # Analyze with ChatGPT
                    report_content = analyze_with_chatgpt(results, analysis_query)
                    
                    # Display the report in Streamlit
                    st.subheader("Generated Report")
                    st.markdown(report_content)
                    
                    # Generate PDF
                    pdf_base64 = generate_pdf(report_content, analysis_query)
                    
                    # Create download link
                    href = f'<a href="data:application/pdf;base64,{pdf_base64}" download="analysis_report.pdf">Download PDF Report</a>'
                    st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()