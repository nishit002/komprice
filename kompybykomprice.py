import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import openai
import matplotlib.pyplot as plt

# Set OpenAI API key securely
openai.api_key = st.secrets["openai"]["openai_api_key"]

# Raw URLs for the datasets
PRODUCT_URL_FILE = "https://raw.githubusercontent.com/nishit002/komprice/fef95da449eecca9afd2805b35c5d6bbd4a8df7e/Product_URL_Test.csv"
SUPPLIER_INFO_FILE = "https://raw.githubusercontent.com/nishit002/komprice/fef95da449eecca9afd2805b35c5d6bbd4a8df7e/Supplier_Info_prices.csv"
CITY_LIST_FILE = "https://raw.githubusercontent.com/nishit002/komprice/fef95da449eecca9afd2805b35c5d6bbd4a8df7e/city_List_test.csv"

# Load datasets dynamically from GitHub
@st.cache
def load_data(url):
    return pd.read_csv(url)

product_data = load_data(PRODUCT_URL_FILE)  # Product URLs
supplier_data = load_data(SUPPLIER_INFO_FILE)  # Supplier Info
city_list = load_data(CITY_LIST_FILE)  # City List

# Step 1: Select Category
st.title("Product Comparison App")
categories = product_data["Category"].unique().tolist()
selected_category = st.selectbox("Select Product Category", categories)

# Step 2: Filter Products by Category
filtered_products = product_data[product_data["Category"] == selected_category]
products = filtered_products["Product Name"].unique().tolist()

# Step 3: Select Products to Compare
product_1 = st.selectbox("Select Product 1", products)
product_2 = st.selectbox("Select Product 2", [p for p in products if p != product_1])

# Step 4: Select User's City
cities = city_list["City"].unique().tolist()
selected_city = st.selectbox("Select Your City", cities)

# Scraping with ScraperAPI
def scrape_product_data_with_scraperapi(url):
    try:
        api_key = st.secrets["scraperapi"]["scraperapi_key"]
        proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}"
        response = requests.get(proxy_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract product details
        if "amazon" in url:
            title = soup.find("span", {"id": "productTitle"})
            title = title.text.strip() if title else "Title not found"

            features = soup.find_all("span", class_="a-list-item")
            features = [f.text.strip() for f in features] if features else ["Features not found"]

            price = soup.find("span", {"class": "a-price-whole"})
            price = price.text.replace(",", "").strip() if price else "Price not found"

        elif "flipkart" in url:
            title = soup.find("span", {"class": "B_NuCI"})
            title = title.text.strip() if title else "Title not found"

            features = soup.find_all("li", class_="_21Ahn-")
            features = [f.text.strip() for f in features] if features else ["Features not found"]

            price = soup.find("div", {"class": "_30jeq3 _16Jk6d"})
            price = price.text.replace("₹", "").replace(",", "").strip() if price else "Price not found"

        else:
            title, features, price = "Unsupported Store", [], "N/A"

        return title, features, float(price) if price.isdigit() else "N/A"
    except requests.exceptions.RequestException as e:
        return "Error: Unable to fetch data", [], "N/A"
    except Exception as e:
        return "Error: Unexpected issue", [], "N/A"

# Step 5: Fetch Data and Compare
if st.button("Show Comparison"):
    # Get Product URLs
    urls_1 = filtered_products[filtered_products["Product Name"] == product_1]["Product URL"].tolist()
    urls_2 = filtered_products[filtered_products["Product Name"] == product_2]["Product URL"].tolist()

    # Scrape data for both products
    results_1 = [scrape_product_data_with_scraperapi(url) for url in urls_1]
    results_2 = [scrape_product_data_with_scraperapi(url) for url in urls_2]

    # Feature Comparison Table
    st.markdown("### Feature Comparison")
    feature_data = {
        "Category": ["Title", "Key Features", "Price"],
        product_1: [results_1[0][0], ", ".join(results_1[0][1][:10]), results_1[0][2]],
        product_2: [results_2[0][0], ", ".join(results_2[0][1][:10]), results_2[0][2]],
    }
    st.table(pd.DataFrame(feature_data))

    # Sentiment Analysis
    def analyze_with_gpt(title, features):
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

    st.markdown("### Sentiment Analysis")
    st.write(f"**{product_1} Sentiment Analysis:**")
    st.text(analyze_with_gpt(results_1[0][0], results_1[0][1]))
    st.write(f"**{product_2} Sentiment Analysis:**")
    st.text(analyze_with_gpt(results_2[0][0], results_2[0][1]))

    # Price Comparison Table
    st.markdown("### Price Comparison Across Stores")
    price_comparison_data = []
    for result, urls, product in [(results_1, urls_1, product_1), (results_2, urls_2, product_2)]:
        for store_result, url in zip(result, urls):
            price_comparison_data.append({
                "Product": product,
                "Store": "Amazon" if "amazon" in url else "Flipkart",
                "Price": store_result[2],
                "Buy Now": f"[Link]({url})"
            })
    price_comparison_df = pd.DataFrame(price_comparison_data)
    st.table(price_comparison_df)

    # Local Supplier Data
    st.markdown("### Local Supplier Information")
    suppliers = supplier_data[(supplier_data["City"] == selected_city) & (supplier_data["Product Name"].isin([product_1, product_2]))]
    if not suppliers.empty:
        suppliers["Cheapest"] = suppliers["Price"] == suppliers["Price"].min()
        st.table(suppliers)

        # Add supplier prices to the graph
        for _, row in suppliers.iterrows():
            price_comparison_data.append({
                "Product": row["Product Name"],
                "Store": row["Supplier Name"],
                "Price": row["Price"],
                "Buy Now": f"Supplier Address: {row['Address']}"
            })

    # Plot Graph: Price Comparison
    st.markdown("### Price Comparison Graph")
    if price_comparison_data:
        graph_df = pd.DataFrame(price_comparison_data)
        graph_df = graph_df.groupby(["Product", "Store"]).mean().reset_index()
        for product in graph_df["Product"].unique():
            product_df = graph_df[graph_df["Product"] == product]
            fig, ax = plt.subplots()
            ax.bar(product_df["Store"], product_df["Price"])
            ax.set_title(f"Price Comparison for {product}")
            ax.set_ylabel("Price")
            ax.set_xlabel("Store")
            st.pyplot(fig)
