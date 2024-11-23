import pandas as pd
import streamlit as st
import openai
from playwright.async_api import async_playwright
import asyncio
import random
import matplotlib.pyplot as plt

# API Configurations
openai.api_key = st.secrets["openai"]["openai_api_key"]

# Load Data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

product_data = load_data("Product_URL_Test.csv")
supplier_data = load_data("Supplier_Info_prices.csv")
city_list = pd.read_csv("city_List_test.csv")

# User-Agent List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# Function to scrape with Playwright
async def scrape_page(url, latitude=28.4595, longitude=77.0266):
    """Scrape a single page using Playwright with geolocation and user agent."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),  # Random User Agent
                geolocation={"latitude": latitude, "longitude": longitude},  # Geolocation
                permissions=["geolocation"],  # Allow geolocation
            )
            page = await context.new_page()

            st.write(f"Navigating to {url}...")
            await page.goto(url, timeout=120000)  # 120 seconds timeout

            # Wait for main content to load
            st.write("Waiting for the page to load...")
            await page.wait_for_load_state("networkidle")

            # Debugging: Save a screenshot of the loaded page
            await page.screenshot(path="debug_screenshot.png")
            st.write("Screenshot saved: debug_screenshot.png")

            # Extract Title
            try:
                title = await page.text_content('span[id="productTitle"]') or "Title not found"
                title = title.strip()
            except Exception as e:
                st.write(f"Error extracting title: {e}")
                title = "Error extracting title"

            # Extract Reviews
            try:
                reviews = await page.eval_on_selector_all(
                    'span[data-hook="review-body"]',
                    "elements => elements.map(el => el.textContent.trim())",
                )
                reviews = reviews if reviews else ["No reviews found"]
            except Exception as e:
                st.write(f"Error extracting reviews: {e}")
                reviews = ["Error extracting reviews"]

            await browser.close()

            return {"title": title, "reviews": reviews}

    except Exception as e:
        st.error(f"Failed to scrape {url}: {e}")
        return {"title": "Error", "reviews": [f"Failed to fetch page: {e}"]}

async def scrape_multiple_pages(urls):
    """Scrape multiple pages concurrently."""
    tasks = [scrape_page(url) for url in urls]
    return await asyncio.gather(*tasks)

# Format Prices
def format_price(price):
    try:
        return f"{float(price):,.2f}"
    except ValueError:
        return "N/A"

# Sentiment Analysis
def analyze_reviews_with_gpt(reviews):
    """Analyze reviews using OpenAI GPT."""
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
st.title("🛒 Product Comparison with Location-Based Scraping")

# Select City
cities = city_list["City"].unique().tolist()
selected_city = st.selectbox("Select a City", cities)

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

    # Scrape products concurrently
    scraped_data_1 = asyncio.run(scrape_multiple_pages(urls_1))
    scraped_data_2 = asyncio.run(scrape_multiple_pages(urls_2))

    # Extract Titles
    title_1 = scraped_data_1[0]["title"] if scraped_data_1 else "No title found"
    title_2 = scraped_data_2[0]["title"] if scraped_data_2 else "No title found"

    st.markdown(f"### Product 1: {title_1}")
    st.markdown(f"### Product 2: {title_2}")

    # Analyze Reviews
    reviews_1 = scraped_data_1[0]["reviews"] if scraped_data_1 else ["No reviews found"]
    reviews_2 = scraped_data_2[0]["reviews"] if scraped_data_2 else ["No reviews found"]

    sentiment_1 = analyze_reviews_with_gpt(reviews_1)
    sentiment_2 = analyze_reviews_with_gpt(reviews_2)

    st.markdown("### 😊 Customer Reviews and Sentiment Analysis")
    st.markdown(f"#### {title_1}")
    st.markdown(sentiment_1)
    st.markdown(f"#### {title_2}")
    st.markdown(sentiment_2)

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
    ]
    for _, row in supplier_info.iterrows():
        price_comparison.append({
            "Product": row["Product Name"],
            "Source": row["Supplier Name"],
            "Price": format_price(row["Price"]),
            "Store Link": f"[Address]({row['Address']})"
        })

    # Create DataFrame for Display
    price_df = pd.DataFrame(price_comparison)
    st.table(price_df)

    # Price Comparison Graph
    st.markdown("### 📊 Price Comparison Graph (Percentage Difference)")
    price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
    if not price_df["Price"].isna().all():
        min_price = price_df["Price"].min()
        price_df["Price Difference (%)"] = ((price_df["Price"] - min_price) / min_price) * 100
        fig, ax = plt.subplots()
        price_df.groupby("Source")["Price Difference (%)"].mean().plot(kind="bar", ax=ax, title="Price Difference by Source")
        ax.set_ylabel("Price Difference (%)")
        ax.set_xlabel("Source")
        st.pyplot(fig)
