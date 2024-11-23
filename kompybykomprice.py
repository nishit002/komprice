import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import matplotlib.pyplot as plt
import openai

# OpenAI API Key
openai.api_key = st.secrets["openai"]["openai_api_key"]

# ScraperAPI Key from Streamlit Secrets
SCRAPER_API_KEY = st.secrets["scraperapi"]["scraperapi_key"]

# User-Agent List for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# ScraperAPI Wrapper Function
def scrape_page_with_scraperapi(url):
    """Scrape a webpage using ScraperAPI."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}  # Random User Agent

        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract Title
        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        # Extract Reviews
        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        return {"title": title, "reviews": reviews}

    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping {url} via ScraperAPI: {e}")
        return {"title": "Error", "reviews": ["Failed to fetch page"]}

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
st.title("🛒 Product Comparison with Sentiment Analysis and City-Specific Prices")

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

    # Scrape Product Data
    st.write("🚀 Scraping Product Data with ScraperAPI...")
    scraped_data_1 = [scrape_page_with_scraperapi(url) for url in urls_1]
    scraped_data_2 = [scrape_page_with_scraperapi(url) for url in urls_2]

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

    # Split Sentiments into Positive and Negative
    positive_sentiments_1 = []
    negative_sentiments_1 = []
    positive_sentiments_2 = []
    negative_sentiments_2 = []

    # Process Sentiments for Product 1
    if "Positive Sentiments:" in sentiment_1:
        positive_sentiments_1 = sentiment_1.split("Positive Sentiments:")[1].split("Negative Sentiments:")[0].strip().split("\n")
    if "Negative Sentiments:" in sentiment_1:
        negative_sentiments_1 = sentiment_1.split("Negative Sentiments:")[1].strip().split("\n")

    # Process Sentiments for Product 2
    if "Positive Sentiments:" in sentiment_2:
        positive_sentiments_2 = sentiment_2.split("Positive Sentiments:")[1].split("Negative Sentiments:")[0].strip().split("\n")
    if "Negative Sentiments:" in sentiment_2:
        negative_sentiments_2 = sentiment_2.split("Negative Sentiments:")[1].strip().split("\n")

    # Create Sentiment Table
    sentiment_table = pd.DataFrame({
        "Aspect": ["Positive Sentiments"] * len(positive_sentiments_1) + ["Negative Sentiments"] * len(negative_sentiments_1),
        title_1: positive_sentiments_1 + negative_sentiments_1,
        title_2: positive_sentiments_2 + negative_sentiments_2
    })
    st.markdown("### 😊 Customer Reviews and Sentiment Analysis")
    st.table(sentiment_table)

    # Price Comparison Table
    st.markdown(f"### 💰 Price Comparison Across Stores and Suppliers (City: {selected_city})")
    price_comparison = []

    # Online Store Prices
    for product, data, urls in zip([product_1, product_2], [scraped_data_1, scraped_data_2], [urls_1, urls_2]):
        for source, url in zip(["Amazon", "Flipkart"], urls):
            price_comparison.append({"Product": product, "Source": source, "Price": "N/A", "Store Link": f"[Buy Now]({url})"})

    # Local Supplier Prices (Filtered by City)
    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) & 
        (supplier_data["City"] == selected_city)
    ].drop_duplicates(subset=["Product Name", "Supplier Name"])
    for _, row in supplier_info.iterrows():
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": f"{float(row['Price']):,.2f}",
            "Store Link": f"[Address]({row['Address']})"
        })

    # Convert to DataFrame for Display
    price_df = pd.DataFrame(price_comparison)
    st.table(price_df)

    # Plot Price Comparison Graph
    st.markdown("### 📊 Price Comparison Graph")
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    if not price_df["Price"].isna().all():
        min_price = price_df["Price"].min()
        price_df["Price Difference (%)"] = ((price_df["Price"] - min_price) / min_price) * 100

        fig, ax = plt.subplots()
        price_df.groupby("Source")["Price Difference (%)"].mean().plot(kind="bar", ax=ax, color="skyblue")
        ax.set_title("Price Difference by Source")
        ax.set_ylabel("Price Difference (%)")
        ax.set_xlabel("Source")
        st.pyplot(fig)
