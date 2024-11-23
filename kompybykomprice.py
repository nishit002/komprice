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
    try:
        params = {
            "api_key": SCRAPER_API_KEY,
            "url": url
        }
        async with session.get(SCRAPER_API_URL, params=params, timeout=20) as response:
            html = await response.text()
            return BeautifulSoup(html, "html.parser")
    except Exception as e:
        return None

async def scrape_concurrently(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

def parse_amazon_page(soup):
    try:
        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        price = soup.find("span", {"class": "a-price-whole"})
        price = price.text.replace(",", "").strip() if price else "Price not found"

        features = soup.find_all("span", {"class": "a-list-item"})
        features = [feature.text.strip() for feature in features] if features else []

        return {"title": title, "price": price, "features": features}
    except Exception:
        return {"title": "Error", "price": "Error", "features": []}

def parse_flipkart_page(soup):
    try:
        title = soup.find("span", {"class": "B_NuCI"})
        title = title.text.strip() if title else "Title not found"

        price = soup.find("div", {"class": "_30jeq3 _16Jk6d"})
        price = price.text.replace("₹", "").replace(",", "").strip() if price else "Price not found"

        features = soup.find_all("li", {"class": "_21Ahn-"})
        features = [feature.text.strip() for feature in features] if features else []

        return {"title": title, "price": price, "features": features}
    except Exception:
        return {"title": "Error", "price": "Error", "features": []}

def scrape_products(urls):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    soups = loop.run_until_complete(scrape_concurrently(urls))
    results = []
    for soup, url in zip(soups, urls):
        if not soup:
            results.append({"title": "Error", "price": "Error", "features": []})
            continue
        if "amazon" in url:
            results.append(parse_amazon_page(soup))
        elif "flipkart" in url:
            results.append(parse_flipkart_page(soup))
    return results

# Sentiment Analysis
def analyze_with_gpt(title, features):
    try:
        prompt = (
            f"The product title is: {title}.\n"
            f"Features: {features}.\n"
            "Provide a detailed sentiment analysis, including likes and dislikes."
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an expert analyst."}, {"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return response['choices'][0]['message']['content']
    except Exception:
        return "Error generating sentiment analysis."

# Streamlit App
st.title("Detailed Product Comparison App")

# Step 1: Select Category and Products
categories = product_data["Category"].unique().tolist()
selected_category = st.selectbox("Select a Category", categories)
filtered_products = product_data[product_data["Category"] == selected_category]
products = filtered_products["Product Name"].unique().tolist()

product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

# Step 2: Scrape and Compare
if st.button("Show Comparison"):
    urls_1 = filtered_products[filtered_products["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = filtered_products[filtered_products["Product Name"] == product_2]["Product URL"].tolist()

    st.write("Scraping Product Data...")
    data_1 = scrape_products(urls_1)
    data_2 = scrape_products(urls_2)

    # Feature Comparison Table
    st.markdown("### Feature Comparison")
    comparison_data = {
        "Feature": ["Title", "Price"] + [f"Feature {i+1}" for i in range(10)],
        product_1: [data_1[0]["title"], data_1[0]["price"]] + data_1[0]["features"][:10],
        product_2: [data_2[0]["title"], data_2[0]["price"]] + data_2[0]["features"][:10]
    }
    st.table(pd.DataFrame(comparison_data))

    # Sentiment Analysis
    st.markdown("### Sentiment Analysis")
    st.write(f"**{product_1} Sentiment Analysis:**")
    st.text(analyze_with_gpt(data_1[0]["title"], data_1[0]["features"]))
    st.write(f"**{product_2} Sentiment Analysis:**")
    st.text(analyze_with_gpt(data_2[0]["title"], data_2[0]["features"]))

    # Price Table with Percentage Difference
    st.markdown("### Price Comparison Across Stores")
    price_comparison = []
    for product, data in zip([product_1, product_2], [data_1, data_2]):
        for source, url in zip(["Amazon", "Flipkart"], urls_1 + urls_2):
            price = data[0]["price"]
            price_comparison.append({"Product": product, "Source": source, "Price": price, "URL": url})

    price_df = pd.DataFrame(price_comparison)
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    min_price = price_df["Price"].min()
    price_df["Price Difference (%)"] = ((price_df["Price"] - min_price) / min_price) * 100
    st.table(price_df)

    # Local Supplier Information
    st.markdown("### Local Supplier Information")
    selected_city = st.selectbox("Select Your City", city_list["City"].unique().tolist())
    supplier_info = supplier_data[(supplier_data["City"] == selected_city) &
                                   (supplier_data["Product Name"].isin([product_1, product_2]))]
    supplier_info["Cheapest"] = supplier_info["Price"] == supplier_info["Price"].min()
    st.table(supplier_info)

    # Price Comparison Graph
    st.markdown("### Price Comparison Graph")
    if not price_df.empty:
        fig, ax = plt.subplots()
        price_df.groupby("Source")["Price"].mean().plot(kind="bar", ax=ax, title="Price Comparison")
        ax.set_ylabel("Price")
        ax.set_xlabel("Source")
        st.pyplot(fig)
