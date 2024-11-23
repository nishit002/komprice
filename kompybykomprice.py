import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
import aiohttp
import asyncio

# ScraperAPI Key
SCRAPER_API_KEY = st.secrets["scraperapi"]["scraperapi_key"]
SCRAPER_API_URL = "http://api.scraperapi.com"

# Load Data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

product_data = load_data("Product_URL_Test.csv")

# Asynchronous Scraping
async def scrape_url(session, url):
    """Scrape a single URL asynchronously."""
    try:
        params = {
            "api_key": SCRAPER_API_KEY,
            "url": url
        }
        async with session.get(SCRAPER_API_URL, params=params, timeout=20) as response:
            html = await response.text()
            return BeautifulSoup(html, "html.parser")
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None

async def scrape_concurrently(urls):
    """Scrape multiple URLs concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Parsing Functions
def parse_amazon_page(soup):
    """Parse Amazon page for title and reviews."""
    try:
        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] if reviews else ["No reviews found"]

        return {"title": title, "reviews": reviews}
    except Exception as e:
        return {"title": "Error", "reviews": [f"Error parsing reviews: {e}"]}

def parse_flipkart_page(soup):
    """Parse Flipkart page for title and reviews."""
    try:
        title = soup.find("span", {"class": "B_NuCI"})
        title = title.text.strip() if title else "Title not found"

        reviews = soup.find_all("div", {"class": "t-ZTKy"})
        reviews = [review.text.strip() for review in reviews if review] if reviews else ["No reviews found"]

        return {"title": title, "reviews": reviews}
    except Exception as e:
        return {"title": "Error", "reviews": [f"Error parsing reviews: {e}"]}

# Scraping Products
def scrape_products(urls):
    """Scrape titles and reviews for a list of URLs."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    soups = loop.run_until_complete(scrape_concurrently(urls))
    results = []
    for soup, url in zip(soups, urls):
        if not soup:
            results.append({"title": "Error", "reviews": ["Failed to fetch page"]})
            continue
        if "amazon" in url:
            results.append(parse_amazon_page(soup))
        elif "flipkart" in url:
            results.append(parse_flipkart_page(soup))
    return results

# Streamlit App
st.title("🛒 Product Review Scraper")

# Select Product
categories = product_data["Category"].unique().tolist()
selected_category = st.selectbox("Select a Category", categories)
filtered_products = product_data[product_data["Category"] == selected_category]
products = filtered_products["Product Name"].unique().tolist()

product_1 = st.selectbox("Select a Product", products)

# Fetch Data
if st.button("🔍 Scrape Product Details"):
    urls = filtered_products[filtered_products["Product Name"] == product_1]["Product URL"].tolist()

    st.write("🚀 Scraping Product Data...")
    scraped_data = scrape_products(urls)

    # Display Results
    for data in scraped_data:
        st.markdown(f"### 📌 {data['title']}")
        st.markdown("#### Customer Reviews")
        for review in data["reviews"]:
            st.markdown(f"- {review}")
