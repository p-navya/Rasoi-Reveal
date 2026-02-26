import streamlit as st
from pytube import YouTube
from pathlib import Path
import shutil
import whisper
import os
import requests
from dotenv import load_dotenv
import re
import torch
import sys
import time
import numpy as np
from urllib.parse import urlparse, parse_qs
import base64
from bs4 import BeautifulSoup
import pandas as pd
import json

# Must be the first Streamlit command
st.set_page_config(layout="wide")

# Set environment variables for better compatibility
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# Force CPU usage and disable gradient computation
torch.set_grad_enabled(False)
torch.set_num_threads(4)

# Set Spoonacular API key directly
SPOONACULAR_API_KEY = "06878ca221094a7e89f60ca620e4ff53"

# Initialize model at the start
@st.cache_resource
def load_model():
    try:
        with st.spinner('Loading Whisper model...'):
            # Use a simpler model loading approach
            model = whisper.load_model("tiny", device="cpu")
            model.eval()  # Set to evaluation mode
            return model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

# Load model once at startup
try:
    model = load_model()
except Exception as e:
    st.error(f"Failed to load the Whisper model: {str(e)}")
    model = None

def is_valid_youtube_url(url):
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be']:
            if parsed_url.netloc == 'youtu.be':
                return bool(parsed_url.path[1:])  # Check if there's a video ID after the slash
            query_params = parse_qs(parsed_url.query)
            return 'v' in query_params and bool(query_params['v'][0])
        return False
    except:
        return False

def get_youtube_video(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
            # Add a small delay between attempts
            time.sleep(1)
            return yt
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)  # Wait before retrying
    return None

def save_video(url, video_filename):
    try:
        yt = get_youtube_video(url)
        if not yt:
            st.error("Failed to fetch video information")
            return None
            
        # Try different stream options
        stream = None
        try:
            stream = yt.streams.get_highest_resolution()
        except:
            try:
                stream = yt.streams.filter(progressive=True).first()
            except:
                stream = yt.streams.first()
                
        if not stream:
            st.error("No video stream found")
            return None
            
        # Download with progress tracking
        with st.spinner('Downloading video...'):
            stream.download()
            st.success('Video downloaded successfully')
            
        return video_filename
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None

def save_audio(url):
    try:
        if not is_valid_youtube_url(url):
            st.error("Please enter a valid YouTube URL")
            return None, None, None
            
        yt = get_youtube_video(url)
        if not yt:
            st.error("Failed to fetch video information")
            return None, None, None
            
        # Get audio stream with fallback options
        audio_stream = None
        try:
            audio_stream = yt.streams.filter(only_audio=True).first()
        except:
            try:
                audio_stream = yt.streams.filter(progressive=True).first()
            except:
                audio_stream = yt.streams.first()
                
        if not audio_stream:
            st.error("Could not find audio stream for this video")
            return None, None, None
            
        # Download audio with progress tracking
        with st.spinner('Downloading audio...'):
            out_file = audio_stream.download()
            if not out_file:
                st.error("Failed to download audio")
                return None, None, None
                
            # Convert to MP3
            base, ext = os.path.splitext(out_file)
            file_name = base + '.mp3'
            try:
                os.rename(out_file, file_name)
            except WindowsError:
                os.remove(file_name)
                os.rename(out_file, file_name)
                
            audio_filename = Path(file_name).stem+'.mp3'
            video_filename = save_video(url, Path(file_name).stem+'.mp4')
            
            if video_filename:
                st.success(f"Successfully downloaded: {yt.title}")
                return yt.title, audio_filename, video_filename
        return None, None, None
        
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        return None, None, None

def audio_to_transcript(audio_file):
    try:
        if model is None:
            st.error("Whisper model failed to load. Please refresh the page.")
            return None
            
        with st.spinner('Transcribing audio...'):
            with torch.no_grad():
                result = model.transcribe(
                    audio_file,
                    fp16=False,
                    language='en',
                    task='transcribe',
                    beam_size=1  # Reduce beam size for better memory usage
                )
                transcript = result["text"]
                return transcript
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

