#!/bin/bash
uvicorn app:app --reload &
streamlit run streamlit_app.py
