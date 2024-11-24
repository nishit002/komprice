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

# ScraperAPI Wrapper Function
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        response = requests.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        price = (
            soup.find("span", {"id": "priceblock_ourprice"})
            or soup.find("span", {"id": "priceblock_dealprice"})
            or soup.find("span", {"class": "a-price-whole"})
        )
        price = price.text.strip() if price else "Price not found"

        return {"title": title, "reviews": reviews, "price": price}

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error scraping {url} via ScraperAPI: {e}")

# Sentiment Analysis Function
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

# Simulated data (replace with real data file paths)
product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = load_data("city_List_test.csv")

# Select City and Products
selected_city = st.selectbox("Select Your City", city_list["City"].unique())
products = product_data["Product Name"].unique()
product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

if st.button("🔍 Compare Products"):
    urls_1 = product_data[product_data["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = product_data[product_data["Product Name"] == product_2]["Product URL"].tolist()

    # Scrape Product Data
    st.write("🚀 Scraping Product Data...")
    scraped_data_1 = [scrape_page_with_scraperapi(url) for url in urls_1]
    scraped_data_2 = [scrape_page_with_scraperapi(url) for url in urls_2]

    # Prepare Price Comparison Data
    price_comparison = []
    for product, data, urls in zip([product_1, product_2], [scraped_data_1, scraped_data_2], [urls_1, urls_2]):
        for source, url in zip(["Amazon", "Flipkart"], urls):
            price_comparison.append({
                "Product": product,
                "Source": source,
                "Price": data[0]["price"] if data else "N/A",
                "Link": f"[Buy Now]({url})"
            })

    supplier_info = supplier_data[
        (supplier_data["Product Name"].isin([product_1, product_2])) &
        (supplier_data["City"] == selected_city)
    ]
    for _, row in supplier_info.iterrows():
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": f"{float(row['Price']):,.2f}",
            "Link": f"[Direction]({row['Address']})"
        })

    # Display Data
    price_df = pd.DataFrame(price_comparison)
    for _, row in price_df.iterrows():
        st.markdown(f"{row['Source']}: {row['Link']}", unsafe_allow_html=True)

    # Plot Graph
    st.markdown("### 📊 Price Comparison Graph")
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    price_df = price_df.dropna(subset=["Price"])

    if not price_df.empty:
        avg_prices = price_df.groupby("Source")["Price"].mean()
        fig, ax = plt.subplots()
        avg_prices.plot(kind="bar", ax=ax)
        ax.set_title("Price Comparison by Source")
        ax.set_ylabel("Average Price")
        ax.set_xlabel("Source")
        st.pyplot(fig)
    else:
        st.write("No valid price data available for plotting.")
