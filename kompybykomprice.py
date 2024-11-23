import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import openai
import matplotlib.pyplot as plt

# Set your OpenAI API key
openai.api_key = st.secrets["openai"]["openai_api_key"]

# Embedded product URL table
product_data = {
    "Product Name": [
        "Samsung M05", "iQOO Z9", "POCO M6", "iQOO Z9 Lite", "Samsung M15", "iQOO Z7 Pro",
        "Samsung M05 (Flipkart)", "iQOO Z9s (Flipkart)", "POCO M6 (Flipkart)", "iQOO Z9 Lite (Flipkart)", "Samsung M15 (Flipkart)"
    ],
    "Store Name": [
        "Amazon", "Amazon", "Amazon", "Amazon", "Amazon", "Amazon",
        "Flipkart", "Flipkart", "Flipkart", "Flipkart", "Flipkart"
    ],
    "Product URL": [
        "https://www.amazon.in/Samsung-Storage-Display-Charging-Security/dp/B0DFY3XCB6",
        "https://www.amazon.in/iQOO-Storage-Ultra-Thin-Dimesity-Processor/dp/B07WHS35V6",
        "https://www.amazon.in/POCO-Orion-Blue-4GB-64GB/dp/B0DC1GNY41",
        "https://www.amazon.in/iQOO-Storage-Dimensity-Camera-Charger/dp/B07WFPLL2H",
        "https://www.amazon.in/Samsung-Storage-MediaTek-Dimensity-Security/dp/B0DGX9VVFV",
        "https://www.amazon.in/iQOO-Storage-Ultra-Thin-Dimesity-Processor/dp/B07WFPM2WQ",
        "https://www.flipkart.com/samsung-m05-mint-green-64-gb/p/itm31b7d648fd40f",
        "https://www.flipkart.com/iqoo-z9s-5g-onyx-green-256-gb/p/itme8048e0375248",
        "https://www.flipkart.com/poco-m6-5g-orion-blue-128-gb/p/itm1227ec8698a77",
        "https://www.flipkart.com/iqoo-z9-lite-5g-mocha-brown-128-gb/p/itm359f39910fd09",
        "https://www.flipkart.com/samsung-galaxy-m15-5g-blue-topaz-128-gb/p/itmf5a4280beb534"
    ]
}

df = pd.DataFrame(product_data)

# Streamlit app
st.title("Detailed Product Comparison (Amazon & Flipkart)")

# Display table of product URLs
st.markdown("### Embedded Product URLs:")
st.dataframe(df)

# Dropdown to select products
product_list = df["Product Name"].tolist()
product_a = st.selectbox("Select Product A", product_list)
product_b = st.selectbox("Select Product B", product_list)

# Function to scrape product details and reviews
def scrape_product_data(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract product title
        if "amazon" in url:
            title = soup.find("span", {"id": "productTitle"})
            title = title.text.strip() if title else "No Title Found"

            # Extract features
            feature_bullets = soup.find_all("span", class_="a-list-item")
            features = [bullet.text.strip() for bullet in feature_bullets if bullet.text.strip()]

            # Extract reviews
            reviews = soup.find_all("span", class_="review-text-content")
            reviews_text = [review.text.strip() for review in reviews]

        elif "flipkart" in url:
            title = soup.find("span", {"class": "B_NuCI"})
            title = title.text.strip() if title else "No Title Found"

            # Extract features
            feature_bullets = soup.find_all("li", class_="_21Ahn-")
            features = [bullet.text.strip() for bullet in feature_bullets if bullet.text.strip()]

            # Extract reviews
            reviews = soup.find_all("div", class_="t-ZTKy")
            reviews_text = [review.text.strip() for review in reviews]

        else:
            title, features, reviews_text = "Unsupported Store", [], []

        return title, features, reviews_text
    except Exception as e:
        return "Error", [], []

# Function to analyze features, likes, and dislikes using GPT
def analyze_with_gpt(title, features, reviews):
    try:
        prompt = (
            f"The product title is: {title}.\n"
            f"Here are the features:\n{features}\n"
            f"Here are some customer reviews:\n{reviews}\n"
            "Based on this, summarize the following in detail:\n"
            "- Key product features\n"
            "- What customers like most about the product\n"
            "- What customers dislike about the product\n"
            "Provide a detailed analysis that can be used for creating comparison tables and graphs."
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert e-commerce assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error analyzing with GPT: {str(e)}"

# Compare the selected products
if product_a and product_b and product_a != product_b:
    url_a = df.loc[df["Product Name"] == product_a, "Product URL"].values[0]
    url_b = df.loc[df["Product Name"] == product_b, "Product URL"].values[0]

    # Scrape data for both products
    title_a, features_a, reviews_a = scrape_product_data(url_a)
    title_b, features_b, reviews_b = scrape_product_data(url_b)

    # Use GPT to analyze features, likes, and dislikes
    analysis_a = analyze_with_gpt(title_a, features_a[:5], reviews_a[:10])
    analysis_b = analyze_with_gpt(title_b, features_b[:5], reviews_b[:10])

    # Display detailed report
    st.subheader("Detailed Report")
    st.markdown(f"### {product_a}")
    st.text(analysis_a)
    st.markdown(f"### {product_b}")
    st.text(analysis_b)

    # Graph: Feature comparison
    feature_counts = {
        product_a: len(features_a),
        product_b: len(features_b),
    }
    fig, ax = plt.subplots()
    ax.bar(feature_counts.keys(), feature_counts.values())
    ax.set_title("Number of Features Compared")
    ax.set_ylabel("Count")
    st.pyplot(fig)
