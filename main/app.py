# bash: uvicorn app:app --reload

import base64
import os
import pickle

from dotenv import load_dotenv
from fastapi import Body, FastAPI
from fastapi.responses import FileResponse
import numpy as np
import openai
from openai import OpenAI
import psycopg2
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from supabase import Client, create_client

# FastAPI config
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
model_embeddings = 'text-embedding-3-small'
model_chat = 'gpt-4o-mini'
max_tokens = 1000
client = OpenAI(api_key=openai_api_key)
app = FastAPI()

# Supabase config
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
db_url = os.getenv('DB_URL')
db_schema = 'consulting'
db_table_clients = 'clients'
db_table_sows = 'sows'
db_table_solutions = 'solutions'
supabase: Client = create_client(supabase_url, supabase_key)


# Prompt schema for POST requests
class PromptRequest(BaseModel):
    prompt: str


@app.get('/clients')
def get_clients():
    response = supabase.schema(db_schema).table(db_table_clients).select('*').execute()
    return response.data


@app.get('/clients/{client_id}/sows')
def get_client_sows(client_id: str):
    response = supabase.schema(db_schema).table(db_table_sows).select('*').eq('client_id', client_id).execute()
    return response.data


@app.get('/sows/{sow_id}/solutions')
def get_sow_solutions(sow_id: str):
    response = supabase.schema(db_schema).table(db_table_solutions).select('*').eq('sow_id', sow_id).execute()
    return response.data


