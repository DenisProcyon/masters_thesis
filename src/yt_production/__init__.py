import pandas as pd
import numpy as np
import os
import re
import json
from datetime import datetime
from googleapiclient.discovery import build
from time import sleep
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from tqdm import tqdm

# Load environment variables
load_dotenv()
YT_API_KEY = os.getenv("YT_API_KEY")

# Neutral keyword-based descriptions for poverty dimensions: around 30 words per dimension 
# (60% standard spanish, 30% mexican/spanish slang and 10% english)
# POVERTY_DIMENSIONS = {
#     "INCOME": """
#     empleo trabajo salario ingresos dinero economía sueldo ahorro impuestos
#     chamba lana nómina billete jale job salary income money
#     """,
    
#     "ACCESS TO HEALTH SERVICES": """
#     salud médico hospital medicina tratamiento atención clínica seguro
#     sistema de salud servicios médicos doctor cuidado ir al doctor health insurance
#     seguro médico doctor particular ir a consulta healthcare medical treatment 
#     """,
    
#     "EDUCATIONAL LAG": """
#     educación escuela universidad maestro estudiante aprendizaje escuela pública
#     clases formación conocimiento título bachillerato preparatoria escuela secundaria
#     """,
    
#     "ACCESS TO SOCIAL SECURITY": """
#     seguridad social pensión jubilación contrato derechos laborales
#     prestaciones protección IMSS ISSSTE afore finiquito ahorro para retiro
#     cotizar retirement benefits social security worker rights informal job
#     """,
    
#     "HOUSING": """
#     vivienda casa habitación hogar alquiler renta depa housing utilities
#     servicios agua luz gas electricidad construcción propiedad rent 
#     techo colonia vecindario urbanización asentamiento cuartito mortgage
#     """,
    
#     "ACCESS TO FOOD": """
#     alimentación comida nutrición alimentos dieta cocinar recetas
#     canasta básica food security nutrition meal groceries
#     comida saludable dieta balanceada comida rápida comida chatarra
#     """,
    
#     "SOCIAL COHESION": """
#     comunidad sociedad integración participación convivencia barrio raza community
#     respeto diversidad solidaridad inclusión pertenencia 
#     vecinos apoyo redes sociales confianza belonging inclusion
#     """}

# limits for scraping
MAX_VIDEOS_PER_SEARCH = 5
MAX_COMMENTS_PER_VIDEO = 300  
API_SLEEP_TIME = 0.5  

class TextProcessor:
    def __init__(self, dimensions: dict[str, str]):
        self.dimensions = dimensions
        self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
        self.model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
        self.dimension_names = list(dimensions.keys())
        self.dimension_texts = []
        for keywords in dimensions.values():
            word_list = keywords.strip().split()
            phrase = " ".join(word_list)
            self.dimension_texts.append(phrase)
        self.dimension_embeddings = self.embedder.encode(self.dimension_texts, convert_to_tensor=True)

    def clean_text(self, text):
        text = re.sub(r'<.*?>', ' ', text)
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip().lower()

    def classify_dimension(self, text):
        if not text:
            return None, 0.0
        embedding = self.embedder.encode(text, convert_to_tensor=True)
        cosine_scores = util.cos_sim(embedding, self.dimension_embeddings)[0]
        max_idx = torch.argmax(cosine_scores).item()
        return self.dimension_names[max_idx], cosine_scores[max_idx].item()

    def get_sentiment_score(self, text):
        if not text:
            return 0.0
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        stars = torch.argmax(outputs.logits, dim=1).item() + 1
        return (stars - 3) / 2  # Normalize to [-1, 1]

