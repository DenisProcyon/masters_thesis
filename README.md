# Real-Time Multidimensional Poverty Nowcasting in Mexico

## Overview  
This project develops a data-driven tool for real-time detection and quantification of **multidimensional poverty** across all 32 Mexican states. By leveraging text-rich data from social media platforms and news outlets, the tool bridges the gap between **outdated official statistics** and **real-time needs**, enabling more timely and targeted social interventions.

This work is part of a thesis project aimed at creating a robust framework for nowcasting poverty across its multiple dimensions. The urgency of this task is particularly high in the Mexican context, where persistent structural problems — including poverty, inequality, and lack of state presence — provide fertile ground for the expansion of criminal organizations.

---

## 🎯 Motivation  
Traditional poverty estimation methods rely on **infrequent surveys** and often **outdated data**. Mexico’s latest official multidimensional poverty statistics date back to **2022**, creating a lag in capturing current socioeconomic dynamics.

This project responds to the need for:
- Real-time insights into poverty dynamics  
- Early-warning systems for deteriorating conditions  
- Enhanced intervention targeting based on current conditions  

---

## 🗂 Repository Structure  


```plaintext
masters_thesis/
├── archive/                  # Archived files (content not shown)
├── requirements.txt          # Python dependencies
├── src/                      # Source code and main notebooks
├── README.md                 # Project overview
├── Mongo.log                 # MongoDB log file
├── url_decoder.log           # URL decoder log

```

### `src`

This folder contains all the core components of the thesis pipeline:

- **Data scraping modules**  
  Code to collect text data from YouTube, Telegram, Google Trends, MediaCloud, and online news.  

- **Main analysis notebooks**  
  Jupyter notebooks for processing and analyzing each digital signal (`*_FINAL.ipynb`), storing the resuling data (`*_data`) and building the nowcasting model (`FINAL_NOWCAST.ipynb`).

- **Production-level code**  
  Code to automate the entire pipeline in a user-friendly interface and create the Grafana dashboard.   

Each data source has dedicated parsing modules:

**Telegram Parsing:**
- `src/telegram_pplt.py` - Main Telegram scraper using Telethon API
- `src/tg_scraper/` - Telegram scraping utilities
- `src/tg_production/__init__.py` - Production Telegram data processing

**YouTube Parsing:**
- `src/yt_client/yt_client.py` - YouTube API client for video and comment extraction
- `src/yt_production/__init__.py` - Production YouTube data processing
- `src/YT_FINAL.ipynb` - YouTube data analysis and processing pipeline

**News Outlets Parsing:**
- `src/newsapi_parser.py` - Google News API parser with proxy support
- `src/mediacloud_api.py` - MediaCloud API integration
- `src/google_news_production/` - Production Google News processing
- `src/mediacloud_production/__init__.py` - Production MediaCloud processing
- `src/trafilatura_production/__init__.py` - Content extraction from news URLs
- `src/gnews_decoder.py` - URL decoding for Google News articles
- `src/NEWS_FINAL.ipynb` - News data analysis and LDA topic modeling

**Google Trends Parsing:**
- `src/serp_google_trends.py` - SerpAPI Google Trends scraper
- `src/serpapi_production/__init__.py` - Production SerpAPI processing
- `src/gt_production/__init__.py` - Google Trends data processing
- `src/GT_final.ipynb` - Google Trends analysis pipeline

**Data Storage & Processing:**
- `src/mongo_wrapper/mongo_wrapper.py` - MongoDB interface for all data sources
- `src/logger/logger.py` - Logging system for all parsers

---


## 🌐 Data Collection  

We use four heterogeneous sources to capture different forms of textual expression and public discourse:

