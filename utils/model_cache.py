"""Cached model loading for performance optimization"""
import streamlit as st
import spacy
from sentence_transformers import SentenceTransformer

@st.cache_resource
def load_spacy_model():
    """Load spacy model once and cache it"""
    return spacy.load("en_core_web_lg")

@st.cache_resource
def load_sentence_transformer():
    """Load sentence transformer model once and cache it"""
    return SentenceTransformer('stsb-roberta-large')
