import openai
import streamlit as st

# Set your OpenAI API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Fetch product data using GPT with a focus on exclusive deals
def fetch_product_data_with_gpt(query):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a shopping assistant."},
                {"role": "user", "content": f"Generate a conversational response for the following query: '{query}'. Provide the best products available in Indian stores with their prices, product names, store names, exclusive offers, discount details, and links to shop online. Present the information in a table and include a breakdown of the offers."}
            ],
            max_tokens=300
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error fetching data: {str(e)}"

# Streamlit app to display the results
st.title("Kompy GPT - Best Deals & Comparison by Komprice")

# User input for product search
query = st.text_input("Search for products (e.g., best mobile phone under ₹20,000):")

if query:
    st.write(f"Looking for the best products for: '{query}'")
    
    # Fetch product data using GPT
    result = fetch_product_data_with_gpt(query)
    
    # Display GPT response
    if result:
        st.markdown(result, unsafe_allow_html=True)

# Suggested questions related to trending electronics and product comparisons
st.subheader("Suggested Shopping Queries")
suggestions = [
    "What are the top trending smartphones in India?",
    "Compare the latest laptops in India under ₹50,000.",
    "Which are the best budget TVs in India?",
]

# Create buttons for suggested questions
for question in suggestions:
    if st.button(question):
        query = question  # Set query for fetching results
        result = fetch_product_data_with_gpt(query)  # Fetch results
        if result:
            st.markdown(result, unsafe_allow_html=True)
