import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import matplotlib.pyplot as plt
import openai
from tenacity import retry, stop_after_attempt, wait_fixed

# OpenAI API Key
openai.api_key = "YOUR_API_KEY"

# ScraperAPI Key
SCRAPER_API_KEY = "YOUR_SCRAPER_API_KEY"

# User-Agent List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
]

# Scraper Function
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def scrape_page_with_scraperapi(url):
    """Scrape a webpage using ScraperAPI."""
    try:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract Product Title
        title = soup.find("span", {"id": "productTitle"})
        title = title.text.strip() if title else "Title not found"

        # Extract Customer Reviews
        reviews = soup.find_all("span", {"data-hook": "review-body"})
        reviews = [review.text.strip() for review in reviews if review] or ["No reviews found"]

        # Extract Price and Clean It
        price = (
            soup.find("span", {"id": "priceblock_ourprice"})
            or soup.find("span", {"id": "priceblock_dealprice"})
            or soup.find("span", {"class": "a-price-whole"})
        )
        price = price.text.strip() if price else "Price not found"
        price_cleaned = ''.join([c for c in price if c.isdigit() or c == '.'])

        return {"title": title, "reviews": reviews, "price": price_cleaned}

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error scraping {url}: {e}")

# Sentiment Analysis Function
def analyze_reviews_with_gpt(reviews):
    """Analyze reviews using GPT."""
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

# Test Phase 1
product_urls = [
    "https://www.amazon.in/example-product-1",
    "https://www.amazon.in/example-product-2"
]

# Scrape and Analyze
scraped_results = [scrape_page_with_scraperapi(url) for url in product_urls]
for result in scraped_results:
    print(f"Title: {result['title']}")
    print(f"Price: {result['price']}")
    print(f"Reviews: {', '.join(result['reviews'][:3])}...")
    print(f"Sentiment Analysis: {analyze_reviews_with_gpt(result['reviews'])}")

print("\nPhase 1 completed. Ready to proceed to Phase 2.\n")
# Example Supplier Data (Replace with actual CSV file)
supplier_data = pd.DataFrame({
    "Product Name": ["Example Product 1", "Example Product 2"],
    "Supplier Name": ["Local Supplier 1", "Local Supplier 2"],
    "City": ["City A", "City B"],
    "Price": ["2000", "2200"],
    "Address": ["https://goo.gl/maps/example1", "https://goo.gl/maps/example2"]
})

# City Selection
selected_city = "City A"

# Combine Scraped Data and Supplier Data
price_comparison = []

# Online Store Prices
for result in scraped_results:
    price_comparison.append({
        "Product": result["title"],
        "Source": "Online Store",
        "Price": result["price"],
        "Link": "https://example-store-link"
    })

# Local Supplier Prices
local_suppliers = supplier_data[supplier_data["City"] == selected_city]
for _, row in local_suppliers.iterrows():
    price_comparison.append({
        "Product": row["Product Name"],
        "Source": row["Supplier Name"],
        "Price": row["Price"],
        "Link": f"[Direction]({row['Address']})"
    })

# Convert to DataFrame
price_df = pd.DataFrame(price_comparison)
print("Price Comparison Table:")
print(price_df)

# Clean Price Column
price_df["Price"] = pd.to_numeric(price_df["Price"], errors="coerce")
price_df = price_df.dropna(subset=["Price"])

# Plot Graph
if not price_df.empty:
    avg_prices = price_df.groupby("Source")["Price"].mean()
    fig, ax = plt.subplots()
    avg_prices.plot(kind="bar", ax=ax)
    ax.set_title("Price Comparison by Source")
    ax.set_ylabel("Average Price")
    ax.set_xlabel("Source")
    plt.show()
else:
    print("No valid price data available for plotting.")

print("\nPhase 2 completed.")
