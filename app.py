import streamlit as st
import pickle
import numpy as np
import pandas as pd
import requests
from typing import List, Tuple
import time

# --- CONFIGURATION & VISUALS ---
st.set_page_config(page_title="CineMatch", layout="wide", page_icon="🎬")

# 1. Load API Key from secrets.toml (or Streamlit Cloud Secrets)
if "tmdb_api_key" in st.secrets:
    DEFAULT_API_KEY = st.secrets["tmdb_api_key"]
else:
    DEFAULT_API_KEY = ""

# 2. Custom CSS (Theme Adaptive)
st.markdown("""
<style>
    /* We use Streamlit's internal CSS variables so the app 
       automatically adapts to Light or Dark mode.
       
       var(--secondary-background-color) = Light Grey (in Light Mode) / Dark Grey (in Dark Mode)
       var(--text-color) = Black (in Light Mode) / White (in Dark Mode)
    */

    /* Card Styling - Targeted at Column Containers */
    div[data-testid="column"] {
        background-color: var(--secondary-background-color);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid rgba(128, 128, 128, 0.2); /* Subtle border works in both modes */
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    div[data-testid="column"]:hover {
        transform: scale(1.02);
        border-color: #e50914; /* Netflix Red border on hover */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Headers - Keep them Red for branding */
    h1, h2, h3 {
        color: #e50914 !important;
        font-family: 'Arial', sans-serif;
    }

    /* Button Styling */
    div.stButton > button {
        background-color: #e50914;
        color: white;
        border: none;
        width: 100%;
        transition: background-color 0.3s;
    }
    div.stButton > button:hover {
        background-color: #b20710; /* Darker red on hover */
        color: white;
    }
    
    /* Ensure text inside cards follows the theme */
    div[data-testid="column"] p, div[data-testid="column"] span {
        color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIC (UNCHANGED) ---
@st.cache_data
def load_data():
    # 1. Load the optimized movies file
    movies = pickle.load(open('movies.pkl', 'rb'))
    
    # 2. Load the 3 parts of similarity and stitch them together
    part0 = pickle.load(open('similarity_part_0.pkl', 'rb'))
    part1 = pickle.load(open('similarity_part_1.pkl', 'rb'))
    part2 = pickle.load(open('similarity_part_2.pkl', 'rb'))
    
    similarity = np.concatenate((part0, part1, part2), axis=0)
    
    # Ensure movies is a DataFrame
    if not isinstance(movies, pd.DataFrame):
        movies = pd.DataFrame(movies)
    return movies, similarity
movies, similarity = load_data()
if 'title' not in movies.columns:
    st.error("movies.pkl must contain a 'title' column.")
    st.stop()

title_list = movies['title'].values

st.title("🎬 CineMatch")
st.markdown("##### *Discover your next favorite film*")

# --- SIDEBAR & API KEY LOGIC ---
with st.sidebar:
    st.header("Preference")
    n_recs = st.slider("Number of recommendations", 3, 12, 6)
    
    # Check if default key exists to simplify user experience
    if len(DEFAULT_API_KEY) > 10:
        use_posters = True
        tmdb_api_key = DEFAULT_API_KEY
    else:
        use_posters = st.checkbox("Show posters", value=False)
        tmdb_api_key = ""
        if use_posters:
            tmdb_api_key = st.text_input("TMDB API Key", type="password")

# --- FUNCTIONS (UNCHANGED) ---
@st.cache_data
def recommend_movie(movie_name: str, top_n: int = 5) -> List[Tuple[str, float, int]]:
    try:
        idx = int(movies[movies['title'] == movie_name].index[0])
    except Exception:
        return []

    distances = similarity[idx]
    S = list(enumerate(distances))
    S = sorted(S, key=lambda x: x[1], reverse=True)[1: top_n + 1]

    results = []
    for i, score in S:
        mrow = movies.iloc[i]
        mid = mrow['id'] if 'id' in movies.columns else -1
        results.append((mrow['title'], float(score), int(mid) if not pd.isna(mid) else -1))
    return results

@st.cache_data
def fetch_poster(tmdb_id: int, api_key: str) -> str:
    if tmdb_id < 0 or not api_key:
        return ""
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}&language=en-US"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            path = data.get('poster_path', None)
            if path:
                return "https://image.tmdb.org/t/p/w500" + path
    except Exception:
        return ""
    return ""

# --- MAIN UI ---
selected_movie = st.selectbox("Type or select a movie from the catalog:", title_list)

if st.button("Recommend Movies"):
    recs = recommend_movie(selected_movie, top_n=n_recs)
    
    if not recs:
        st.warning("No recommendations found.")
    else:
        st.subheader(f"Because you watched '{selected_movie}':")
        st.markdown("---")
        
        # Grid Layout Calculation
        cols_per_row = 3
        rows = (len(recs) + cols_per_row - 1) // cols_per_row
        
        for i in range(rows):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i * cols_per_row + j
                if idx < len(recs):
                    title, score, mid = recs[idx]
                    with cols[j]:
                        # Poster Logic
                        if use_posters and tmdb_api_key:
                            poster_url = fetch_poster(mid, tmdb_api_key)
                            if poster_url:
                                st.image(poster_url, use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/300x450?text=No+Poster", use_container_width=True)
                        
                        # Movie Details
                        st.markdown(f"**{title}**")

                        st.caption(f"Match Score: {int(score*100)}%")

