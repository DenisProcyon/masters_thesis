## 🧱 Repository Structure

```bash
mexico-social-data-pipeline/
├── src/
│   ├── telegram/              # Telegram post/comment models and logic
│   ├── youtube/               # YouTube API wrapper
│   ├── news_data/             # News parsing and preprocessing
│   ├── gt_data/               # Google Trends scraping
│   ├── mongo_wrapper/         # MongoDB integration layer
│   ├── logger/                # Logging abstraction (file + console)
├── tg_scraper.py              # Telegram collection logic
├── yt_client.py               # YouTube video/comment retriever
├── main_pipeline.py           # Orchestration of all sources
├── notebooks/                 # Data exploration and correlation notebooks
├── data/                      # Example exports and raw samples
├── requirements.txt
├── .env.example               # Template for API keys and DB access
└── README.md
```

---

## 🌐 Chapter I — Social Media Data Collection

Our first and most direct source of public opinion is **social media**. We focus on two key platforms:

### 📲 1. Telegram

Telegram is widely used in Latin America for public and semi-anonymous discussions on politics, economy, and society.
It offers unfiltered insights from both citizens and grassroots media outlets.

We use the [`telethon`](https://github.com/LonamiWebs/Telethon) library to:

* Scrape historical messages from public channels
* Filter posts based on target keywords (e.g. *"crisis"*, *"violencia"*)
* Optionally collect user comments per post

```python
from tg_scraper import get_posts
from telethon.sync import TelegramClient

client = TelegramClient("anon", api_id, api_hash)

posts = await get_posts(
    client=client,
    channel="@NoticiasMexico",
    start="01/03/2024",
    end="01/04/2024",
    target_strings=["crisis", "violencia", "alimentos"]
)
```

Each message is converted into a structured `Post` object, which is later stored in MongoDB.

---

### 📺 2. YouTube

YouTube provides semi-structured video content, news reports, and public commentary.
We retrieve both **video metadata** and **comment threads** via the YouTube Data API v3.

#### Videos can be fetched by:

* Public **channel handle** (e.g. `@MilenoNoticias`)
* **Keyword queries** (e.g. `"protestas en Chiapas"`)

```python
from youtube.yt_client import YouTubeClient

yt_client = YouTubeClient(api_key=YOUTUBE_API_KEY)

# Fetch videos
videos = yt_client.get_videos_by_handle("@NoticiasMexico")

# Fetch comments for a specific video
comments = yt_client.get_comments_by_video_id(video_id="abc123xyz")
```


## 🗄️ Chapter II — MongoDB and Why It Matters

### 🧾 Why MongoDB?

| Feature                  | Why it matters for us                                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| ✅ **Human-readable**     | Documents are plain JSON, easy to inspect, version, or export                                                        |
| 🔄 **Flexible schema**   | Different platforms (Telegram, YouTube, News) have different structures. No need to normalize prematurely             |
| 🚀 **Lightweight setup** | Can be installed locally in 1 min (`brew`, `apt`, or Docker) - ideal for reproducible academic setups                 |
| ♻️ **Reusable**          | Anyone can swap out our data and reuse the same logic with their own region, topic, or keywords                       |
| 🔍 **Queryable**         | Supports slicing by region, timestamp, keyword, etc. in one line, great for building datasets per state or timeframe |

---

### 🧪 Example: Telegram Post Document in MongoDB

```json
{
  "_id": 18932,
  "text": "La situación alimentaria en Oaxaca es crítica...",
  "author": 546118323,
  "posting_ts": 1710000123.0,
  "comments": [
    {
      "id": 98182,
      "text": "Es verdad, no hay nada en los supermercados",
      "author": 129993,
      "posting_ts": 1710001523.0,
      "post_id": 18932
    }
  ]
}
```

No need for migrations, schema files, or foreign key constraints.
Each post and its comments live in the same document — making inspection and analysis easier for non-technical researchers too.

---

### 🧪 Example: YouTube Video Document

```json
{
  "_id": "zXY2abc390",
  "snippet": {
    "title": "Protestas en Chiapas",
    "publishedAt": "2024-03-12T10:00:00Z",
    "description": "Miles de personas salen a la calle...",
    "channelTitle": "Noticias México"
  },
  "statistics": {
    "viewCount": "10492",
    "likeCount": "301"
  }
}
```

Again — rich, nested structure, flexible fields, no schema rigidity.
It’s also ready for symbolic transformation or filtering (e.g. only videos from Oaxaca between two dates).

---

## 📰 Chapter III — News & Public Discourse

While social media gives us informal, bottom-up signals, **news media** reflects structured, editorially curated coverage. It’s especially important for tracking:

* Government announcements
* Regional disasters
* Food or violence spikes
* Political events

We collect news data from two sources:
➡️ **Google News** (via `gnews`)
➡️ **MediaCloud** (public news database focused on media ecosystems)

---

### 🧭 Strategy: What We Collect

* Articles mentioning each **Mexican state** by name
* From **2020**, covering the pre- and post-pandemic period
* Stored per state into MongoDB for exploration and filtering

---

## 🧪 A. Google News via `gnews`

We split the full year into **10-day chunks**, then query Google News for each state name.

```python
from newsapi_parser import process_state
from datetime import datetime

process_state(
    state="Oaxaca",
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2020, 12, 1),
    max_workers=20
)
```

Each article is:

* Proxied via `proxies.txt` to avoid throttling
* Assigned a unique ID (hashed URL)
* Stored under collection `gnews_{state}` in Mongo

✅ Articles are downloaded in parallel using threads for speed.
✅ Stored in JSON format, ready for querying or symbolic transformation.

---

## 🧪 B. MediaCloud API

To supplement GNews with **independent or niche outlets**, we also use [`mediacloud`](https://mediacloud.org/), an academic-grade API.

```python
from mediacloud.api import SearchApi
from datetime import date
from mediacloud_collector import get_data

mc = SearchApi(MEDIACLOUD_API_KEY)

get_data(
    mediacloud_engine=mc,
    keyword="Veracruz",
    start_date=date(2020, 1, 1),
    end_date=date(2020, 12, 1)
)
```

Key features:

* Supports **pagination** across large result sets
* Pulls from **dozens of Mexican collections** (print, digital, and local news)
* Saves to Mongo under `mediacloud_{state}`
---

### 🧾 Example document

```json
{
  "_id": 839221231,
  "title": "Violencia aumenta en Veracruz según informe local",
  "url": "https://noticiasveracruz.mx/article/violencia-2020",
  "publish_date": "2020-07-15",
  "source_name": "Noticias Veracruz",
  "summary": "El artículo informa sobre el aumento de violencia en zonas rurales de Veracruz...",
  "state": "Veracruz"
}
```

This document is **rich in metadata** but still lacks the full body text, which is critical for deeper semantic analysis.

---


## 🧾 Chapter IV — Extracting Full Article Content

By default, the articles we fetch from GNews and MediaCloud **do not contain full content** — only titles, snippets, and links.
Moreover, Google News often provides **redirect URLs**, not direct links to the article.

To solve this, we implement a **three-stage content pipeline**:

---

### 🧩 Step 1: Decode Google News Redirect URLs

Google often returns links like:

```
https://news.google.com/articles/CBMiMWh0dHBzOi8vd3d3LmVsdW5pdmVyc2FsLmNvbS5teC9ub3RpY2lhL29he...
```

These are just wrappers. We resolve the actual URLs using a custom utility `gnewsdecoder` + rotating proxies:

```python
decoded = gnewsdecoder("https://news.google.com/articles/...", proxy="http://IP:PORT")
```

We do this in parallel:

```python
from decode_urls import update_articles_multithread

articles = mongo_client.get_collection_entries("gnews_Oaxaca")
update_articles_multithread("gnews_Oaxaca", articles, max_workers=30)
```

This creates a new field in MongoDB:

```json
{
  "_id": "...",
  "url": "https://news.google.com/...",
  "decoded_url": "https://eluniversal.com.mx/article-about-violence"
}
```

---

Отлично! Вот как мы можем расширить и улучшить раздел `🔍 Step 2`, чтобы объяснить, **что такое `trafilatura`**, зачем мы её выбрали, и какие альтернативы могли бы быть.

---

### 🔍 Step 2: Scrape Clean Article Text with `trafilatura`

Once we decode the URLs and reach the actual news websites, we need a tool that can extract only the **core article content** — without headers, footers, ads, navigation bars, or comments.

For this, we use [`trafilatura`](https://github.com/adbar/trafilatura), a modern and **high-precision web scraping library** built specifically for news and academic web content.

---

### 🧠 What is `trafilatura`?

`trafilatura` is a Python library for **article content extraction**. Unlike generic HTML parsers, it uses a hybrid rule-based and NLP approach to identify the actual readable part of a page — the article body — and discard all the boilerplate.

#### Key Features:

* 🚀 No JavaScript rendering required (fast and lightweight)
* 🧼 Built-in cleaning of noise, ads, and unrelated elements
* 🌍 Language-aware (handles Spanish and multilingual text)
* ✅ Suitable for academic-scale scraping

---

### 🧪 How we use it

```python
from trafilatura import fetch_url, extract

html = fetch_url("https://eluniversal.com.mx/article-about-veracruz")

text = extract(
    html
    output_format="txt"
)
```

We wrap this logic into a multithreaded batch runner to extract dozens of articles per state:

```python
from fetch_article_texts import get_articles_content_threaded

get_articles_content_threaded(
    articles=articles,
    mongo_client=mongo_client,
    collection="gnews_Oaxaca",
    max_workers=30
)
```

---

### 📦 Why we chose `trafilatura`

| Feature                  | Reason                                            |
| -------------------------- | ---------------------------------------------------- |
| No browser needed          | Much faster than headless Chrome (e.g. Selenium), especially in our case, for hundreds of thousands articles     |
| Language-aware             | Handles Spanish text structure well                  |
| Customizable output        | Choose between plain text or HTML with metadata      |
| Designed for news articles | Works out of the box for press websites, blogs, etc. |

We evaluated other tools (like `newspaper3k`, `readability-lxml`, and `goose3`), but `trafilatura` provided the **best recall and consistency**, especially for non-English content.

---

### Final Mongo Document Structure

```json
{
  "_id": "...",
  "title": "Crisis alimentaria en Oaxaca",
  "url": "https://news.google.com/...",
  "decoded_url": "https://eluniversal.com.mx/real-article-url",
  "content": "The article reports that access to basic food supplies in Oaxaca..."
}
```

This allows us to:

* Perform **topic classification** using full text
* Compute **sentiment scores** or **symbolic encodings**
* Link coverage to **state-level metrics** over time