class YouTubeAnalyzer:
    def __init__(self, api_key: str, dimensions: dict[str, str]):
        self.dimensions = dimensions
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.processor = TextProcessor(dimensions)

    def search_videos(self, query, published_after, published_before, max_results=MAX_VIDEOS_PER_SEARCH):
        """Search for videos using a keyword query."""
        videos = []
        next_page_token = None
        
        try:
            while len(videos) < max_results:
                response = self.youtube.search().list(
                    q=query,
                    part="snippet",
                    maxResults=min(50, max_results - len(videos)),  # YouTube API allows max 50 per request
                    pageToken=next_page_token,
                    type="video",
                    order="relevance",
                    publishedAfter=published_after,
                    publishedBefore=published_before,
                    relevanceLanguage="es"
                ).execute()
                
                for item in response.get("items", []):
                    if item["id"]["kind"] == "youtube#video":
                        videos.append({
                            "id": item["id"]["videoId"],
                            "title": item["snippet"]["title"],
                            "description": item["snippet"].get("description", ""),
                            "published_at": item["snippet"]["publishedAt"]
                        })
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(videos) >= max_results:
                    break
                
                sleep(API_SLEEP_TIME)  # Avoid quota exceeded errors
                
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
        
        print(f"Found {len(videos)} videos for query '{query}'")
        return videos

    def get_video_comments(self, video_id, max_comments=MAX_COMMENTS_PER_VIDEO):
        """Get comments for a specific video."""
        comments = []
        next_page_token = None
        
        try:
            while len(comments) < max_comments:
                response = self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),  # YouTube API allows max 100 per request
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get("items", []):
                    comment_text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                    comments.append(comment_text)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(comments) >= max_comments:
                    break
                
                sleep(API_SLEEP_TIME)  # Avoid quota exceeded errors
                
        except Exception as e:
            # Many videos have comments disabled, so we'll just pass silently
            pass
        
        return comments

    def analyze_state_by_keywords(self, state_name, search_terms, date_range):
        """Analyze a state by searching for videos using specified search terms."""
        print(f"\nAnalyzing {state_name}...")
        dimension_stats = {dim: {"sentiment_sum": 0.0, "count": 0} for dim in self.dimensions}
        total_videos = 0
        total_comments = 0
        
        # Search for videos with each search term
        for search_term in search_terms:
            print(f"  Searching for '{search_term}'...")
            videos = self.search_videos(
                query=search_term,
                published_after=date_range["published_after"],
                published_before=date_range["published_before"],
                max_results=MAX_VIDEOS_PER_SEARCH
            )
            
            if not videos:
                continue
                
            total_videos += len(videos)
            
            # Process videos
            for video in tqdm(videos, desc=f"Processing videos for '{search_term}'"):
                # Get video comments
                comments = self.get_video_comments(video["id"], MAX_COMMENTS_PER_VIDEO)
                total_comments += len(comments)
                
                # Concatenate title, description and comments for analysis
                all_texts = [video["title"] + ". " + video["description"]] + comments
                
                # Analyze each text
                for text in all_texts:
                    clean = self.processor.clean_text(text)
                    if len(clean) < 10:  # Skip very short texts
                        continue
                        
                    dimension, confidence = self.processor.classify_dimension(clean)
                    if confidence > 0.1:  # Only count if confidence is high enough
                        sentiment = self.processor.get_sentiment_score(clean)
                        dimension_stats[dimension]["sentiment_sum"] += sentiment
                        dimension_stats[dimension]["count"] += 1
        
        print(f"  Analyzed {total_videos} videos and {total_comments} comments for {state_name}")

        return dimension_stats, total_videos, total_comments
    
def get_states_search_terms(states: list[str]) -> dict[str, list]:
    result = {}
    for state in states:
        terms = ["noticias", "news", "economía"]
        result[state] = [f'{state.capitalize()} {term}' for term in terms]
    
    return result

def analyze_all_states(start_year: int, end_year: int, states: list[str], dimensions: dict[str, str]) -> list[pd.DataFrame]:
    analyzer = YouTubeAnalyzer(YT_API_KEY, dimensions=dimensions)
    date_range = {
        "published_after": f'{start_year}-01-01T00:00:00Z',
        "published_before": f'{end_year}-12-31T23:59:59Z'
    }
    
    # Create directories for results
    os.makedirs(f'yt_data_{start_year}_{end_year}', exist_ok=True)
    
    # Store overall stats for summary
    all_results = []

    states_search_terms = get_states_search_terms(states[0:1])
    
    for state, search_terms in states_search_terms.items():
        stats, total_videos, total_comments = analyzer.analyze_state_by_keywords(
            state_name=state,
            search_terms=search_terms,
            date_range=date_range
        )
        
        # Create dataframe for this state
        df = pd.DataFrame([
            {
                "state": state,
                "dimension": dim.replace("_", " ").title(),
                "avg_sentiment": v["sentiment_sum"] / v["count"] if v["count"] else 0,
                "mentions_count": v["count"],
                "videos_analyzed": total_videos,
                "comments_analyzed": total_comments
            }
            for dim, v in stats.items()
        ])
        
        # Save state-specific results
        output_file = f"yt_data_{start_year}_{end_year}/{state.replace(' ', '_').lower()}.csv"
        df.to_csv(output_file, index=False)
        print(f"Saved results to {output_file}")
        
        # Add to overall results
        all_results.append(df)

    return all_results