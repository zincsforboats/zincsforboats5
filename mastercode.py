from flask import Flask, jsonify, request
import os
import requests
import logging
import re

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Shopify API credentials
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN', 'YOUR_SHOPIFY_ACCESS_TOKEN')
SHOPIFY_SHOP_NAME = os.environ.get('SHOPIFY_SHOP_NAME', 'YOUR_SHOP_NAME')
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'https://zincs-for-boats.myshopify.com')

# Function to parse the user query
def parse_query(query):
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    model_pattern = re.compile(r'\b(?:Hewescraft\s+\d+\s+\w+)\b', re.IGNORECASE)
    product_pattern = re.compile(r'\b(zinc plates?)\b', re.IGNORECASE)

    year = year_pattern.search(query)
    model = model_pattern.search(query)
    product = product_pattern.search(query)

    return {
        'year': year.group(0) if year else None,
        'model': model.group(0) if model else None,
        'product': product.group(0) if product else None
    }

# Function to fetch product details from Shopify
def fetch_product_details(query):
    try:
        logging.info(f"Fetching product details from Shopify for query: {query}")
        url = f"https://{SHOPIFY_SHOP_NAME}.myshopify.com/admin/api/2021-04/products.json"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
        }
        params = {'title': query}
        logging.info(f"Request URL: {url}")
        logging.info(f"Request Headers: {headers}")
        logging.info(f"Request Params: {params}")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        products = response.json().get('products', [])
        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response JSON: {response.json()}")
        return products
    except requests.RequestException as e:
        logging.error(f"Error fetching data from Shopify: {e}")
        return []

# Function to generate a response based on product availability
def generate_response(query):
    products = fetch_product_details(query)
    
    if products:
        response_parts = []
        for product in products:
            product_name = product['title']
            product_url = f"{WEBSITE_URL}/products/{product['handle']}"
            response_parts.append(f"[{product_name}]({product_url})")
        
        response_message = f"We found the following matches for your query:\n\n" + "\n".join(response_parts)
    else:
        response_message = (f"We currently do not have the exact product you're looking for in our system, but we may have them in stock. "
                            f"Please visit our [Shopify store]({WEBSITE_URL}) and use the on-site search option. "
                            f"Thank you for visiting today, and we appreciate the opportunity to earn your business.")
    
    return response_message

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
        if not query:
            logging.info("Query not provided")
            return jsonify({"error": "Query is required"}), 400
        
        response_message = generate_response(query)
        logging.info("Returning generated response")
        return jsonify({"message": response_message})
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