@app.get('/sows/{sow_id}/suggestions')
def generate_suggestions_from_sow(sow_id: str):
    # Fetch the SOW content
    sow_data = supabase.schema(db_schema).table(db_table_sows).select('*').eq('id', sow_id).single().execute()
    if not sow_data.data:
        raise HTTPException(status_code=404, detail='SOW not found')

    sow_title = sow_data.data['sow_title']
    sow_content = sow_data.data['content']

    # Step 1: Embed the SOW content
    embedding_response = openai.embeddings.create(input=sow_content, model=model_embeddings)
    prompt_embedding = np.array(embedding_response.data[0].embedding)

    # Step 2: Fetch embeddings from the DB
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT sow_id, embedding FROM consulting.embeddings WHERE sow_id != %s', (sow_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    similarities = []
    for other_sow_id, embedding in rows:
        db_embedding = np.array(pickle.loads(base64.b64decode(embedding)))
        similarity = np.dot(prompt_embedding, db_embedding)
        similarities.append((other_sow_id, similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_sow_ids = [sow_id for sow_id, _ in similarities[:3]]

    # Step 3: Fetch matched SOWs
    matched_contents = []
    for match_id in top_sow_ids:
        response = supabase.schema(db_schema).table(db_table_sows).select('*').eq('id', match_id).single().execute()
        if response.data:
            matched_contents.append(response.data['content'])

    # Step 4: Compose GPT prompt
    joined_sows = '\n\n'.join([f'- {c}' for c in matched_contents])
    final_prompt = f"""
    A client submitted this SOW:
    \"\"\"
    {sow_content}
    \"\"\"

    Based on these similar past SOWs:
    {joined_sows}

    Suggest 2-3 specific solutions for this client,
    along with recommended team size and predicted duration.
    """

    # Step 5: Get suggestions from GPT
    chat_response = openai.chat.completions.create(
        model=model_chat,
        messages=[
            {'role': 'system', 'content': 'You are an expert consulting strategist.'},
            {'role': 'user', 'content': final_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )

    suggestions = chat_response.choices[0].message.content.strip().split('\n')
    return {'sow_title': sow_title, 'suggestions': suggestions}


@app.post('/suggestions')
def generate_suggestions(request: PromptRequest = Body(...)):
    prompt = request.prompt

    # Step 1: Embed the new client prompt
    embedding_response = openai.embeddings.create(input=prompt, model=model_embeddings)
    prompt_embedding = np.array(embedding_response.data[0].embedding)

    # Step 2: Fetch embeddings from the DB
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT sow_id, embedding FROM consulting.embeddings')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    similarities = []
    for sow_id, embedding in rows:
        db_embedding = np.array(pickle.loads(base64.b64decode(embedding)))
        similarity = np.dot(prompt_embedding, db_embedding)
        similarities.append((sow_id, similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_sow_ids = [sow_id for sow_id, _ in similarities[:3]]

    # Step 3: Fetch matched SOWs
    matched_contents = []
    for sow_id in top_sow_ids:
        response = supabase.schema(db_schema).table(db_table_sows).select('*').eq('id', sow_id).single().execute()
        if response.data:
            matched_contents.append(response.data['content'])

    # Step 4: Compose GPT prompt
    joined_sows = '\n\n'.join([f'- {c}' for c in matched_contents])
    final_prompt = f"""
    A new client submitted this request:
    \"\"\"
    {prompt}
    \"\"\"

    Based on these similar past SOWs:
    {joined_sows}

    Suggest 2-3 specific solutions for this client,
    along with recommended team size and predicted duration.
    """

    # Step 5: Get suggestions from GPT (goes right here)
    chat_response = openai.chat.completions.create(
        model=model_chat,
        messages=[
            {'role': 'system', 'content': 'You are an expert consulting strategist.'},
            {'role': 'user', 'content': final_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )

    # Then return the results
    suggestions = chat_response.choices[0].message.content.strip().split('\n')
    return {'prompt': prompt, 'suggestions': suggestions}


@app.post('/match-sows')
def match_sows(request: PromptRequest):
    prompt = request.prompt

    # Embed the prompt
    embedding_response = openai.embeddings.create(input=prompt, model=model_embeddings)
    prompt_embedding = np.array(embedding_response.data[0].embedding)

    # Connect to the DB and fetch all stored embeddings
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT sow_id, embedding FROM consulting.embeddings')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    similarities = []
    for sow_id, embedding in rows:
        db_embedding = np.array(pickle.loads(base64.b64decode(embedding)))
        similarity = np.dot(prompt_embedding, db_embedding)
        similarities.append((sow_id, similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_matches = similarities[:3]
    match_ids = [match[0] for match in top_matches]

    matches = []
    for sow_id in match_ids:
        response = supabase.schema(db_schema).table(db_table_sows).select('*').eq('id', sow_id).single().execute()
        matches.append(response.data)

    return {'matches': matches}

@app.post('/generate-report')
def generate_report(request: PromptRequest):
    prompt = request.prompt

    embedding_response = client.embeddings.create(input=prompt, model=model_embeddings)
    prompt_embedding = np.array(embedding_response.data[0].embedding)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT sow_id, embedding FROM consulting.embeddings')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    similarities = []
    for sow_id, embedding in rows:
        db_embedding = np.array(pickle.loads(base64.b64decode(embedding)))
        similarity = np.dot(prompt_embedding, db_embedding)
        similarities.append((sow_id, similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_matches = similarities[:3]
    match_ids = [match[0] for match in top_matches]

    context_blocks = []
    for sow_id in match_ids:
        response = supabase.schema(db_schema).table(db_table_sows).select('*').eq('id', sow_id).single().execute()
        sow = response.data
        block = f"""Title: {sow['sow_title']}
Content:
{sow['content']}
---"""
        context_blocks.append(block)

    prompt_context = '\n'.join(context_blocks)
    full_prompt = f"""
You are a consulting strategist. A new client described:
"{prompt}"

Here are similar past client SOWs:

{prompt_context}

Based on this context, generate 2–3 specific solution recommendations for the new client,
along with recommended team size and predicted duration.
"""

    response = client.chat.completions.create(
        model=model_chat,
        messages=[
            {'role': 'system', 'content': 'You are an expert consulting strategist.'},
            {'role': 'user', 'content': full_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )

    return {'prompt': prompt, 'report': response.choices[0].message.content.strip()}


@app.post('/save-suggestion')
def save_suggestion(request: dict = Body(...)):
    prompt = request.get('prompt')
    suggestions = request.get('suggestions')

    # Ensure suggestions is a list of strings
    if not isinstance(suggestions, list):
        raise HTTPException(status_code=400, detail='Suggestions must be a list')

    response = supabase.schema(db_schema).table('saved_suggestions').insert({
        'prompt': prompt,
        'suggestions': suggestions  # List will be serialized as text[]
    }).execute()

    return {'status': 'saved', 'data': response.data}


@app.post('/export-suggestion-pdf')
def export_suggestion_pdf(request: dict = Body(...)):
    prompt = request.get('prompt')
    suggestions = request.get('suggestions')
    filename = 'suggestions.pdf'

    c = canvas.Canvas(filename)
    c.setFont('Helvetica', 12)
    c.drawString(50, 800, 'Client Request:')
    c.drawString(50, 785, prompt)

    y = 760
    for i, suggestion in enumerate(suggestions, start=1):
        if y < 50:
            c.showPage()
            y = 800
        c.drawString(50, y, f'{i}. {suggestion}')
        y -= 20

    c.save()

    return FileResponse(path=filename, filename=filename, media_type='application/pdf')
