import os
import json
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Abilita CORS per Github Pages (in produzione potresti limitare le origini)
CORS(app)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "AGGIUNGI_IL_TUO_TOKEN_QUI")
# Endpoint per Llama-3-8B su HF Inference API (modello di esempio, si può cambiare)
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

# Carica Cassa di Conoscenza Base (MD)
try:
    with open("Master-Course-Minecraft-Network.md", "r", encoding="utf-8") as f:
        md_kb = f.read()
except FileNotFoundError:
    md_kb = "Knowledge base MD mancante."

# Carica Frontend Context (HTML/JS) per consapevolezza architetturale
try:
    with open("index.html", "r", encoding="utf-8") as f:
        html_ctx = f.read()
except FileNotFoundError:
    html_ctx = "Frontend HTML mancante."

# Unisci per il prompt (limitando ai concetti chiave per non sforare il limite di token)
KNOWLEDGE_BASE = f"STRUTTURA E CODICE FRONTEND (Estratto):\n{html_ctx[:4000]}\n\nTEORIA INGEGNERISTICA (MD):\n{md_kb}"

@app.route('/generate-course', methods=['POST'])
def generate_course():
    data = request.json
    if not data:
        return jsonify({"error": "Dati utente mancanti."}), 400
        
    age = data.get("age", 25)
    try:
        age_num = int(age)
    except ValueError:
        age_num = 25
        
    role = data.get("role", "Generico")
    prefs = data.get("prefs", "")

    # 2. Costruzione Sistema RAG e Prompt Dinamico
    is_junior = age_num < 14
    junior_instruction = ""
    if is_junior:
        junior_instruction = (
            "ATTENZIONE: L'utente è un 'Junior' (meno di 14 anni). DEVI usare analogie semplicissime "
            "(es. l'elettricità è come l'acqua nei tubi, il server è come una grande biblioteca). "
            "Mantieni le frasi brevi e il tono incoraggiante."
        )
    
    system_prompt = f"""Sei l'Intelligenza Artificiale del Trattato Universale di Ingegneria.
Il tuo compito è generare UN modulo didattico personalizzato basato sulla Knowledge Base fornita.

PROFILO UTENTE:
- Età: {age}
- Ruolo Scelto: {role}
- Obiettivo/Preferenze: {prefs}

{junior_instruction}

REGOLE DI GENERAZIONE E GUARDRAILS (TASSATIVO):
1. SE L'OBIETTIVO/PREFERENZE ({prefs}) contiene parole volgari, sessuali, illegali, violente O se la richiesta è TOTALMENTE FUORI CONTESTO (es. ricette di cucina, storia non informatica, sport, politica pertinenti ad altre materie), DEVI RIFIUTARE LA GENERAZIONE.
2. In caso di RIFIUTO (violazione guardrails), restituisci SOLTANTO questo esatto JSON, senza nient'altro:
{{ "error": "Accesso Negato: Rilevati termini non consentiti o richiesta fuori dai parametri del Trattato." }}
3. SE LA RICHIESTA È VALIDA (Ingegneria, Informatica, Gaming, Sistemi, Scienze collegate), restituisci SOLO un oggetto JSON valido. NESSUN altro testo.
4. Formato JSON richiesto per RICHIESTA VALIDA:
{{
  "id": "modulo-generato-ai",
  "title": "Titolo Accattivante del Modulo",
  "part": "Materia (es. Networking, Programmazione...)",
  "fondamenti": "3-4 paragrafi di pura trattazione scientifica e tecnica appropriata all'età e al ruolo...",
  "pratica": "Esempio pratico nel contesto di server Minecraft o architetture affini.",
  "junior": "Un'analogia semplicissima per riassumere il concetto."
}}

KNOWLEDGE_BASE:
{KNOWLEDGE_BASE[:2800]}

Se hai bisogno di riferimenti all'architettura frontend, basati sull'estratto fornito sopra per capire id, classi e logica esistente.
"""

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": system_prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False
        }
    }
    
    # 3. Chiamata API all'LLM
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        result = response.json()
        
        # Estrai e pulisci il JSON restituito (l'LLM potrebbe aggiungere markdown)
        generated_text = result[0]['generated_text']
        match = re.search(r'\{.*\}', generated_text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            course_data = json.loads(json_str)
            return jsonify(course_data), 200
        else:
            return jsonify({"error": "L'LLM non ha generato un formato valido. Fallback necessario."}), 502
            
    except Exception as e:
        print(f"Errore generazione LLM: {str(e)}")
        # In caso di backend/LLM morto, restituiamo un errore per triggerare il Fallback nel Frontend
        return jsonify({"error": "Motore IA temporaneamente offline. Connessione al Core Centrale persa."}), 503

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
