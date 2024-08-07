from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
import logging
import re
import openai
import math

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)

# Shopify API credentials
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN', 'YOUR_SHOPIFY_ACCESS_TOKEN')
SHOPIFY_SHOP_NAME = os.environ.get('SHOPIFY_SHOP_NAME', 'YOUR_SHOP_NAME')
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'https://zincsforboats.com')

# OpenAI API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Function to parse the user query
def parse_query(query):
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    model_pattern = re.compile(r'\b(?:Hewescraft\s+\d+\s+\w+)\b', re.IGNORECASE)
    product_pattern = re.compile(r'\b(zinc plates?|boat stands?|anodes?|paints?)\b', re.IGNORECASE)

    year = year_pattern.search(query)
    model = model_pattern.search(query)
    product = product_pattern.search(query)

    return {
        'year': year.group(0) if year else None,
        'model': model.group(0) if model else None,
        'product': product.group(0) if product else None
    }

# Function to fetch product details from Shopify using GraphQL
def fetch_product_details(query):
    try:
        logging.info(f"Fetching product details from Shopify for query: {query}")
        url = f"https://{SHOPIFY_SHOP_NAME}.myshopify.com/api/2024-07/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": SHOPIFY_ACCESS_TOKEN
        }
        data = {
            "query": """
            query searchProducts($query: String!, $first: Int) {
                products(first: $first, query: $query) {
                    edges {
                        node {
                            id
                            title
                            handle
                        }
                    }
                }
            }
            """,
            "variables": {
                "query": query,
                "first": 10
            }
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an HTTPError on bad responses
        products = response.json()['data']['products']['edges']
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response JSON: {response.json()}")
        return [product['node'] for product in products]
    except requests.RequestException as e:
        logging.error(f"Error fetching data from Shopify: {e}")
        return []

# Function to generate a response based on product availability
def generate_response(query, page=1, per_page=10):
    parsed_query = parse_query(query)
    product_query = parsed_query['product']
    products = fetch_product_details(product_query)
    
    if products:
        total_products = len(products)
        total_pages = math.ceil(total_products / per_page)
        
        start = (page - 1) * per_page
        end = start + per_page
        paginated_products = products[start:end]
        
        response_parts = []
        for product in paginated_products:
            product_name = product['title']
            product_url = f"{WEBSITE_URL}/products/{product['handle']}"
            response_parts.append(f"[{product_name}]({product_url})")
        
        response_message = (f"We found the following matches for your query (Page {page} of {total_pages}):\n\n" + 
                            "\n".join(response_parts) +
                            f"\n\nUse 'next' or 'prev' to navigate pages.")
    else:
        response_message = (f"We currently do not have the exact product you're looking for in our system, but we may have them in stock. "
                            f"Please visit our [Shopify store]({WEBSITE_URL}) and use the on-site search option. "
                            f"Thank you for visiting today, and we appreciate the opportunity to earn your business.")
    
    return response_message, total_pages

# Function to interact with OpenAI API
def get_openai_response(prompt):
    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo",  # Update to a current model
            prompt=prompt,
            max_tokens=150
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"Error fetching data from OpenAI: {e}")
        return "An error occurred while trying to generate a response."

# Root route
@app.route('/')
def home():
    return "Welcome to the Boat Zincs API"

# Route to handle user queries
@app.route('/get_response', methods=['GET'])
def get_response():
    try:
        logging.info("Handling /get_response request")
        query = request.args.get('query')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        if not query:
            logging.info("Query not provided")
            return jsonify({"error": "Query is required"}), 400
        
        logging.info(f"Received query: {query}")
        response_message, total_pages = generate_response(query, page, per_page)
        openai_response = get_openai_response(query)
        final_response = f"{response_message}\n\nAdditionally, here's some advice: {openai_response}"
        logging.info("Returning generated response")
        return jsonify({"message": final_response, "total_pages": total_pages, "current_page": page})
    except Exception as e:
        logging.error(f"Error in /get_response endpoint: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

# Route to handle data request
@app.route('/data', methods=['GET'])
def get_data():
    try:
        logging.info("Fetching data for /data endpoint")
        data = {"product_1": "Johnson Evinrude Skeg Zinc 40 - 75 Hp 1999 - 2006",
                "product_2": "Coastal Copper 450 Multi-Season Ablative Antifouling Bottom Paint Black Gallon"}
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /data endpoint: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
