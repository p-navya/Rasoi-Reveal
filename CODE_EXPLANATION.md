# Detailed Code Explanation

## 1. Application Structure

### Main Application File (app.py)
The application is built using Streamlit and follows a modular structure with three main tabs:

```python
# Main application structure
tab1, tab2, tab3 = st.tabs(["From Food Blog", "Direct Recipe Request", "Explore Cuisines"])
```

### Tab 1: Food Blog Recipe Extraction
```python
with tab1:
    st.subheader("Extract Recipe from Food Blog")
    col1, col2 = st.columns([1, 2, 1])
    with col2:
        blog_url = st.text_input('Enter URL of food blog:')
        if blog_url:
            if st.button("Extract Recipe"):
                recipe_data = extract_recipe_from_blog(blog_url)
                display_recipe(recipe_data)
```
This tab handles recipe extraction from food blogs using the `extract_recipe_from_blog` function.

### Tab 2: Direct Recipe Generation
```python
with tab2:
    st.subheader("Generate Recipe")
    col1, col2 = st.columns([1, 2, 1])
    with col2:
        recipe_request = st.text_input('Enter your recipe request:')
        if recipe_request:
            if st.button("Generate Recipe"):
                recipe_result = get_recipe_from_text_request(recipe_request)
                display_recipe(recipe_result)
```
This tab handles direct recipe generation using the Spoonacular API.

### Tab 3: Cuisine Exploration
```python
with tab3:
    st.subheader("Explore Cuisines")
    # Cuisine selection and recipe display
    if st.session_state.selected_cuisine:
        recipes = get_signature_recipes(st.session_state.selected_cuisine)
        display_recipes(recipes)
```
This tab allows users to explore recipes by cuisine type.

## 2. Core Functions

### Recipe Extraction Function
```python
def extract_recipe_from_blog(url):
    """
    Extracts recipe information from a food blog URL.
    
    Parameters:
        url (str): The URL of the food blog
    
    Returns:
        dict: Structured recipe information including:
            - title
            - ingredients
            - instructions
            - cook_time
            - servings
    """
    try:
        # Fetch and parse HTML content
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract recipe data from JSON-LD schema
        recipe_data = extract_from_schema(soup)
        if recipe_data:
            return recipe_data
            
        # Fallback to HTML parsing
        return extract_from_html(soup)
        
    except Exception as e:
        st.error(f"Error extracting recipe: {str(e)}")
        return None
```

### Recipe Generation Function
```python
def get_recipe_from_text_request(text_request):
    """
    Generates recipe information from text input using Spoonacular API.
    
    Parameters:
        text_request (str): User's recipe request
    
    Returns:
        str: Formatted recipe information
    """
    try:
        # Search for recipes using Spoonacular API
        search_url = "https://api.spoonacular.com/recipes/complexSearch"
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "query": text_request,
            "addRecipeInformation": True,
            "addRecipeNutrition": True
        }
        
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if data.get("results"):
            recipe = data["results"][0]
            return format_recipe(recipe)
            
        return "No recipes found matching your request."
        
    except Exception as e:
        st.error(f"Error generating recipe: {str(e)}")
        return None
```

### Nutrition Information Function
```python
def get_nutrition_info(ingredients):
    """
    Calculates nutrition information for a list of ingredients.
    
    Parameters:
        ingredients (list): List of ingredients
    
    Returns:
        dict: Nutrition information including:
            - calories
            - protein
            - fat
            - carbs
            - fiber
            - sugar
            - sodium
            - cholesterol
    """
    try:
        # Calculate nutrition using Spoonacular API
        nutrition_url = "https://api.spoonacular.com/recipes/guessNutrition"
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "title": "Recipe",
            "ingredientList": ",".join(ingredients)
        }
        
        response = requests.get(nutrition_url, params=params)
        return response.json()
        
    except Exception as e:
        st.error(f"Error calculating nutrition: {str(e)}")
        return None
```

