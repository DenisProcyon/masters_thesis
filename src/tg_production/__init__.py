import pandas as pd
import numpy as np
import re
from tqdm import tqdm
import os
from sentence_transformers import SentenceTransformer, util
import torch
from dotenv import load_dotenv
from mongo_wrapper.mongo_wrapper import MongoWrapper

load_dotenv()

# STATES = [
#     "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", "Chihuahua",
#     "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México", "Guanajuato", 
#     "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", 
#     "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", 
#     "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"]

# TARGET_CHANNELS = [
#     "elpaismexico_2020",
#     "ElUniversalOnline_2020",
#     "proceso_unofficial_2020",
#     "politicomx_2020",
#     "lajornada_unofficial_2020",
#     "larazondemexico_2020",
#     "sinembargomx_2020",
#     "elpaisamerica_2020",
#     "animalpolitico_2020",
#     "ElEconomista_MTY_2020"
#     ]

# define dimensions of poverty 
# POVERTY_DIMENSIONS = {
#     "INCOME": """
#     desempleo salario mínimo bajos ingresos deudas familiares pobreza laboral
#     pérdida de empleo ingreso insuficiente precariedad laboral empleo informal
#     falta de oportunidades laborales reducción de salario inestabilidad económica
#     recesión subempleo despidos masivos contratos temporales informalidad
#     costos de vida elevados falta de empleo formal insuficiencia salarial
#     """,

#     "ACCESS TO HEALTH SERVICES": """
#     falta de acceso a servicios de salud hospitales saturados escasez de medicamentos 
#     deficiencias en la atención médica carencia de personal médico emergencia sanitaria
#     costos elevados de tratamientos cierre de centros de salud lista de espera prolongada
#     equipos médicos inoperantes desabasto de vacunas falta de atención especializada
#     """,

#     "EDUCATIONAL_LAG": """
#     deserción escolar suspensión de clases carencia de docentes  
#     dificultades de acceso a la educación educación interrumpida rezago académico 
#     falta de recursos escolares acceso desigual a la educación deficiencias en formación 
#     básica carencia de materiales educativos 
#     """,

#     "ACCESS TO SOCIAL SECURITY": """
#     empleo informal ausencia de prestaciones sociales falta de contrato laboral 
#     exclusión del sistema de pensiones carencia de protección social trabajo precario 
#     derechos laborales no garantizados falta de cotización al sistema desprotección estructural
#     dificultades para acceder al seguro social informalidad laboral empleo sin afiliación
#     """,

#     "HOUSING": """
#     vivienda precaria hacinamiento falta de servicios básicos 
#     infraestructura deteriorada zonas marginadas viviendas inseguras
#     """,
    
#     "ACCESS TO FOOD": """
#     inseguridad alimentaria acceso limitado a alimentos inflación precios
#     raciones insuficientes pobreza alimentaria aumento de precios comeder comunitario
#     canasta básica crisis alimentaria comida pobre ayuda alimentaria 
#     insuficiencia nutricional alimentación deficiente encarecimiento de alimentos
#     inflación en alimentos carencia alimentaria productos básicos banco de alimentos
#     alimentos inaccesibles gasto alimentario elevado programas alimentarios
#     """,

#     "SOCIAL_COHESION": """
#     discriminación étnica marginación social exclusión comunidades vulnerables
#     conflictos intercomunitarios tensiones sociales barreras sociales 
#     desigualdad aislamiento social
#     """}

# initialize the classifier with Spanish sentence embeddings model and precompute embeddings for all poverty dimensions
class PovertyDimensionClassifier:
    def __init__(self, dimensions: dict[str, str]):
        self.dimensions = dimensions

        # load Spanish sentence transformer model optimized for semantic similarity
        self.model = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es')
        
        # store dimension names for easy reference
        self.dimension_names = list(self.dimensions.keys())
        
        # precompute embeddings for all poverty dimension descriptions
        self.dimension_embeddings = self.model.encode(
            list(self.dimensions.values()), 
            convert_to_tensor=True)
    
    # clean and preprocess text for better embedding quality
    def clean_text(self, text):
        if not isinstance(text, str):
            return ""
        
        # remove HTML tags that might appear in Telegram posts
        text = re.sub(r'<.*?>', ' ', text)
        
        # remove URLs and links
        text = re.sub(r'http\S+', '', text)
        
        # keep only alphanumeric characters and Spanish accented letters
        text = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', text)
        
        # normalize whitespace and convert to lowercase
        return re.sub(r'\s+', ' ', text).strip().lower()
    
    # classify text into poverty dimensions using semantic similarity
    def classify_text(self, text, threshold=0.10):
        if not text:
            return None, 0.0
        
        # clean the input text
        cleaned_text = self.clean_text(text)
        
        # skip very short texts as they might lack semantic content
        if len(cleaned_text) < 10:
            return None, 0.0
        
        # generate embedding for the input text
        text_embedding = self.model.encode(cleaned_text, convert_to_tensor=True)
        
        # compute cosine similarity between text and all poverty dimensions
        cosine_scores = util.cos_sim(text_embedding, self.dimension_embeddings)[0]
        
        # find the dimension with highest similarity score
        max_idx = torch.argmax(cosine_scores).item()
        max_score = cosine_scores[max_idx].item()
        
        # classify into one of the dimension only if similarity exceeds threshold
        if max_score >= threshold:
            return self.dimension_names[max_idx], max_score
        else:
            return None, max_score
        
