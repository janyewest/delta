#!/usr/bin/env python3

import base64
import os
import pickle

from dotenv import load_dotenv
from openai import OpenAI
import psycopg2

# Load environment variables
load_dotenv()

# Set up OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
model_embeddings = 'text-embedding-3-small'
client = OpenAI(api_key=openai_api_key)

# Supabase database connection
db_url = os.getenv('DB_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Fetch all SOWs
cur.execute("""SELECT id, content FROM consulting.sows""")
sows = cur.fetchall()

for sow_id, content in sows:
    print(f'Generating embedding for SOW ID {sow_id}')

    response = client.embeddings.create(input=content, model=model_embeddings)
    embedding = response.data[0].embedding

    # Serialize and encode the embedding
    embedding_bytes = pickle.dumps(embedding)
    embedding_b64 = base64.b64encode(embedding_bytes).decode('utf-8')

    cur.execute(
        """
        INSERT INTO consulting.embeddings (sow_id, embedding)
        VALUES (%s, %s)
        ON CONFLICT (sow_id) DO UPDATE SET embedding = EXCLUDED.embedding
        """,
        (sow_id, embedding_b64),
    )

conn.commit()
cur.close()
conn.close()
print('Embeddings updated and stored.')
