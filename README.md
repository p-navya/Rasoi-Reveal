# RasoiReveal - Recipe Generator and Extractor

A Streamlit-based web application that helps users extract recipes from food blogs, generate recipes from text requests, and explore different cuisines.

## Features

### 1. Recipe Extraction from Food Blogs
- Extract recipes from any food blog URL
- Parses structured data (JSON-LD) and HTML content
- Extracts ingredients, instructions, cooking time, and other details
- Clean and formatted display of recipe information

### 2. Direct Recipe Generation
- Generate recipes from text requests
- Uses Spoonacular API for recipe search and generation
- Provides detailed recipe information including:
  - Ingredients list
  - Step-by-step instructions
  - Nutrition information
  - Cooking time and servings
  - Dietary tags and cuisine type

### 3. Cuisine Exploration
- Browse recipes by cuisine type
- Six major cuisines available:
  - Italian 🍝
  - Indian 🍛
  - Chinese 🥢
  - Mexican 🌮
  - Japanese 🍱
  - Mediterranean 🥙
- Signature recipes for each cuisine
- Detailed recipe information on selection

## Technical Details

### Dependencies
- streamlit
- pytube
- whisper
- requests
- beautifulsoup4
- pandas
- python-dotenv
- torch

### API Integration
- Spoonacular API for recipe generation and nutrition information
- YouTube API for video processing (if needed)

### Key Functions

1. **Recipe Extraction**
```python
def extract_recipe_from_blog(url):
    # Extracts recipe data from blog URLs
    # Returns structured recipe information
```

2. **Recipe Generation**
```python
def get_recipe_from_text_request(text_request):
    # Generates recipes from text input
    # Uses Spoonacular API
```

3. **Nutrition Information**
```python
def get_nutrition_info(ingredients):
    # Calculates nutrition information for recipes
    # Returns detailed nutrition breakdown
```

4. **Cuisine Management**
```python
def get_signature_recipes(cuisine):
    # Returns signature recipes for each cuisine
```

### UI Components

1. **Main Tabs**
- Food Blog (Recipe extraction)
- Recipe Search (Direct generation)
- Explore (Cuisine browsing)

2. **Styling**
- Custom CSS for modern, responsive design
- Dark theme with transparent elements
- Smooth transitions and hover effects
- Mobile-friendly layout

## Usage

1. **Extract Recipe from Blog**
   - Enter the food blog URL
   - Click "Extract Recipe"
   - View formatted recipe information

2. **Generate Recipe**
   - Enter your recipe request
   - Click "Generate Recipe"
   - View complete recipe with nutrition info

3. **Explore Cuisines**
   - Select a cuisine type
   - Browse signature recipes
   - Click "Get Recipe" for detailed information

## Error Handling

- Graceful error handling for API failures
- User-friendly error messages
- Fallback mechanisms for data extraction
- Input validation for URLs and requests

## Future Improvements

1. **Recipe Management**
   - Save favorite recipes
   - Create custom recipe collections
   - Share recipes with others

2. **Enhanced Features**
   - Recipe scaling
   - Unit conversion
   - Shopping list generation
   - Meal planning

3. **UI Enhancements**
   - Dark/Light theme toggle
   - Custom recipe input
   - Recipe ratings and reviews
   - Social sharing options

## Setup and Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables:
```bash
SPOONACULAR_API_KEY=your_api_key
```
4. Run the application:
```bash
streamlit run app.py
```

## Contributing

Feel free to submit issues and enhancement requests!