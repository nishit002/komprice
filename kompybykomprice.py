import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import matplotlib.pyplot as plt
import openai
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed

# OpenAI API Key
openai.api_key = st.secrets["openai"]["openai_api_key"]

# ScraperAPI Key from Streamlit Secrets
SCRAPER_API_KEY = st.secrets["scraperapi"]["scraperapi_key"]

# User-Agent List for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0 Safari/537.36",
]

# Retry mechanism for scraping
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    """Scrape a webpage using ScraperAPI with retries and error handling."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        response = requests.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract Title
        title = soup.find("span", {"id": "productTitle"}) or soup.select_one("span.B_NuCI")
        title = title.text.strip() if title else "Title not found"

        # Extract Price
        price = soup.find("span", {"id": "priceblock_ourprice"}) or soup.find("span", {"id": "priceblock_dealprice"})
        price = price.text.strip() if price else "Price not found"

        # Extract Features
        features = [li.text.strip() for li in soup.find_all("li")] or ["No features found"]

        # Extract Reviews
        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        return {"title": title, "price": price, "features": features, "reviews": reviews}
    except Exception as e:
        return {"title": "Error", "price": "Error scraping", "features": ["Error scraping"], "reviews": [str(e)]}

# Sentiment Analysis Using OpenAI
def analyze_reviews_with_gpt(reviews):
    """Analyze reviews using OpenAI GPT."""
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
st.title("🛒 Product Comparison with Sentiment Analysis and Detailed Features")

# Load Data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = pd.read_csv("city_List_test.csv")

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

    # Scrape Product Data in Parallel
    st.write("🚀 Scraping Product Data with ScraperAPI...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        scraped_data_1 = list(executor.map(scrape_page_with_scraperapi, urls_1))
        scraped_data_2 = list(executor.map(scrape_page_with_scraperapi, urls_2))

    # Display Titles and Prices
    title_1 = scraped_data_1[0]["title"] if scraped_data_1 else "No title found"
    title_2 = scraped_data_2[0]["title"] if scraped_data_2 else "No title found"

    price_1 = scraped_data_1[0]["price"] if scraped_data_1 else "Price not found"
    price_2 = scraped_data_2[0]["price"] if scraped_data_2 else "Price not found"

    st.markdown(f"### Product 1: {title_1} - {price_1}")
    st.markdown(f"### Product 2: {title_2} - {price_2}")

    # Compare Features
    features_1 = scraped_data_1[0]["features"] if scraped_data_1 else []
    features_2 = scraped_data_2[0]["features"] if scraped_data_2 else []

    combined_features = list(set(features_1 + features_2))
    feature_comparison = pd.DataFrame({
        "Feature": combined_features,
        product_1: ["✔" if feature in features_1 else "✘" for feature in combined_features],
        product_2: ["✔" if feature in features_2 else "✘" for feature in combined_features],
    })
    st.markdown("### 🛠️ Feature Comparison")
    st.table(feature_comparison)

    # Display Missing Features
    missing_in_1 = set(features_2) - set(features_1)
    missing_in_2 = set(features_1) - set(features_2)

    if missing_in_1:
        st.markdown(f"### Features Missing in {product_1}")
        st.table(pd.DataFrame({"Missing Feature": list(missing_in_1)}))

    if missing_in_2:
        st.markdown(f"### Features Missing in {product_2}")
        st.table(pd.DataFrame({"Missing Feature": list(missing_in_2)}))

    # Analyze Reviews
    reviews_1 = scraped_data_1[0]["reviews"] if scraped_data_1 else ["No reviews found"]
    reviews_2 = scraped_data_2[0]["reviews"] if scraped_data_2 else ["No reviews found"]

    sentiment_1 = analyze_reviews_with_gpt(reviews_1)
    sentiment_2 = analyze_reviews_with_gpt(reviews_2)

    # Sentiment Analysis
    st.markdown("### 😊 Positive and Negative Sentiments")
    sentiment_table = pd.DataFrame({
        "Aspect": ["Positive Sentiments", "Negative Sentiments"],
        title_1: sentiment_1.split("\n\n"),
        title_2: sentiment_2.split("\n\n"),
    })
    st.table(sentiment_table)

    # Price Comparison Graph
    st.markdown("### 💰 Price Comparison")
    price_df = pd.DataFrame({
        "Product": [product_1, product_2],
        "Price": [price_1, price_2]
    })
    price_df["Price"] = pd.to_numeric(price_df["Price"].str.replace("₹", "").str.replace(",", ""), errors="coerce")
    if not price_df["Price"].isna().all():
        fig, ax = plt.subplots()
        price_df.plot(kind="bar", x="Product", y="Price", ax=ax, color=["blue", "green"])
        ax.set_ylabel("Price (₹)")
        st.pyplot(fig)
