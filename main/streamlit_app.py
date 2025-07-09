#!/usr/bin/env python3
# streamlit run streamlit_app.py

import streamlit as st
import requests

# Example prompt: We need to integrate multiple hospital data sources into a unified analytics platform on the cloud.


API_URL = 'http://127.0.0.1:8000'

st.title('🧠 SOW Solution Recommender')

if 'suggestions' not in st.session_state:
    st.session_state['suggestions'] = None
    st.session_state['prompt'] = ''
    st.session_state['match'] = None

prompt = st.text_area('Describe your new client need:', height=150)

if st.button('Find Recommendations'):
    with st.spinner('Finding matching SOWs and generating suggestions...'):
        match_resp = requests.post(f'{API_URL}/match-sows', json={'prompt': prompt})
        if match_resp.status_code == 200:
            matches = match_resp.json()['matches']
            best_match = matches[0]
            sow_id = best_match['id']

            suggest_resp = requests.get(f'{API_URL}/sows/{sow_id}/suggestions')
            if suggest_resp.status_code == 200:
                st.session_state['prompt'] = prompt
                st.session_state['suggestions'] = suggest_resp.json()['suggestions']
                st.session_state['match'] = best_match
            else:
                st.error('Error getting suggestions')
        else:
            st.error('Error matching SOWs')

if st.session_state['suggestions']:
    match = st.session_state['match']
    st.subheader('🧾 Closest Matching SOW')
    st.markdown(f"**Title:** {match['sow_title']}")
    st.markdown(f"**Content:** {match['content']}")

    st.subheader('💡 Recommended Solutions')
    for s in st.session_state['suggestions']:
        st.write(s)

    if st.button('💾 Save to Supabase'):
        save_resp = requests.post(f'{API_URL}/save-suggestion', json={
            'prompt': st.session_state['prompt'],
            'suggestions': st.session_state['suggestions']
        })
        if save_resp.status_code == 200:
            st.success('Suggestions saved successfully!')
        else:
            st.error('Failed to save suggestions.')

    export_content = f"Prompt:\n{st.session_state['prompt']}\n\nSuggestions:\n" + '\n'.join(st.session_state['suggestions'])
    st.download_button(
        label='📄 Export as TXT',
        data=export_content,
        file_name='sow_suggestions.txt',
        mime='text/plain'
    )