### 1. **Telegram**  
- Scraped using [`telethon`](https://github.com/LonamiWebs/Telethon)  
- Political and economic Mexican channels (e.g., *El Universal*, *Sin Embargo MX*)  
- Messages are classified by State and stored in MongoDB  
- Posts are categorized into poverty dimensions using Spanish keyword embeddings  

### 2. **YouTube**  
- Scraped using the official Google API  
- For each state: `state + noticias/economía/news`  
- 300 videos per state and up to 300 comments per video  
- No MongoDB storage: comments are processed after scraping  
- Comments classified by dimension using multilingual embeddings  

### 3. **News Outlets**  
- Data from **Google News** and **MediaCloud**  
- Filtered by articles mentioning each Mexican state  
- Decoded redirected URLs and scraped full text using `trafilatura`  
- News processed via LDA to extract topics per state/year  

### 4. **Google Trends**  
- Accessed via **SerpApi**  
- Queried using 3–4 keywords per poverty dimension  
- We aggregate interest over time per dimension and state  

---

## 🧪 Data Processing  

Each source required tailored NLP approaches due to the diversity in formality, language, and depth:

### Word Embedding Classification  
Used to assign YouTube comments and Telegram posts to poverty dimensions.

- **YouTube**:  
  `paraphrase-multilingual-MiniLM-L12-v2` – multilingual, informal/jargon-rich  
- **Telegram**:  
  `hiiamsid/sentence_similarity_spanish_es` – formal, Spanish-optimized  

### Sentiment Analysis (YouTube Only)  
- Model: `nlptown/bert-base-multilingual-uncased-sentiment`  
- Original scores [0–5] normalized to [-1, 1]  
- Not applied to Telegram, as posts are factual/news-like  

### LDA Topic Modeling (News)  
- 8 topics fitted per state/year  
- Reduced topic overlap via `eta` and `alpha` tuning  
- LDA output: topic share vector per state  

---

## 🧩 Components Retrieved  

From the above analysis, we extract the following components:

- **YouTube Conditional Sentiment Score**: average sentiment per dimension and state  
- **YouTube Dimension Share**: percentage of comments discussing each dimension  
- **Telegram Dimension Share**: percentage of posts discussing each dimension  
- **LDA Topic Shares**: state-level topic distribution from news  
- **Google Trends Interest**: average interest per poverty dimension  

---

## 📈 Stacked Regression for Poverty Nowcasting  

We implement a **three-stage stacking ensemble** to nowcast multidimensional poverty:

**Stage 1 - Feature Selection**: LASSO regression (α=1.0) independently selects relevant predictors for each poverty dimension from 39 text-based indicators, addressing the high-dimensional, small-sample challenge.

**Stage 2 - Base Learners**: Two complementary models generate predictions:
- **Random Forest**: Captures non-linear relationships and feature interactions (low bias, moderate variance)
- **PLS Regression**: Provides stable linear modeling with 2 latent components (higher bias, low variance)

**Stage 3 - Meta-Learning**: Linear regression optimally combines base learner predictions using 5-fold cross-validation to prevent overfitting.

The ensemble leverages bias-variance complementarity: Random Forest handles complex patterns while PLS ensures prediction stability in small-sample settings. Fixed hyperparameters prevent CV instability common with limited observations (32 states).

### Data & Evaluation

**Training**: 2020 poverty data  
**Validation**: 2022 out-of-sample predictions  
**Metrics**: R², MAE across six poverty dimensions (income, health, education, social security, housing, food)

---

## Results

### 🔢 Mean Absolute Error (MAE) by Dimension

| Dimension         | MAE       |
|------------------|-----------|
| income           | 9.44      |
| health           | 11.48     |
| food             | 4.38      |
| education        | 3.24      |
| social_security  | 8.97      |
| housing          | 5.31      |
| **Average**      | **7.14**  |

> Note: `r²` values and features used per dimension are available in `metrics.csv`

### 📈 Visual Results

#### ❌ Worst Performing Dimensions

The following dimensions showed the **poorest predictive performance**. This is likely due to the fact that they are **highly sensitive to short-term economic and health shocks**, such as those caused by the COVID-19 pandemic. Since the model was trained on data from 2020 (a year deeply impacted by the pandemic) and validated on 2022 (a partial recovery period), the underlying conditions for these dimensions changed significantly between training and prediction periods.

- **Income**: Subject to large fluctuations due to lockdowns, informal work disruption, and government aid  
- **Health**: Severely impacted by pandemic-related strain on the healthcare system  
- **Food**: Affected by supply chain interruptions and inflation in basic goods  

![income](src/out_sample_val/income_plot.png)  
![health](src/out_sample_val/health_plot.png)  
![food](src/out_sample_val/food_plot.png)  

#### ✅ Best Performing Dimensions

These dimensions achieved **better prediction accuracy**, as they reflect more **structural and slowly-evolving aspects** of multidimensional poverty. Unlike income or health, they are less influenced by short-term shocks like the COVID-19 crisis, and thus the model generalizes more robustly across years.

- **Education**: Although affected by school closures, structural gaps remain stable over time  
- **Social Security**: Mostly tied to institutional access, which evolves gradually  
- **Housing**: Based on physical conditions or infrastructure, typically slow-changing  

![education](src/out_sample_val/education_plot.png)  
![social_security](src/out_sample_val/social_security_plot.png)  
![housing](src/out_sample_val/housing_plot.png)



## 📉 PCA for Nowcasting without Targets

Since social cohesion lacks a direct target variable, we construct a **latent index** using **Principal Component Analysis (PCA)**. We implemented the following steps:

- **Feature Selection**: All variables containing "cohesion" are selected.

- **PCA Extraction**: After standardization, we retained the **first principal component (PC1)**, which captures maximum variance and serves as a unified cohesion index summarizing shared signal across all proxies.

- **Sign Correction**: Since PCA components are sign-invariant, we ensure consistent interpretation by checking the sum of loadings. If negative, we invert scores so that **higher values = worse social cohesion**.

- **Normalization**: Scores are scaled to 0-100 using MinMaxScaler for consistency with CONEVAL poverty indicators, where 100 represents maximum deprivation.


![image](https://github.com/user-attachments/assets/33e4026a-307b-47e3-b4d9-520261de2532)




