import openai
import streamlit as st

# Set your OpenAI API key
openai.api_key = "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"

# Fetch product data using GPT with a focus on exclusive deals
def fetch_product_data_with_gpt(query):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a shopping assistant."},
            {"role": "user", "content": f"Generate a conversational response for the following query: '{query}'. Provide the best products available in Indian stores with their prices, product names, store names, exclusive offers, discount details, and links to shop online. Present the information in a table and include a breakdown of the offers."}
        ],
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

# Streamlit app to display the results
st.title("Kompy GPT - Best Deals & Comparison by Komprice")

# Add a shopping-related GIF of an Indian person
kompy_gif_url = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2Z1Ym5kN2YxMmhjNXI2am1maTNoOXc3NjdreDdvN3FjdnVkcTZwdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3og0IPNcCRz8Tizbd6/giphy.gif"
st.image(kompy_gif_url, width=150)

# User input for product search
query = st.text_input("Search for products (e.g., best mobile phone under ₹20,000):")

# Initialize result variable
result = ""

if query:
    st.write(f"Looking for the best products for: '{query}'")
    
    # Fetch product data using GPT
    result = fetch_product_data_with_gpt(query)
    
    # Display GPT response as a table
    st.markdown(result, unsafe_allow_html=True)

# Suggested questions related to trending electronics and product comparisons
st.subheader("Suggested Shopping Queries")
suggestions = [
    "What are the top trending smartphones in India?",
    "Compare the latest laptops in India under ₹50,000.",
    "Which are the best budget TVs in India?",
    "Show me the best smartwatches under ₹10,000.",
    "Compare wireless earbuds with the best sound quality in India.",
    "What are the top air conditioners to buy this summer?",
    "Which DSLR cameras are trending in India?"
]

# Create buttons for suggested questions
for question in suggestions:
    if st.button(question):
        query = question  # Set query for fetching results
        result = fetch_product_data_with_gpt(query)  # Fetch results
        st.markdown(result, unsafe_allow_html=True)

# Display the result only once
if result:
    st.markdown(result, unsafe_allow_html=True)
