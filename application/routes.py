from flask import Flask, render_template, request,redirect
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from application import app,db,imageup

food_data = pd.read_csv('meals_dataset_descriptive.csv')

def extract_nutri_fromdb():
    meals=db.meals.find()

    meal_nutrition_db = {
        "calories": 0,
        "proteins": 0,
        "fats": 0,
        "carbohydrates": 0,
        "fiber": 0,
        "sugar": 0,
        "sodium": 0
    }

    for meal in meals:
        for nutrient in meal_nutrition_db:
            meal_nutrition_db[nutrient] += meal['nutritional_info'].get(nutrient, 0)

    return meal_nutrition_db

def calculate_nutritional_difference(meal_nutrition_db,user_nutrition):
    difference = {}
    for nutrient, requirement in user_nutrition.items():
        intake = meal_nutrition_db.get(nutrient, 0)
        difference[nutrient] = requirement - intake
    return difference


def calculate_protein_intake(weight, activity_level):
    activity_protein_factors = {
        'sedentary': 0.8,
        'lightly active': 1.0,
        'moderately active': 1.2,
        'very active': 1.5,
        'extra active': 1.8
    }
    protein_factor = activity_protein_factors.get(activity_level.lower(), 0.8)
    protein_intake_grams = protein_factor * weight
    return protein_intake_grams

def calculate_bmr(weight, height, age, gender):
    if gender.lower() == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    elif gender.lower() == 'female':
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    else:
        return None

def calculate_tdee(bmr, activity_level):
    activity_factors = {
        'sedentary': 1.2,
        'lightly active': 1.375,
        'moderately active': 1.55,
        'very active': 1.725,
        'extra active': 1.9
    }
    factor = activity_factors.get(activity_level, 1.2)
    return bmr * factor

def calculate_bmi(weight, height):
    height_m = height / 100
    return weight / (height_m ** 2)

def suggest_caloric_adjustment(tdee, bmi):
    if bmi < 18.5:
        return tdee + 500, 'gain weight'
    elif 18.5 <= bmi < 24.9:
        return tdee, 'maintain weight'
    elif 25 <= bmi < 29.9:
        return tdee - 500, 'lose weight'
    else:
        return tdee - 1000, 'lose weight'

def calculate_fat_intake(calories):
    fat_calories = calories * 0.25
    fat_grams = fat_calories / 9
    return fat_calories, fat_grams

def calculate_fiber_intake(age):
    return age + 5

def calculate_sugar_intake(calories):
    return (calories * 0.1) / 4

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    weight = float(request.form['weight'])
    height = float(request.form['height'])
    age = int(request.form['age'])
    gender = request.form['gender']
    activity = request.form['activity']

    bmr = calculate_bmr(weight, height, age, gender)
    tdee = calculate_tdee(bmr, activity)
    bmi = calculate_bmi(weight, height)
    adjusted_calories, goal = suggest_caloric_adjustment(tdee, bmi)
    protein_intake_grams = calculate_protein_intake(weight, activity)
    fat_calories, fat_grams = calculate_fat_intake(adjusted_calories)
    fiber_intake = calculate_fiber_intake(age)
    sugar_intake = calculate_sugar_intake(adjusted_calories)


    user_nutrition = {
        'calories': adjusted_calories,
        'proteins': protein_intake_grams,
        'carbohydrates': adjusted_calories * 0.4 / 4,  # Assuming 40% of calories from carbs
        'fat': fat_grams,
        'fiber': fiber_intake,
        'sugar': sugar_intake,
        'sodium': 2000
    }
    
    meal_nutrition_db=extract_nutri_fromdb()
    difference = calculate_nutritional_difference(meal_nutrition_db,user_nutrition)

    count = db.meals.count_documents({})
    for nutrient in difference:
        difference[nutrient]=difference[nutrient]/(4-count)

    next_meal_calories = difference['calories']
    next_meal_protein =  difference['proteins']
    next_meal_carbohydrates = difference['carbohydrates']
    next_meal_fat_grams = difference['fat']
    next_meal_fiber = difference['fiber']
    next_meal_sugar = difference['sugar']
    next_meal_sodium = difference['sodium']

    def filter_by_confidence(food_data, threshold=0.8):
        return food_data[food_data['Similarity'] >= threshold]

    scaler = StandardScaler()
    nutritional_columns = ['calories', 'proteins', 'carbohydrates', 'fat', 'fiber', 'sugar', 'sodium']
    food_nutrition = food_data[nutritional_columns]
    food_nutrition_scaled = scaler.fit_transform(food_nutrition)

    user_nutrition_df = pd.DataFrame([difference])
    user_nutrition_df = user_nutrition_df
    user_nutrition_scaled = scaler.transform(user_nutrition_df)

    cos_sim = cosine_similarity(food_nutrition_scaled, user_nutrition_scaled).flatten()

    food_data['Similarity'] = cos_sim

    filtered_adjusted_food_data = filter_by_confidence(food_data, threshold=0.8)

    top_recommendations = filtered_adjusted_food_data.sort_values(by='Similarity', ascending=False).head()
    top_recommendations_list = top_recommendations['Meal Name'].tolist()

    
    return render_template('results.html', bmr=bmr, bmi=bmi, tdee=tdee, adjusted_calories=adjusted_calories,
                           goal=goal, protein_intake_grams=protein_intake_grams, fat_calories=fat_calories,
                           fat_grams=fat_grams, fiber_intake=fiber_intake, sugar_intake=sugar_intake,
                           lunch_calories=next_meal_calories, lunch_protein=next_meal_protein, lunch_carbohydrates=next_meal_carbohydrates,
                           lunch_fat_grams=next_meal_fat_grams, lunch_fiber=next_meal_fiber, lunch_sugar=next_meal_sugar,
                           lunch_sodium=next_meal_sodium, top_recommendations=top_recommendations_list)



@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        meal_type = request.form['meal_type']
        uploaded_image = request.files['image']
        
        def upload_or_update_meal(meal_type, image_url, nutritional_info):
            existing_meal = db.meals.find_one({"meal_type": meal_type})
            meal_data = {
                "meal_type": meal_type,
                "image_url": image_url,
                "nutritional_info": nutritional_info
            }
            if existing_meal:
                db.meals.update_one({"_id": existing_meal["_id"]}, {"$set": meal_data})
            else:
                db.meals.insert_one(meal_data)

        if uploaded_image:
            image = imageup.Image.open(imageup.io.BytesIO(uploaded_image.read()))
            image.save(f'static/uploads/{uploaded_image.filename}')
            
            nutritional_info = imageup.process_image(uploaded_image)
            upload_or_update_meal(meal_type, f'static/uploads/{uploaded_image.filename}', nutritional_info)
            
            return render_template('resultimage.html', nutritional_info=nutritional_info, image_url=f'static/uploads/{uploaded_image.filename}')
        else:
            return 'No image uploaded', 400
    
    return render_template('upload.html')

