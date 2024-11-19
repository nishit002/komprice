import openai
import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# Set your OpenAI API key securely
openai.api_key = st.secrets["openai"]["openai_api_key"]

# Function to fetch product data from GPT
def fetch_product_data_with_gpt(query):
    try:
        st.write("Fetching product data from GPT...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a shopping assistant."},
                {"role": "user", "content": f"Generate a response for this query: '{query}'. Provide the best products available in Indian stores with their prices, product names, store names, exclusive offers, and discounts. Do not include URLs in the response."}
            ],
            max_tokens=500,
            timeout=20  # Timeout for GPT API
        )
        st.write("GPT response received.")
        return response['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        return "Error: The request to OpenAI API timed out."
    except Exception as e:
        return f"Error fetching data: {str(e)}"

# Function to search for product URLs
def get_product_url(product_name, store_name):
    try:
        st.write(f"Fetching URL for {product_name} from {store_name}...")
        if store_name.lower() == "amazon india":
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
        elif store_name.lower() == "flipkart":
            search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '+')}"
        elif store_name.lower() == "samsung store":
            search_url = f"https://www.samsung.com/in/search/?searchword={product_name.replace(' ', '%20')}"
        else:
            return "Store not supported"

        # Fetch search results page
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)  # Timeout for web scraping
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract the first product link
        if "amazon" in search_url:
            link = soup.find("a", class_="a-link-normal")
            if link:
                return "https://www.amazon.in" + link.get("href")
        elif "flipkart" in search_url:
            link = soup.find("a", class_="_1fQZEK")  # Flipkart product link class
            if link:
                return "https://www.flipkart.com" + link.get("href")
        elif "samsung" in search_url:
            link = soup.find("a", class_="search-result-link")  # Samsung link class
            if link:
                return "https://www.samsung.com" + link.get("href")

        return "URL not found"
    except requests.exceptions.Timeout:
        return "Error: The request to fetch URL timed out."
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

# Streamlit app to display results
st.title("Kompy GPT - Best Deals & Comparison by Komprice")

# User input for product search
query = st.text_input("Search for products (e.g., best mobile phone under ₹20,000):")

if query:
    st.write(f"Looking for the best products for: '{query}'")
    
    # Fetch product data using GPT
    result = fetch_product_data_with_gpt(query)
    
    # Display GPT response and add URLs
    if result:
        st.markdown("### Product Recommendations")
        products = []
        
        # Parse GPT response (assuming tabular format)
        for line in result.split("\n")[1:]:  # Skip the header row
            if line.strip():
                product_details = line.split("\t")  # Tab-separated values
                if len(product_details) == 6:  # Ensure valid row
                    product_name, store_name, price, offer, discount, _ = product_details
                    products.append((product_name, store_name, price, offer, discount))

        # Limit to top 5 products for speed
        products = products[:5]

        # Add progress bar for scraping
        progress_bar = st.progress(0)

        for i, product in enumerate(products):
            product_name, store_name, price, offer, discount = product
            url = get_product_url(product_name, store_name)
            # Display product details
            st.markdown(f"""
            **Product Name**: {product_name}  
            **Store Name**: {store_name}  
            **Price**: {price}  
            **Exclusive Offer**: {offer}  
            **Discount**: {discount}  
            [Shop Online]({url})  
            """, unsafe_allow_html=True)
            progress_bar.progress((i + 1) / len(products))
            time.sleep(0.2)  # Small delay to show progress bar

# Suggested queries
st.subheader("Suggested Shopping Queries")
suggestions = [
    "What are the top trending smartphones in India?",
    "Compare the latest laptops in India under ₹50,000.",
    "Which are the best budget TVs in India?",
]

# Create buttons for suggested queries
for question in suggestions:
    if st.button(question):
        query = question
        result = fetch_product_data_with_gpt(query)
        if result:
            st.markdown(result, unsafe_allow_html=True)
