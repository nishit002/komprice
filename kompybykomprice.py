import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import openai
from tenacity import retry, stop_after_attempt, wait_fixed
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import logging
import matplotlib.pyplot as plt

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

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    """Scrape a webpage using ScraperAPI with retries and error handling."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(api_url, headers=headers, timeout=60)
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

        # Clean and format price
        price_cleaned = ''.join([char for char in price if char.isdigit() or char == '.'])
        price_cleaned = float(price_cleaned) if price_cleaned else None

        reviews = soup.find_all("span", {"data-hook": "review-body"}) or soup.find_all("div", {"class": "t-ZTKy"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        return {"title": title, "price": price_cleaned, "source": source, "reviews": reviews, "url": url}

    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return {"title": "Title not found", "price": None, "source": "Error", "reviews": [], "url": url, "error": str(e)}

def calculate_discount_percentage(product_name, df):
    """Calculate discount percentage based on highest and cheapest price."""
    product_data = df[df["Product"] == product_name]
    if not product_data.empty:
        highest_price = product_data["Price"].max()
        cheapest_price = product_data["Price"].min()
        discount_percentage = (highest_price - cheapest_price) / highest_price * 100
        return discount_percentage, highest_price, cheapest_price
    return None, None, None

# Streamlit App
st.title("🛒 Product Comparison with Discounts and Sentiment Analysis")

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
    urls_1 = product_data[product_data["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = product_data[product_data["Product Name"] == product_2]["Product URL"].tolist()

    st.write("🚀 Scraping Product Data...")
    with ThreadPoolExecutor() as executor:
        scraped_data_1 = list(executor.map(scrape_page_with_scraperapi, urls_1))
        scraped_data_2 = list(executor.map(scrape_page_with_scraperapi, urls_2))

    price_comparison = []
    for url, data in zip(urls_1 + urls_2, scraped_data_1 + scraped_data_2):
        if data["price"] is not None:
            price_comparison.append({
                "Product": data["title"],
                "Source": data["source"],
                "Price": data["price"],
                "Link": f'<a href="{url}" target="_blank">Buy Now</a>'
            })

    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) &
        (supplier_data["City"] == selected_city)
    ].drop_duplicates()
    for _, row in supplier_info.iterrows():
        address_encoded = urllib.parse.quote(row['Address'])
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={address_encoded}"
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": float(row["Price"]),
            "Link": f'<a href="{google_maps_url}" target="_blank">Get Direction</a>'
        })

    price_df = pd.DataFrame(price_comparison)

    # Calculate discount percentages
    discount_1, highest_1, cheapest_1 = calculate_discount_percentage(product_1, price_df)
    discount_2, highest_2, cheapest_2 = calculate_discount_percentage(product_2, price_df)

    # Plot Discount Percentage Graphs
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    products = [product_1, product_2]
    discounts = [discount_1, discount_2]
    ax1.bar(products, discounts, color=["blue", "orange"])
    ax1.set_title("Discount Percentage by Product")
    ax1.set_xlabel("Product")
    ax1.set_ylabel("Discount Percentage (%)")
    for index, value in enumerate(discounts):
        ax1.text(index, value, f"{value:.1f}%", ha="center", va="bottom")

    # Annotate highest and cheapest prices
    for index, (highest, cheapest) in enumerate(zip([highest_1, highest_2], [cheapest_1, cheapest_2])):
        ax1.text(index, discounts[index] / 2,
                 f"Highest: ₹{highest:.2f}\nCheapest: ₹{cheapest:.2f}",
                 ha="center", va="center", color="white", fontsize=10)

    # Display the graph in Streamlit
    st.markdown("### Discount Percentage Comparison")
    st.pyplot(fig1)

    # Display Price Comparison Table
    st.markdown("### Price Comparison Table")
    st.write(price_df.to_html(escape=False, index=False), unsafe_allow_html=True)
