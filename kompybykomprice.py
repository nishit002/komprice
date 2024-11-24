import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import matplotlib.pyplot as plt
import openai
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
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# ScraperAPI Wrapper Function with Improved Price Extraction
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        response = requests.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract Title
        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        # Extract Reviews
        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        # Extract Price
        price = (
            soup.find("span", {"id": "priceblock_ourprice"})
            or soup.find("span", {"id": "priceblock_dealprice"})
            or soup.find("span", {"class": "a-price-whole"})
        )
        price = price.text.strip() if price else "Price not found"

        return {"title": title, "reviews": reviews, "price": price}

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error scraping {url} via ScraperAPI: {e}")

# Sentiment Analysis Using OpenAI
def analyze_reviews_with_gpt(reviews):
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

    # Scrape Product Data
    st.write("🚀 Scraping Product Data, Please Wait...")
    scraped_data_1 = [scrape_page_with_scraperapi(url) for url in urls_1]
    scraped_data_2 = [scrape_page_with_scraperapi(url) for url in urls_2]

    # Display Titles and Prices
    title_1 = scraped_data_1[0]["title"] if scraped_data_1 else "No title found"
    title_2 = scraped_data_2[0]["title"] if scraped_data_2 else "No title found"

    price_1 = scraped_data_1[0]["price"] if scraped_data_1 else "Price not found"
    price_2 = scraped_data_2[0]["price"] if scraped_data_2 else "Price not found"

    st.markdown(f"### Product 1: {title_1} - {price_1}")
    st.markdown(f"### Product 2: {title_2} - {price_2}")

    # Analyze Reviews
    reviews_1 = scraped_data_1[0]["reviews"] if scraped_data_1 else ["No reviews found"]
    reviews_2 = scraped_data_2[0]["reviews"] if scraped_data_2 else ["No reviews found"]

    sentiment_1 = analyze_reviews_with_gpt(reviews_1)
    sentiment_2 = analyze_reviews_with_gpt(reviews_2)

    # Display Sentiments
    st.markdown("### 😊 Customer Reviews: Positive Sentiments")
    st.markdown(f"**{title_1}**:\n{sentiment_1}")
    st.markdown(f"**{title_2}**:\n{sentiment_2}")

    # Price Comparison Table
    st.markdown(f"### 💰 Price Comparison Across Stores and Suppliers (City: {selected_city})")
    price_comparison = []

    # Online Store Prices
    for product, data, urls in zip([product_1, product_2], [scraped_data_1, scraped_data_2], [urls_1, urls_2]):
        for source, url in zip(["Amazon", "Flipkart"], urls):
            price_comparison.append({
                "Product": product,
                "Source": source,
                "Price": data[0]["price"] if data else "N/A",
                "Store Link": f"[Buy Now]({url})"
            })

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
            "Store Link": f"[Direction]({row['Address']})"  # Updated anchor text
        })

    # Display Price Comparison Table
    price_df = pd.DataFrame(price_comparison)
    st.write(price_df)

    # Plot Price Comparison Graph
    st.markdown("### 📊 Price Comparison Graph")
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    price_df = price_df.dropna(subset=["Price"])  # Remove rows with NaN prices

    if not price_df.empty:
        # Group data by Source and calculate average prices
        avg_prices = price_df.groupby("Source")["Price"].mean()

        # Plot the data
        fig, ax = plt.subplots()
        avg_prices.plot(kind="bar", ax=ax)
        ax.set_title("Price Comparison by Source")
        ax.set_ylabel("Average Price")
        ax.set_xlabel("Source")
        st.pyplot(fig)
    else:
        st.write("No valid price data available for plotting.")