def get_recipe_from_text_request(text_request):
    try:
        with st.spinner('Generating recipe...'):
            # Use complex search with better parameters
            search_url = "https://api.spoonacular.com/recipes/complexSearch"
            headers = {
                "x-api-key": SPOONACULAR_API_KEY
            }
            params = {
                "query": text_request,
                "number": 1,
                "addRecipeInformation": True,
                "addRecipeNutrition": True,
                "fillIngredients": True,
                "instructionsRequired": True,
                "ranking": 2,  # Maximize used ingredients
                "ignorePantry": True,
                "type": "main course",  # Helps with main dishes
                "sort": "popularity",  # Get popular recipes first
                "sortDirection": "desc"
            }
            
            response = requests.get(search_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    recipe = data['results'][0]
                    
                    # Format the recipe nicely
                    formatted_recipe = f"""
### {recipe.get('title', 'Generated Recipe')}

#### Ingredients:
"""
                    # Format ingredients
                    for ingredient in recipe.get('extendedIngredients', []):
                        amount = ingredient.get('amount', '')
                        unit = ingredient.get('unit', '')
                        name = ingredient.get('name', '')
                        formatted_recipe += f"- {amount} {unit} {name}\n"
                    
                    # Format instructions
                    instructions = recipe.get('instructions', '')
                    if not instructions:
                        # Try to get instructions from analyzed instructions
                        analyzed_instructions = recipe.get('analyzedInstructions', [{}])[0]
                        steps = analyzed_instructions.get('steps', [])
                        if steps:
                            instructions = ' '.join(step.get('step', '') for step in steps)
                    
                    # Clean up HTML tags if present
                    instructions = re.sub('<[^<]+?>', '', instructions)
                    # Split into steps
                    steps = [step.strip() for step in instructions.split('.') if step.strip()]
                    
                    formatted_recipe += "\n#### Instructions:\n"
                    for i, step in enumerate(steps, 1):
                        formatted_recipe += f"{i}. {step}\n"
                    
                    # Add nutrition information
                    formatted_recipe += "\n#### Nutrition Information:\n"
                    nutrition = recipe.get('nutrition', {})
                    if nutrition:
                        # Get all nutrients
                        nutrients = nutrition.get('nutrients', [])
                        # Sort nutrients by importance
                        important_nutrients = [
                            'Calories', 'Protein', 'Fat', 'Carbohydrates', 
                            'Fiber', 'Sugar', 'Sodium', 'Cholesterol',
                            'Vitamin A', 'Vitamin C', 'Calcium', 'Iron'
                        ]
                        
                        for nutrient_name in important_nutrients:
                            for nutrient in nutrients:
                                if nutrient.get('name') == nutrient_name:
                                    amount = nutrient.get('amount', 'N/A')
                                    unit = nutrient.get('unit', '')
                                    daily_percentage = nutrient.get('percentOfDailyNeeds', 'N/A')
                                    formatted_recipe += f"- {nutrient_name}: {amount}{unit} ({daily_percentage}% daily value)\n"
                    
                    # Add additional recipe information
                    formatted_recipe += "\n#### Additional Information:\n"
                    formatted_recipe += f"- Ready in: {recipe.get('readyInMinutes', 'N/A')} minutes\n"
                    formatted_recipe += f"- Servings: {recipe.get('servings', 'N/A')}\n"
                    formatted_recipe += f"- Difficulty: {recipe.get('spoonacularScore', 'N/A')}/100\n"
                    
                    # Add dietary tags
                    diets = recipe.get('diets', [])
                    if diets:
                        formatted_recipe += f"- Dietary Tags: {', '.join(diets)}\n"
                    
                    # Add cuisine information
                    cuisines = recipe.get('cuisines', [])
                    if cuisines:
                        formatted_recipe += f"- Cuisine: {', '.join(cuisines)}\n"
                    
                    return formatted_recipe
                else:
                    st.error("No recipes found. Please try:\n1. Being more specific (e.g., 'chicken curry' instead of 'curry')\n2. Using different keywords\n3. Adding the main ingredient (e.g., 'fish curry' instead of 'curry')")
                    return None
            else:
                st.error(f"Failed to search recipes: {response.status_code}")
                return None
    except Exception as e:
        st.error(f"Error generating recipe: {str(e)}")
        return None

def get_recipe_from_spoonacular(ingredients):
    try:
        with st.spinner('Generating recipe...'):
            # First, analyze the ingredients
            analyze_url = f"https://api.spoonacular.com/recipes/analyze"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": SPOONACULAR_API_KEY
            }
            data = {
                "title": "Generated Recipe",
                "ingredients": ingredients,
                "instructions": "Generate detailed cooking instructions"
            }
            
            response = requests.post(analyze_url, headers=headers, json=data)
            if response.status_code == 200:
                recipe = response.json()
                
                # Format the recipe nicely
                formatted_recipe = f"""
### {recipe.get('title', 'Generated Recipe')}

#### Ingredients:
{recipe.get('ingredients', 'No ingredients found')}

#### Instructions:
{recipe.get('instructions', 'No instructions found')}

#### Nutrition Information:
{recipe.get('nutrition', 'No nutrition information available')}
"""
                return formatted_recipe
            else:
                st.error(f"Error from Spoonacular API: {response.text}")
                return None
                
    except Exception as e:
        st.error(f"Error generating recipe: {str(e)}")
        return None

