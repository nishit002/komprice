import pandas as pd
import streamlit as st
import openai
from playwright.sync_api import sync_playwright
import random
import matplotlib.pyplot as plt

# API Configurations
openai.api_key = st.secrets["openai"]["openai_api_key"]

# User-Agent List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# Function to scrape with Playwright
def scrape_page(url):
    """Scrape a single page using Playwright with a visible browser and IP rotation."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Non-headless browser
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),  # Random User Agent
            )
            page = context.new_page()

            # Go to the URL
            st.write(f"Navigating to {url}...")
            page.goto(url, timeout=120000)

            # Wait for the page to load
            st.write("Waiting for the page to load...")
            page.wait_for_load_state("networkidle")

            # Extract title
            try:
                title = page.text_content('span[id="productTitle"]') or "Title not found"
                title = title.strip()
            except Exception as e:
                st.write(f"Error extracting title: {e}")
                title = "Error extracting title"

            # Extract reviews
            try:
                reviews = page.locator('span[data-hook="review-body"]').all_text_contents()
                reviews = reviews if reviews else ["No reviews found"]
            except Exception as e:
                st.write(f"Error extracting reviews: {e}")
                reviews = ["Error extracting reviews"]

            browser.close()

            return {"title": title, "reviews": reviews}

    except Exception as e:
        st.error(f"Failed to scrape {url}: {e}")
        return {"title": "Error", "reviews": [f"Failed to fetch page: {e}"]}

# Function to refresh IP (using a proxy service)
def refresh_ip():
    """Simulates refreshing the IP by reconfiguring the proxy (requires proxy setup)."""
    st.write("Refreshing IP...")
    # Use proxy service like ScraperAPI, BrightData, etc.
    # Example: Set up a proxy in the Playwright context or your network.

# Function to fetch data for multiple pages
def scrape_multiple_pages(urls):
    results = []
    for url in urls:
        refresh_ip()  # Refresh IP before each request
        result = scrape_page(url)
        results.append(result)
    return results

# Sentiment Analysis Using OpenAI
def analyze_reviews_with_gpt(reviews):
    try:
        prompt = (
            "Analyze the following customer reviews and provide a summary in bullet points "
            "for what customers like (positive sentiment) and dislike (negative sentiment):\n"
            f"Reviews: {reviews}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a sentiment analysis expert."},
                      {"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error generating sentiment analysis: {e}"

# Streamlit App
st.title("🛒 Product Comparison with IP Refreshing")

# Load Data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

product_data = load_data("Product_URL_Test.csv")

# Select Products for Comparison
products = product_data["Product Name"].unique().tolist()
product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

if st.button("🔍 Compare Products"):
    urls_1 = product_data[product_data["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = product_data[product_data["Product Name"] == product_2]["Product URL"].tolist()

    # Scrape Product Data
    st.write("🚀 Scraping Product Data...")
    scraped_data_1 = scrape_multiple_pages(urls_1)
    scraped_data_2 = scrape_multiple_pages(urls_2)

    # Display Titles
    title_1 = scraped_data_1[0]["title"] if scraped_data_1 else "No title found"
    title_2 = scraped_data_2[0]["title"] if scraped_data_2 else "No title found"

    st.markdown(f"### Product 1: {title_1}")
    st.markdown(f"### Product 2: {title_2}")

    # Analyze Reviews
    reviews_1 = scraped_data_1[0]["reviews"] if scraped_data_1 else ["No reviews found"]
    reviews_2 = scraped_data_2[0]["reviews"] if scraped_data_2 else ["No reviews found"]

    sentiment_1 = analyze_reviews_with_gpt(reviews_1)
    sentiment_2 = analyze_reviews_with_gpt(reviews_2)

    st.markdown("### 😊 Customer Reviews and Sentiment Analysis")
    st.markdown(f"#### {title_1}")
    st.markdown(sentiment_1)
    st.markdown(f"#### {title_2}")
    st.markdown(sentiment_2)
