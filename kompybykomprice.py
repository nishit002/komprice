import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
import matplotlib.pyplot as plt
import asyncio
import aiohttp
import openai

# API Keys and Configurations
SCRAPER_API_KEY = st.secrets["scraperapi"]["scraperapi_key"]
SCRAPER_API_URL = "http://api.scraperapi.com"
openai.api_key = st.secrets["openai"]["openai_api_key"]

# Load data dynamically
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

# Load datasets
product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = load_data("city_List_test.csv")

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
    except Exception:
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

# Sentiment Analysis
def analyze_reviews_with_gpt(reviews):
    """Analyze reviews and return a sentiment summary."""
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
        return f"- Error generating sentiment analysis: {e}"

# Streamlit App
st.title("🛒 Product Comparison with Reviews and Sentiment Analysis")

# Select Product
categories = product_data["Category"].unique().tolist()
selected_category = st.selectbox("Select a Category", categories)
filtered_products = product_data[product_data["Category"] == selected_category]
products = filtered_products["Product Name"].unique().tolist()

product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

# Fetch Data
if st.button("🔍 Show Comparison"):
    urls_1 = filtered_products[filtered_products["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = filtered_products[filtered_products["Product Name"] == product_2]["Product URL"].tolist()

    st.write("🚀 Scraping Product Data...")
    scraped_data_1 = scrape_products(urls_1)
    scraped_data_2 = scrape_products(urls_2)

    # Display Titles
    title_1 = scraped_data_1[0]["title"] if scraped_data_1 else "No title found"
    title_2 = scraped_data_2[0]["title"] if scraped_data_2 else "No title found"
    st.markdown(f"### Product 1: {title_1}")
    st.markdown(f"### Product 2: {title_2}")

    # Sentiment Analysis
    reviews_1 = scraped_data_1[0]["reviews"] if scraped_data_1 else ["No reviews found"]
    reviews_2 = scraped_data_2[0]["reviews"] if scraped_data_2 else ["No reviews found"]

    sentiment_1 = analyze_reviews_with_gpt(reviews_1)
    sentiment_2 = analyze_reviews_with_gpt(reviews_2)

    st.markdown("### Sentiment Analysis")
    st.markdown(f"**{title_1}**\n{sentiment_1}")
    st.markdown(f"**{title_2}**\n{sentiment_2}")

    # Price Comparison Table
    st.markdown("### 💰 Price Comparison Across Stores and Suppliers")
    price_comparison = []
    for product, data, urls in zip([product_1, product_2], [scraped_data_1, scraped_data_2], [urls_1, urls_2]):
        for source, url in zip(["Amazon", "Flipkart"], urls):
            price = data[0]["reviews"] if data else "Price not found"
            price_comparison.append({"Product": product, "Source": source, "Price": price, "Store Link": f"[Buy Now]({url})"})

    supplier_info = supplier_data[(supplier_data["Product Name"].isin([product_1, product_2]))]
    for _, row in supplier_info.iterrows():
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": row["Price"],
            "Store Link": f"[Address]({row['Address']})"
        })

    price_df = pd.DataFrame(price_comparison)
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    min_price = price_df["Price"].min()
    price_df["Price Difference (%)"] = ((price_df["Price"] - min_price) / min_price) * 100
    st.table(price_df)

    # Price Comparison Graph
    st.markdown("### 📊 Price Comparison Graph")
    if not price_df.empty:
        fig, ax = plt.subplots()
        price_df.groupby("Source")["Price"].mean().plot(kind="bar", ax=ax, title="Price Comparison")
        ax.set_ylabel("Price")
        ax.set_xlabel("Source")
        st.pyplot(fig)