# load Telegram posts from MongoDB and classify them by Mexican states
def load_state_posts(states: list[str], channel_collections: list[str]):
    # connect to MongoDB
    mongo_client = MongoWrapper(
        db=os.getenv("MONGO_DB"),
        user=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        ip=os.getenv("MONGO_IP"),
        port=os.getenv("MONGO_PORT"))
    
    all_channels = mongo_client.get_all_collections()
    available_target_channels = [
        channel for channel in channel_collections
        if channel in all_channels]
    
    # initialize dictionary to store posts categorized by state
    state_posts = {state: [] for state in states}
    
    # create regex patterns for each state to identify mentions in posts - match complete state names, not partial matches
    state_patterns = {
        state: re.compile(r'\b' + re.escape(state) + r'\b', re.IGNORECASE) 
        for state in states}
    
    # process each available target channel
    for channel in tqdm(available_target_channels, desc="Loading channels"):
        # retrieve all posts from the current channel
        posts = mongo_client.get_collection_entries(collection=channel)
        print(f"Channel: {channel} - {len(posts)} posts found")
        # process each post in the channel
        for post in tqdm(posts, desc=f"Analyzing {channel}", leave=False):
            post_text = post.get('text', '')
            # check if post mentions any of the Mexican states   
            for state, pattern in state_patterns.items():
                if pattern.search(post_text):
                    # store post if state is mentioned
                    state_posts[state].append(post_text)  
    
    # convert to df 
    for state in states:
        if state_posts[state]:
            state_posts[state] = pd.DataFrame(state_posts[state], columns=['text'])
        else:
            state_posts[state] = pd.DataFrame(columns=['text'])
    
    return state_posts


# analyze all posts for each state and classify them into poverty dimensions
def analyze_poverty_dimensions(state_posts, dimensions: dict[str, str]):
    # initialize the classifier
    classifier = PovertyDimensionClassifier(dimensions)
    
    # store results for all states and dimensions
    results = []

    # process each state individually
    for state, df in state_posts.items():
        print(f"\nAnalyzing {state} ({len(df)} posts)...")
    
        # initialize counters for each poverty dimension plus the "other" category - fallback for posts not related to 
        # any dimension or posts that do not exceed the threshold
        dimension_counts = {dim: 0 for dim in dimensions.keys()}
        dimension_counts["OTHER"] = 0  
    
        # classify each post in the current state
        for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Classifying {state}"):
            text = row['text']
        
            # get classification result from the classifier
            dimension, _ = classifier.classify_text(text)
        
            # increment counter for the identified dimension or "other"
            if dimension:
                dimension_counts[dimension] += 1
            else:
                dimension_counts["OTHER"] += 1
        
        total_posts = len(df)
        dimension_percentages = {
            dim: (count / total_posts) * 100 
            if total_posts != 0 else 0.0
            for dim, count in dimension_counts.items()}
        print(f"\nResults for {state}:")
        print(f"Total posts: {total_posts}")
        print("\nDistribution of posts across poverty dimensions:")
        
        for dim, count in dimension_counts.items():
            dim_name = dim if dim != "OTHER" else "Non-poverty posts"
            pct = dimension_percentages[dim]
            print(f"- {dim_name}: {count} posts ({pct:.1f}%)")
        
        for dim in list(dimensions.keys()) + ["OTHER"]:
            results.append({
                'state': state,
                'dimension': dim,
                'count': dimension_counts[dim],
                'percentage': dimension_percentages[dim],
                'total_posts': total_posts})
    
    results_df = pd.DataFrame(results)

    return results_df

def launch(start_year: int, end_year: str, states: list[str], channel_collections: list[str], dimensions: dict[str, str]) -> pd.DataFrame:
    state_posts = load_state_posts(states, channel_collections)
    
    results = analyze_poverty_dimensions(state_posts, dimensions)
    
    results.to_csv(f'tg_{start_year}_{end_year}.csv', index=False)

    return results
