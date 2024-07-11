from flask import Flask, request, render_template, redirect, url_for,jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import os
import io
import re as re
from application import app


load_dotenv()  # Load environment variables

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to load Google Gemini Pro Vision API And get response
def get_gemini_response(input_text, image, prompt):
    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        response = model.generate_content([input_text, image[0], prompt])
        return response.text
    except Exception as e:
        print(f"Error during API call: {e}")
        return {"error": str(e)}


def input_image_setup(uploaded_file):
    if uploaded_file:
        uploaded_file.seek(0)  # Ensure the file pointer is at the beginning
        bytes_data = uploaded_file.read()
        image_parts = [
            {
                "mime_type": uploaded_file.mimetype,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Connect to MongoDB

# Function to upload meal and store nutritional information


def parse_nutritional_info(response_text):
    nutritional_info = {}
    try:
        # Using regular expressions to extract nutrient values
        nutritional_info['calories'] = int(re.search(r"calories:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['proteins'] = int(re.search(r"proteins:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['fats'] = int(re.search(r"fats:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['carbohydrates'] = int(re.search(r"carbohydrates:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['fiber'] = int(re.search(r"fiber:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['sugar'] = int(re.search(r"sugar:\s*(\d+)", response_text, re.IGNORECASE).group(1))
        nutritional_info['sodium'] = int(re.search(r"sodium:\s*(\d+)", response_text, re.IGNORECASE).group(1))
    except Exception as e:
        print(f"Error parsing response text: {e}")
        return None

    return nutritional_info

# Function to process the uploaded image and extract nutritional information
def process_image(image):
    input_prompt = """
    Meal Nutrient Analysis:

    Image: [Visual representation of the meal]
    Total Nutrients:

    **Carbohydrates: [amount in grams]**
    **Proteins: [amount in grams]**
    **Fats: [amount in grams]**
    **calories: [amount in kcal]**
    **fiber: [amount in g]**
    **Sugar: [amount in grams]**
    **Sodium: [amount in milligrams]**
    Notes:

    Ensure accuracy in identifying food items and their corresponding nutrient content.
    Cross-reference with reliable nutritional databases for accurate nutrient quantification.
    Provide any additional relevant information or context about the meal if available.
    """
    image_data = input_image_setup(image)
    nutritional_info_text = get_gemini_response(input_prompt, image_data, input_prompt)
    # Placeholder for actual nutritional information extraction
    nutritional_info = parse_nutritional_info(nutritional_info_text)
    
    return nutritional_info
