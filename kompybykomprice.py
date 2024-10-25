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
            {"role": "user", "content": f"Generate a conversational response for the best mobile phones under ₹20,000 available in Indian stores with their prices, product names, store names, exclusive offers, discount details, and links to shop online. Present the information in a table and include a breakdown of the offers."}
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
query = st.text_input("Search for mobile phones (e.g., best mobile phone under ₹20,000):")

if query:
    st.write(f"Looking for the best mobile phones under ₹20,000? Here are the top options for you from popular Indian stores:")
    
    # Fetch product data using GPT
    gpt_reply = fetch_product_data_with_gpt(query)
    
    # Display GPT response as table
    st.markdown(gpt_reply, unsafe_allow_html=True)

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
        # Set the query text input to the clicked suggestion
        st.session_state.query = question  # Store query in session state
        query = question  # Set query for fetching results
        gpt_reply = fetch_product_data_with_gpt(query)
        st.markdown(gpt_reply, unsafe_allow_html=True)

# If a query was previously set, show results
if 'query' in st.session_state:
    query = st.session_state.query
    gpt_reply = fetch_product_data_with_gpt(query)
    st.markdown(gpt_reply, unsafe_allow_html=True)
