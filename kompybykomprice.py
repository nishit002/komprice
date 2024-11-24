import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import matplotlib.pyplot as plt
import openai
from tenacity import retry, stop_after_attempt, wait_fixed
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
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Scraper Function with Enhanced Price Extraction
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    """Scrape a webpage using ScraperAPI with retries and error handling."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Detect source based on URL
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

        # Clean and format price
        price_cleaned = ''.join([char for char in price if char.isdigit() or char == '.'])
        price_cleaned = float(price_cleaned) if price_cleaned else None

        # Log details
        logging.info(f"Scraped URL: {url}, Source: {source}, Title: {title}, Price: {price_cleaned}")

        return {"title": title, "price": price_cleaned, "source": source}

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        raise e
    except Exception as e:
        logging.error(f"Scraper error: {e}")
        raise e

# Streamlit App
st.title("🛒 Product Comparison with Accurate Price Scraping")

# Load Data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = load_data("city_List_test.csv")

# Select City
cities = city_list["City"].unique().tolist()
selected_city = st.selectbox("Select Your City", cities)

# Select Products for Comparison
products = product_data["Product Name"].unique().tolist()
product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

if st.button("🔍 Compare Products"):
    urls_1 = product_data[product_data["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = product_data[product_data["Product Name"] == product_2]["Product URL"].tolist()

    # Concurrent Scraping of Product Data
    st.write("🚀 Scraping Product Data...")
    with ThreadPoolExecutor() as executor:
        scraped_data_1 = list(executor.map(scrape_page_with_scraperapi, urls_1))
        scraped_data_2 = list(executor.map(scrape_page_with_scraperapi, urls_2))

    # Prepare price comparison data
    price_comparison = []

    for data in [scraped_data_1, scraped_data_2]:
        for item in data:
            if item["price"] is not None:
                price_comparison.append({
                    "Product": item["title"],
                    "Source": item["source"],
                    "Price": item["price"],
                    "Link": f"[Buy Now](#)"
                })

    # Local Supplier Prices
    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) &
        (supplier_data["City"] == selected_city)
    ].drop_duplicates(subset=["Product Name", "Supplier Name"])
    for _, row in supplier_info.iterrows():
        address_encoded = urllib.parse.quote(row['Address'])
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={address_encoded}"
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": float(row["Price"]),
            "Link": f"[Get Direction]({google_maps_url})"
        })

    # Add Cheapest Source Tag
    price_df = pd.DataFrame(price_comparison)
    min_price = price_df["Price"].min()
    price_df["Cheapest"] = price_df["Price"].apply(lambda x: "Cheapest" if x == min_price else "")

    # Render Hyperlinks in the Table
    price_df["Link"] = price_df["Link"].apply(
        lambda x: f'<a href="{x.split("(")[1][:-1]}" target="_blank">{x.split("[")[1].split("]")[0]}</a>'
    )

    # Display Price Comparison Table
    st.markdown("### Price Comparison Table")
    st.write(price_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Plot Price Comparison Graph
    st.markdown("### 📊 Price Comparison Graph")
    if not price_df.empty:
        avg_prices = price_df.groupby("Source")["Price"].mean()
        fig, ax = plt.subplots()
        avg_prices.plot(kind="bar", ax=ax)
        ax.set_title("Price Comparison by Source")
        ax.set_ylabel("Average Price (₹)")
        ax.set_xlabel("Source")
        st.pyplot(fig)
    else:
        st.write("No valid price data available for plotting.")
