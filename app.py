import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Control de Vencimientos", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
