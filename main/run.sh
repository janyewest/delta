#!/bin/bash
source ../../../venv/bin/activate
uvicorn app:app --reload &
streamlit run streamlit_app.py