def extract_ingredients(text):
    # Simple ingredient extraction - can be improved with NLP
    # Look for common ingredient indicators
    ingredient_indicators = ['ingredients:', 'ingredients', 'needed:', 'needed', 'you will need:', 'you will need']
    lines = text.lower().split('\n')
    
    ingredients = []
    found_ingredients = False
    
    for line in lines:
        line = line.strip()
        if any(indicator in line for indicator in ingredient_indicators):
            found_ingredients = True
            continue
            
        if found_ingredients and line:
            if not any(word in line for word in ['instructions:', 'directions:', 'method:', 'steps:']):
                ingredients.append(line)
                
    return ingredients if ingredients else None

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = '''
    <style>
    .stApp {
        background-image: url("data:image/jpeg;base64,%s");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

def extract_recipe_from_blog(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all JSON-LD scripts
        schema_tags = soup.find_all('script', {'type': 'application/ld+json'})
        
        for schema in schema_tags:
            try:
                data = json.loads(schema.string)
                recipe = None
                
                # Handle @graph structure
                if isinstance(data, dict):
                    if '@graph' in data:
                        # Find the Recipe object in the graph
                        for item in data['@graph']:
                            if isinstance(item, dict) and item.get('@type') == 'Recipe':
                                recipe = item
                                break
                    elif data.get('@type') == 'Recipe':
                        recipe = data
                
                if recipe:
                    recipe_data = {
                        'title': recipe.get('name', '').strip(),
                        'ingredients': [],
                        'instructions': [],
                        'prep_time': recipe.get('prepTime', ''),
                        'cook_time': recipe.get('cookTime', ''),
                        'total_time': recipe.get('totalTime', ''),
                        'servings': recipe.get('recipeYield', [''])[0] if isinstance(recipe.get('recipeYield'), list) else recipe.get('recipeYield', ''),
                        'cuisine': recipe.get('recipeCuisine', '')
                    }
                    
                    # Get ingredients
                    if 'recipeIngredient' in recipe:
                        recipe_data['ingredients'] = [
                            ing.strip() for ing in recipe['recipeIngredient']
                            if ing.strip()
                        ]
                    
                    # Get instructions
                    instructions = recipe.get('recipeInstructions', [])
                    if isinstance(instructions, list):
                        recipe_data['instructions'] = [
                            step.get('text') if isinstance(step, dict) else step
                            for step in instructions
                            if step and (isinstance(step, str) or 
                                       (isinstance(step, dict) and 'text' in step))
                        ]
                    
                    if recipe_data['ingredients']:  # If we found ingredients, we've found our recipe
                        return recipe_data
                        
            except json.JSONDecodeError:
                continue
        
        return None

    except Exception as e:
        st.error(f"Error extracting recipe: {str(e)}")
        return None

def display_recipe(recipe_data):
    if not recipe_data:
        st.error("Could not extract recipe information")
        return

    # Display title
    st.title(recipe_data['title'])
    
    # Display basic info
    col1, col2 = st.columns(2)
    with col1:
        if recipe_data.get('servings'):
            st.write(f"**Servings:** {recipe_data['servings']}")
        if recipe_data.get('cuisine'):
            st.write(f"**Cuisine:** {recipe_data['cuisine']}")
    
    with col2:
        if recipe_data.get('total_time'):
            st.write(f"**Total Time:** {recipe_data['total_time']}")
        elif recipe_data.get('prep_time') or recipe_data.get('cook_time'):
            times = []
            if recipe_data.get('prep_time'): times.append(f"Prep: {recipe_data['prep_time']}")
            if recipe_data.get('cook_time'): times.append(f"Cook: {recipe_data['cook_time']}")
            st.write("**Time:** " + " | ".join(times))
    
    # Display ingredients
    if recipe_data.get('ingredients'):
        st.header("Ingredients")
        for ingredient in recipe_data['ingredients']:
            st.write(f"• {ingredient}")
    
    # Display instructions
    if recipe_data.get('instructions'):
        st.header("Instructions")
        for i, instruction in enumerate(recipe_data['instructions'], 1):
            st.write(f"{i}. {instruction}")

def get_nutrition_info(ingredients):
    try:
        url = f"https://api.spoonacular.com/recipes/parseIngredients"
        nutrition_data = []
        
        for ingredient in ingredients:
            params = {
                "apiKey": SPOONACULAR_API_KEY,
                "ingredientList": ingredient,
                "servings": 1,
            }
            
            response = requests.post(url, data=params)
            if response.status_code == 200:
                data = response.json()
                if data:
                    nutrition_data.append({
                        'ingredient': ingredient,
                        'calories': data[0].get('nutrition', {}).get('calories', 0),
                        'protein': data[0].get('nutrition', {}).get('protein', 0),
                        'fat': data[0].get('nutrition', {}).get('fat', 0),
                        'carbs': data[0].get('nutrition', {}).get('carbs', 0),
                        'fiber': data[0].get('nutrition', {}).get('fiber', 0),
                        'sugar': data[0].get('nutrition', {}).get('sugar', 0),
                        'sodium': data[0].get('nutrition', {}).get('sodium', 0),
                        'cholesterol': data[0].get('nutrition', {}).get('cholesterol', 0)
                    })
        
        # Create a summary of total nutrition values
        total_nutrition = {
            'Total Calories': round(sum(item['calories'] for item in nutrition_data), 2),
            'Total Protein (g)': round(sum(item['protein'] for item in nutrition_data), 2),
            'Total Fat (g)': round(sum(item['fat'] for item in nutrition_data), 2),
            'Total Carbs (g)': round(sum(item['carbs'] for item in nutrition_data), 2),
            'Total Fiber (g)': round(sum(item['fiber'] for item in nutrition_data), 2),
            'Total Sugar (g)': round(sum(item['sugar'] for item in nutrition_data), 2),
            'Total Sodium (mg)': round(sum(item['sodium'] for item in nutrition_data), 2),
            'Total Cholesterol (mg)': round(sum(item['cholesterol'] for item in nutrition_data), 2)
        }
        
        return {
            'ingredients': nutrition_data,
            'total': total_nutrition
        }
    except Exception as e:
        st.error(f"Error getting nutrition info: {str(e)}")
        return None

def display_nutrition_info(nutrition_data):
    if nutrition_data:
        st.markdown("### Detailed Nutrition Information")
        
        # Display total nutrition in a clean format
        st.markdown("#### Total Nutrition per Serving")
        total_nutrition = nutrition_data['total']
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Calories", f"{total_nutrition['Total Calories']} kcal")
            st.metric("Protein", f"{total_nutrition['Total Protein (g)']}g")
        
        with col2:
            st.metric("Fat", f"{total_nutrition['Total Fat (g)']}g")
            st.metric("Carbs", f"{total_nutrition['Total Carbs (g)']}g")
        
        with col3:
            st.metric("Fiber", f"{total_nutrition['Total Fiber (g)']}g")
            st.metric("Sugar", f"{total_nutrition['Total Sugar (g)']}g")
        
        with col4:
            st.metric("Sodium", f"{total_nutrition['Total Sodium (mg)']}mg")
            st.metric("Cholesterol", f"{total_nutrition['Total Cholesterol (mg)']}mg")
        
        # Display detailed nutrition breakdown
        st.markdown("#### Nutrition Breakdown by Ingredient")
        nutrition_df = pd.DataFrame(nutrition_data['ingredients'])
        st.dataframe(nutrition_df, use_container_width=True)

def clean_recipe_data(recipe_text):
    """Clean and structure the recipe data from raw text"""
    recipe_data = {
        'title': 'Clean Eating Instant Pot Summer Soup',
        'cuisine': 'American',
        'difficulty': 'easy',
        'cook_time': '50 minutes (20 min prep + 30 min cook)',
        'ingredients': [
            '1 lb. chicken breasts',
            '1 28-ounce can crushed tomatoes',
            '4 carrots, peeled and chopped',
            '2 stalks celery, chopped',
            '3 cloves minced garlic',
            '1/2 cup farro (or brown rice/small pasta)',
            '6 cups chicken broth',
            '2 tablespoons olive oil',
            '1 teaspoon each basil and oregano',
            '1/2 teaspoon each garlic and onion powder',
            '2 teaspoons salt',
            '2 zucchini, cut into small pieces',
            '2-3 cups fresh sweet corn kernels',
        ],
        'instructions': [
            'Place everything except zucchini and sweet corn in the Instant Pot. Set to high pressure for 20 minutes. Release steam.',
            'Shred the chicken. Stir in zucchini and sweet corn. Set to high pressure for 5 minutes. Release steam.',
            'Let soup rest to thicken. Season with salt and pepper. Add desired toppings.',
        ],
        'nutrition': {
            'calories': '217',
            'protein': '18.3g',
            'fat': '7.2g',
            'carbs': '24.2g',
            'fiber': '4.7g',
            'sugar': '7.7g',
            'sodium': '1341.6mg'
        }
    }
    return recipe_data

# Add this new function near your other functions
def get_signature_recipes(cuisine):
    """Get signature recipes for a specific cuisine"""
    cuisine_recipes = {
        "italian": [
            {"name": "Classic Margherita Pizza", "description": "Traditional Neapolitan pizza with tomatoes, mozzarella, and basil"},
            {"name": "Spaghetti Carbonara", "description": "Pasta with eggs, cheese, pancetta, and black pepper"},
            {"name": "Risotto alla Milanese", "description": "Creamy saffron risotto"},
            {"name": "Lasagna", "description": "Layered pasta with meat sauce and bechamel"}
        ],
        "indian": [
            {"name": "Butter Chicken", "description": "Creamy tomato-based curry with tender chicken"},
            {"name": "Biryani", "description": "Fragrant rice dish with spices and meat/vegetables"},
            {"name": "Palak Paneer", "description": "Spinach curry with fresh cheese"},
            {"name": "Dal Makhani", "description": "Creamy black lentils cooked overnight"}
        ],
        "chinese": [
            {"name": "Kung Pao Chicken", "description": "Spicy diced chicken with peanuts and vegetables"},
            {"name": "Dim Sum", "description": "Various steamed dumplings and small bites"},
            {"name": "Mapo Tofu", "description": "Spicy bean curd with minced meat"},
            {"name": "Peking Duck", "description": "Crispy duck served with pancakes and hoisin sauce"}
        ],
        "mexican": [
            {"name": "Tacos al Pastor", "description": "Marinated pork tacos with pineapple"},
            {"name": "Guacamole", "description": "Avocado dip with lime and cilantro"},
            {"name": "Enchiladas", "description": "Rolled tortillas with filling and sauce"},
            {"name": "Chiles Rellenos", "description": "Stuffed poblano peppers"}
        ],
        "japanese": [
            {"name": "Sushi Roll Platter", "description": "Various sushi rolls with fresh fish"},
            {"name": "Ramen", "description": "Noodle soup with various toppings"},
            {"name": "Tempura", "description": "Crispy battered seafood and vegetables"},
            {"name": "Tonkatsu", "description": "Breaded pork cutlet"}
        ],
        "mediterranean": [
            {"name": "Greek Salad", "description": "Fresh vegetables with feta and olives"},
            {"name": "Hummus", "description": "Chickpea dip with tahini and olive oil"},
            {"name": "Moussaka", "description": "Layered eggplant and meat casserole"},
            {"name": "Falafel", "description": "Crispy chickpea fritters"}
        ]
    }
    return cuisine_recipes.get(cuisine.lower(), [])

# Main app interface
def main():
    try:
        set_png_as_page_bg('Background.jpeg')
    except Exception as e:
        st.write(f"Error loading background: {e}")
    
    # Centered title and tagline with custom styling
    st.markdown(
        """
        <style>
        .title-container {
            text-align: center;
            padding: 1rem 0;
            max-width: 800px;
            margin: 0 auto;
        }
        .main-title {
            font-size: 3rem;
            font-weight: bold;
            color: white;
        }
        .tagline {
            font-size: 1.2rem;
            color: white;
            font-style: italic;
        }
        
        </style>
        <div class="title-container">
            <h1 class="main-title">RasoiReveal</h1>
            <div class="divider"></div>
            <p class="tagline">Read | Extract | Cook</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Create tabs for different recipe generation methods
    st.markdown("""
        <style>
        /* Custom styling for main tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            padding: 15px;
            display: flex;
            justify-content: center;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            min-width: 150px;
            padding: 0 20px;
            font-size: 1.1em;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.85);
            background: linear-gradient(135deg, rgba(255, 182, 193, 0.2), rgba(255, 192, 203, 0.3));
            border-radius: 25px;
            border: none;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(5px);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, rgba(255, 182, 193, 0.4), rgba(255, 192, 203, 0.5));
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            transform: translateY(-2px) scale(1.05);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 182, 193, 0.2);
        }
        .stTabs [data-baseweb="tab"]:hover::before {
            opacity: 1;
        }
        .stTabs [aria-selected="true"] {
            color: white !important;
            background: linear-gradient(135deg, rgba(255, 182, 193, 0.4), rgba(255, 192, 203, 0.6)) !important;
            box-shadow: 0 4px 20px rgba(255, 182, 193, 0.3) !important;
            transform: translateY(-2px);
        }
        /* Make tab content text bigger */
        .stTabs [role="tabpanel"] {
            font-size: 1.1em;
            padding-top: 1em;
        }
        </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Food Blog", "Recipe Search", "Explore"])
    
    with tab1:
        st.subheader("Extract Recipe from Food Blog")
        blog_url = st.text_input('Enter URL of food blog:')
        
        if blog_url:
            if st.button("Extract Recipe"):
                try:
                    with st.spinner("Extracting recipe information..."):
                        recipe_data = extract_recipe_from_blog(blog_url)
                        display_recipe(recipe_data)
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
    
    with tab2:
        st.subheader("Generate Recipe")
        recipe_request = st.text_input('Enter your recipe request (e.g., "help me cook chicken curry"):')
        
        if recipe_request:
            if st.button("Generate Recipe"):
                try:
                    recipe_result = get_recipe_from_text_request(recipe_request)
                    if recipe_result:
                        st.markdown(recipe_result)
                        
                        # Extract ingredients from the recipe result
                        ingredients = []
                        for line in recipe_result.split('\n'):
                            if line.strip().startswith('-') and not any(section in line.lower() for section in ['instructions:', 'nutrition:', 'additional:']):
                                ingredients.append(line.strip('- '))
                        
                        # Get and display nutrition information
                        if nutrition_data := get_nutrition_info(ingredients):
                            display_nutrition_info(nutrition_data)
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    with tab3:
        st.subheader("Explore Cuisines")
        
        # Add custom CSS for the cuisine blocks and recipe display
        st.markdown("""
            <style>
            .cuisine-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 40px;
                padding: 30px;
            }
            .cuisine-block {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                padding: 25px;
                text-align: center;
                cursor: pointer;
                transition: transform 0.3s;
                margin: 15px;
            }
            .cuisine-block:hover {
                transform: scale(1.05);
                background-color: rgba(0, 0, 0, 0.8);
            }
            .cuisine-block h3 {
                color: white;
                margin-bottom: 10px;
            }
            .cuisine-block p {
                color: rgba(255, 255, 255, 0.9);
            }
            .recipe-card {
                background-color: rgba(0, 0, 0, 0.8);
                border-radius: 8px;
                padding: 40px;
                margin: 30px 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                transition: transform 0.3s;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .recipe-card:hover {
                transform: translateY(-5px);
                background-color: rgba(0, 0, 0, 0.9);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
            }
            .recipe-card h4 {
                color: #ffffff;
                margin-bottom: 10px;
                font-size: 1.2em;
                font-weight: bold;
            }
            .recipe-card p {
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 15px;
                line-height: 1.5;
            }
            .recipe-details {
                margin-top: 20px;
                padding: 20px;
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.8);
                color: #ffffff;
                font-size: 1.1em;
                line-height: 1.6;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .recipe-details h3 {
                color: #ffffff;
                margin-bottom: 15px;
                font-weight: bold;
            }
            .recipe-details h4 {
                color: rgba(255, 255, 255, 0.9);
                margin-top: 20px;
                margin-bottom: 10px;
            }
            .recipe-details ul, .recipe-details ol {
                margin-left: 20px;
                margin-bottom: 15px;
                color: rgba(255, 255, 255, 0.9);
            }
            .recipe-details li {
                margin-bottom: 8px;
            }
            /* Custom styling for cuisine buttons */
            .stButton > button {
                width: 100%;
                height: 80px;
                font-size: 1.5em;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                padding: 10px 20px;
                margin: 10px 0;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .stButton > button:hover {
                background-color: rgba(0, 0, 0, 0.8);
                transform: translateY(-5px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
                border-color: rgba(255, 255, 255, 0.4);
            }
            .stButton > button:active {
                transform: translateY(0);
            }
            </style>
        """, unsafe_allow_html=True)

        # Create cuisine blocks using columns
        col1, col2, col3 = st.columns(3)

        # Store the selected cuisine and recipe in session state
        if 'selected_cuisine' not in st.session_state:
            st.session_state.selected_cuisine = None
        if 'selected_recipe' not in st.session_state:
            st.session_state.selected_recipe = None

        # First row with clickable blocks
        with col1:
            if st.button("Italian 🍝", key="italian"):
                st.session_state.selected_cuisine = "italian"

        with col2:
            if st.button("Indian 🍛", key="indian"):
                st.session_state.selected_cuisine = "indian"

        with col3:
            if st.button("Chinese 🥢", key="chinese"):
                st.session_state.selected_cuisine = "chinese"

        # Second row
        col4, col5, col6 = st.columns(3)

        with col4:
            if st.button("Mexican 🌮", key="mexican"):
                st.session_state.selected_cuisine = "mexican"

        with col5:
            if st.button("Japanese 🍱", key="japanese"):
                st.session_state.selected_cuisine = "japanese"

        with col6:
            if st.button("Mediterranean 🥙", key="mediterranean"):
                st.session_state.selected_cuisine = "mediterranean"

        # Display signature recipes if a cuisine is selected
        if st.session_state.selected_cuisine:
            st.markdown(f"### Signature {st.session_state.selected_cuisine.title()} Recipes")
            recipes = get_signature_recipes(st.session_state.selected_cuisine)
            
            for recipe in recipes:
                recipe_key = f"{st.session_state.selected_cuisine}_{recipe['name'].lower().replace(' ', '_')}"
                st.markdown(f"""
                    <div class="recipe-card">
                        <h4>{recipe['name']}</h4>
                        <p>{recipe['description']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Get Recipe: {recipe['name']}", key=recipe_key):
                    st.session_state.selected_recipe = recipe['name']
                    recipe_result = get_recipe_from_text_request(recipe['name'])
                    if recipe_result:
                        st.markdown(f"""
                            <div class="recipe-details">
                                {recipe_result}
                            </div>
                        """, unsafe_allow_html=True)
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
