# load necessary libraries
import pandas as pd
import numpy as np
from datetime import datetime
from mongo_wrapper.mongo_wrapper import MongoWrapper
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

STATES = [
    "MX-AGU", "MX-BCN", "MX-BCS", "MX-CAM", "MX-CHP", "MX-CHH",
    "MX-COA", "MX-COL", "MX-DUR", "MX-GUA", "MX-GRO", "MX-HID",
    "MX-JAL", "MX-DIF", "MX-MIC", "MX-MOR", "MX-NAY", "MX-NLE",
    "MX-OAX", "MX-PUE", "MX-QUE", "MX-ROO", "MX-SLP", "MX-SIN",
    "MX-SON", "MX-MEX", "MX-TAB", "MX-TAM", "MX-TLA", "MX-VER",
    "MX-YUC", "MX-ZAC"]

keywords = [
    "crisis,desempleo,pobreza",
    "conflictos,discriminación", 
    "violencia,becas,escuela secundaria,enfermedad,centro de salud",
    "pensiones,seguro social,ayuda alimentaria,banco de alimentos,comedor comunitario",
    "comida barata,receta pobre,apoyo Infonavit,ayuda renta,renta barata",
    "servicios en la vivienda,vivienda del gobierno", 
    "agua potable, FOVISSSTE",
    "tianguis, tiendeo, PromoDescuentos"]

# create a list of all unique keywords for processing
ALL_KEYWORDS = []
for dimension_words in POVERTY_DIMENSIONS.values():
    ALL_KEYWORDS.extend(dimension_words)
ALL_KEYWORDS = list(set(ALL_KEYWORDS))  # remove duplicates

# from the timeseries - which go from 2004 onwards - extract only the year so that we can filter the data by year of interest
def extract_year_from_timestamp(timestamp):
    return datetime.fromtimestamp(int(timestamp)).year

# for each word, compute the average value for each year
def extract_individual_word_averages(raw_data, target_years=[2020, 2022]):
    if 'interest_over_time' not in raw_data:
        return {}
    
    timeline_data = raw_data['interest_over_time']['timeline_data']
    
    # define a dictionary: {year: {word: [values]}}
    yearly_word_data = defaultdict(lambda: defaultdict(list))
    
    for entry in timeline_data:
        timestamp = entry['timestamp']
        year = extract_year_from_timestamp(timestamp)
        
        # keep only the years we are interested in 
        if year in target_years:
            for value_entry in entry['values']:
                word = value_entry['query']
                extracted_value = value_entry['extracted_value']
                yearly_word_data[year][word].append(extracted_value)
    
    # compute the average for each word in each year
    result = {}
    for year in yearly_word_data:
        result[year] = {}
        for word in yearly_word_data[year]:
            values = yearly_word_data[year][word]
            if values:
                result[year][word] = round(np.mean(values), 2)
            else:
                result[year][word] = 0
    
    return result

# after computing the averages for each word, we aggregate words that belong to the same dimension and calculate its average 
def calculate_dimension_averages(word_averages):
    dimension_averages = {}
    
    for year, words_data in word_averages.items():
        dimension_averages[year] = {}
        
        for dimension, dimension_words in POVERTY_DIMENSIONS.items():
            available_values = []
            for word in dimension_words:
                if word in words_data and words_data[word] > 0:
                    available_values.append(words_data[word])
            if available_values:
                dimension_averages[year][dimension] = round(np.mean(available_values), 2)
            else:
                dimension_averages[year][dimension] = 0
    
    return dimension_averages

# process all states to extract individual words data and dimension averages
def process_all_states():
    mongo_client = MongoWrapper(
        db="serpapi_5y",
        user=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        ip=os.getenv("MONGO_IP"),
        port=os.getenv("MONGO_PORT"))
    
    all_states_data = {}
    
    for state in STATES:
        state_word_data = defaultdict(lambda: defaultdict(list))
        
        for keyword_set in keywords:
            collection_name = f'serpapi_timeseries_{state}_{keyword_set}'
            try:
                gt_data = mongo_client.get_collection_entries(collection=collection_name)
                if gt_data:
                    raw_data = gt_data[0]
                    word_averages = extract_individual_word_averages(raw_data)
                    for year in word_averages:
                        for word, avg_value in word_averages[year].items():
                            if word in ALL_KEYWORDS:
                                state_word_data[year][word].append(avg_value)
            except Exception:
                continue
        
        if state_word_data:
            final_state_data = {}
            for year in [2020, 2022]:
                final_state_data[year] = {}
                for word in ALL_KEYWORDS:
                    if word in state_word_data[year] and state_word_data[year][word]:
                        final_state_data[year][word] = round(np.mean(state_word_data[year][word]), 2)
                    else:
                        final_state_data[year][word] = 0
            all_states_data[state] = final_state_data
    return all_states_data

# create output files for each year with individual words and dimension averages
def create_output_files(all_states_data):
    target_years = [2020, 2022]

    result = []
    
    # create columns for indivual averages and dimensions averages 
    for year in target_years:
        rows = []
        for state, state_data in all_states_data.items():
            if year in state_data:
                row = {'state': state}
                for word in ALL_KEYWORDS:
                    row[word] = state_data[year].get(word, 0)
                
                dimension_averages = calculate_dimension_averages({year: state_data[year]})
                if year in dimension_averages:
                    for dimension, avg_value in dimension_averages[year].items():
                        row[f"{dimension}_Dimension"] = avg_value
                rows.append(row)
        
        if rows:
            df = pd.DataFrame(rows)
            word_cols = [col for col in df.columns if col in ALL_KEYWORDS]
            dimension_cols = [col for col in df.columns if col.endswith('_Dimension')]
            ordered_cols = ['state'] + sorted(word_cols) + sorted(dimension_cols)
            df = df[ordered_cols]
            filename = f'google_trends_poverty_{year}.csv'
            df.to_csv(filename, index=False)

def launch():
    all_states_data = process_all_states()
    if all_states_data:
        create_output_files(all_states_data)
        return all_states_data
    else:
        return None