## 3. UI Components and Styling

### Custom CSS Styling
```css
/* Main tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
    padding: 20px 0;
    background-color: rgba(255, 192, 203, 0.1);
    border-radius: 20px;
    margin: 20px 0;
}

/* Tab button styling */
.stTabs [data-baseweb="tab"] {
    height: 50px;
    min-width: 150px;
    padding: 0 20px;
    font-size: 1.1em;
    background: linear-gradient(135deg, rgba(255, 182, 193, 0.2), rgba(255, 192, 203, 0.3));
    border-radius: 25px;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Input box styling */
.stTextInput > div > div > input {
    height: 50px;
    font-size: 1.1em;
    padding: 10px 15px;
    border-radius: 10px;
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
}
```

### Recipe Card Component
```python
def display_recipe(recipe_data):
    """
    Displays recipe information in a formatted card.
    
    Parameters:
        recipe_data (dict): Recipe information
    """
    st.markdown(f"""
        <div class="recipe-card">
            <h4>{recipe_data['title']}</h4>
            <p>{recipe_data['description']}</p>
        </div>
    """, unsafe_allow_html=True)
```

## 4. Error Handling and Validation

### Input Validation
```python
def validate_url(url):
    """
    Validates the input URL.
    
    Parameters:
        url (str): URL to validate
    
    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
```

### Error Handling
```python
try:
    # API call or data processing
    response = requests.get(url)
    data = response.json()
except requests.exceptions.RequestException as e:
    st.error(f"Network error: {str(e)}")
except json.JSONDecodeError as e:
    st.error(f"Invalid response format: {str(e)}")
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")
```

## 5. State Management

### Session State
```python
# Initialize session state variables
if 'selected_cuisine' not in st.session_state:
    st.session_state.selected_cuisine = None
if 'selected_recipe' not in st.session_state:
    st.session_state.selected_recipe = None
```

### State Updates
```python
# Update state on user interaction
if st.button("Select Cuisine"):
    st.session_state.selected_cuisine = cuisine
```

## 6. API Integration

### Spoonacular API
```python
# API configuration
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')

# API endpoints
SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch"
NUTRITION_URL = "https://api.spoonacular.com/recipes/guessNutrition"
```

### API Request Handling
```python
def make_api_request(url, params):
    """
    Makes an API request with error handling.
    
    Parameters:
        url (str): API endpoint
        params (dict): Request parameters
    
    Returns:
        dict: API response
    """
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None
```

## 7. Data Processing

### Recipe Data Formatting
```python
def format_recipe(recipe_data):
    """
    Formats recipe data for display.
    
    Parameters:
        recipe_data (dict): Raw recipe data
    
    Returns:
        str: Formatted recipe information
    """
    return f"""
        ### {recipe_data['title']}
        
        #### Ingredients:
        {format_ingredients(recipe_data['ingredients'])}
        
        #### Instructions:
        {format_instructions(recipe_data['instructions'])}
        
        #### Nutrition Information:
        {format_nutrition(recipe_data['nutrition'])}
    """
```

### Nutrition Data Processing
```python
def process_nutrition_data(nutrition_data):
    """
    Processes and formats nutrition information.
    
    Parameters:
        nutrition_data (dict): Raw nutrition data
    
    Returns:
        dict: Processed nutrition information
    """
    return {
        'calories': round(nutrition_data.get('calories', 0)),
        'protein': round(nutrition_data.get('protein', 0), 1),
        'fat': round(nutrition_data.get('fat', 0), 1),
        'carbs': round(nutrition_data.get('carbs', 0), 1),
        'fiber': round(nutrition_data.get('fiber', 0), 1),
        'sugar': round(nutrition_data.get('sugar', 0), 1),
        'sodium': round(nutrition_data.get('sodium', 0)),
        'cholesterol': round(nutrition_data.get('cholesterol', 0))
    }
``` 