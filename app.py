import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from dateutil import parser
import pdfplumber

st.set_page_config(page_title="Control de Vencimientos", layout="wide")
