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


def analyze_reviews_with_gpt(reviews):
    """Analyze reviews using GPT."""
    if not reviews or reviews == ["No reviews found"]:
        return "No reviews available for sentiment analysis."
    try:
        prompt = (
            "Analyze the following customer reviews and provide a summary in bullet points for: "
            "1. Positive Sentiments\n2. Negative Sentiments\nReviews:\n" + "\n".join(reviews)
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
st.title("🛒 Product Comparison with Sentiment Analysis and Pricing")

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
    urls_1 = product_data[product_data["Product Name"] == product_1][["Product URL", "Product Name"]]
    urls_2 = product_data[product_data["Product Name"] == product_2][["Product URL", "Product Name"]]

    st.write("🚀 Scraping Product Data...")
    errors = []
    with ThreadPoolExecutor() as executor:
        scraped_data_1 = list(executor.map(scrape_page_with_scraperapi, urls_1["Product URL"].tolist()))
        scraped_data_2 = list(executor.map(scrape_page_with_scraperapi, urls_2["Product URL"].tolist()))

    price_comparison = []
    sentiment_summaries = {}
    for url, data in zip(urls_1["Product URL"].tolist() + urls_2["Product URL"].tolist(), scraped_data_1 + scraped_data_2):
        if data["price"] is not None:
            price_comparison.append({
                "Product": data["title"],
                "Source": data["source"],
                "Price": data["price"],
                "Link": f'<a href="{url}" target="_blank">Buy Now</a>'
            })
        sentiment_summaries[data["title"]] = analyze_reviews_with_gpt(data["reviews"])
        if data.get("error"):
            errors.append(f"{url}: {data['error']}")

    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) &
        (supplier_data["City"] == selected_city)
    ].drop_duplicates()
    for _, row in supplier_info.iterrows():
        # Generate Google Maps Directions Link
        address_encoded = urllib.parse.quote(row['Address'])
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={address_encoded}"
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": float(row["Price"]),
            "Link": f'<a href="{google_maps_url}" target="_blank">Get Direction</a>'
        })

    price_df = pd.DataFrame(price_comparison)
    min_price = price_df["Price"].min()
    price_df["Cheapest"] = price_df["Price"].apply(lambda x: "Cheapest" if x == min_price else "")

    # Display Price Comparison Table
    st.markdown("### Price Comparison Table")
    st.write(price_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Display Sentiment Analysis
    st.markdown("### Sentiment Analysis of Reviews")
    for product, sentiment in sentiment_summaries.items():
        st.markdown(f"**{product}:**\n{sentiment}")

    if errors:
        st.markdown("### 🚨 Error Log")
        for error in errors:
            st.error(error)
