import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import openai
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import logging

# OpenAI API Key
openai.api_key = st.secrets["openai"]["openai_api_key"]

# ScraperAPI Key
SCRAPER_API_KEY = st.secrets["scraperapi"]["scraperapi_key"]

# User-Agent List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def scrape_page_with_scraperapi(url):
    """Scrape a webpage with ScraperAPI and handle errors."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(api_url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        if "amazon" in url.lower():
            source = "Amazon"
            title = soup.find("span", {"id": "productTitle"})
            title = title.text.strip() if title else "Title not found"
            price = (
                soup.find("span", {"id": "priceblock_ourprice"})
                or soup.find("span", {"id": "priceblock_dealprice"})
                or soup.find("span", {"class": "a-price-whole"})
            )
            price = price.text.strip() if price else "Price not found"

        elif "flipkart" in url.lower():
            source = "Flipkart"
            title = soup.find("span", {"class": "B_NuCI"})
            title = title.text.strip() if title else "Title not found"
            price = soup.find("div", {"class": "_30jeq3"})
            price = price.text.strip() if price else "Price not found"

        else:
            source = "Other"
            title = "Title not found"
            price = "Price not found"

        # Clean price
        price_cleaned = ''.join([char for char in price if char.isdigit() or char == '.'])
        price_cleaned = float(price_cleaned) if price_cleaned else None

        return {"title": title, "price": price_cleaned, "source": source, "url": url}

    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return {"title": "Error", "price": None, "source": "Error", "url": url}


def analyze_reviews_with_gpt(reviews):
    """Simplified and faster sentiment analysis using GPT."""
    if not reviews:
        return "No reviews available."
    try:
        prompt = (
            "Summarize customer reviews into bullet points:\n"
            + "\n".join(reviews[:3])  # Analyze only first 3 reviews
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"


# Streamlit App
st.title("🛒 Fast Product Comparison with Sentiment Analysis")

@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)


product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = load_data("city_List_test.csv")

cities = city_list["City"].unique().tolist()
selected_city = st.selectbox("Select Your City", cities)

products = product_data["Product Name"].unique().tolist()
product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

if st.button("🔍 Compare Products"):
    # Use only a few URLs to speed up scraping
    urls_1 = product_data[product_data["Product Name"] == product_1]["Product URL"].head(2).tolist()
    urls_2 = product_data[product_data["Product Name"] == product_2]["Product URL"].head(2).tolist()

    st.write("🚀 Scraping Product Data...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        scraped_data_1 = list(executor.map(scrape_page_with_scraperapi, urls_1))
        scraped_data_2 = list(executor.map(scrape_page_with_scraperapi, urls_2))

    price_comparison = scraped_data_1 + scraped_data_2

    # Combine supplier data for the selected city
    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) &
        (supplier_data["City"] == selected_city)
    ].drop_duplicates()

    for _, row in supplier_info.iterrows():
        address_encoded = urllib.parse.quote(row['Address'])
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={address_encoded}"
        price_comparison.append({
            "title": row["Product Name"],
            "source": row["Supplier Name"],
            "price": float(row["Price"]),
            "url": google_maps_url,
        })

    price_df = pd.DataFrame(price_comparison)
    price_df["Cheapest"] = price_df["price"] == price_df["price"].min()

    # Display Price Comparison Table
    st.markdown("### Price Comparison Table")
    st.write(price_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Simulate simplified review summaries
    st.markdown("### Sentiment Analysis of Reviews")
    for data in scraped_data_1 + scraped_data_2:
        st.markdown(f"**{data['title']}**")
        st.markdown(analyze_reviews_with_gpt(["Review text 1", "Review text 2", "Review text 3"]))

    # Error Logging
    st.markdown("### 🚨 Error Log")
    errors = [data for data in price_comparison if data["source"] == "Error"]
    if errors:
        for error in errors:
            st.error(error)
