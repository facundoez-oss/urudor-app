import os
import base64
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CRITERIOS = {
    "Cobana": [
        {"texto": "C Appearance 4 Qlty/Cnd 2 Storage", "calificacion": "REGULAR"},
        {"texto": "C Appearance 2 Qlty/Cnd 1.3 Storage", "calificacion": "ACEPTABLE"},
        {"texto": "B Appearance 3 Qlty/Cnd 1.8 Storage", "calificacion": "BUENO"},
        {"texto": "C Appearance 4 Qlty/Cnd 2.8 Storage", "calificacion": "POBRE"},
        {"texto": "C Appearance 3 Qlty/Cnd 2.3 Storage", "calificacion": "POBRE"},
    ],
    "Oppy": [
        {"texto": "Decay % < 1 - Serious % < 5 - Total % < 10", "calificacion": "BUENO"},
        {"texto": "Decay % > 1 - Serious % < 5 - Total % < 10", "calificacion": "POBRE"},
        {"texto": "Decay % < 1 - Serious % > 5 - Total % < 10", "calificacion": "POBRE"},
        {"texto": "Decay % < 1 - Serious % < 5 - Total % > 10", "calificacion": "POBRE"},
    ],
}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/analizar", methods=["POST"])
def analizar():
    try:
        cliente = request.form.get("cliente")
        archivo = request.files.get("archivo")

        if not cliente or not archivo:
            return jsonify({"error": "Faltan datos"}), 400

        pdf_bytes = archivo.read()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        criterios = CRITERIOS.get(cliente, [])
        criterios_texto = "\n".join(
            [f'{i+1}. "{c["texto"]}" → {c["calificacion"]}' for i, c in enumerate(criterios)]
        )

        prompt = f"""Sos un agente especializado en análisis de informes de calidad (QC) de exportaciones de cítricos de URUD'OR S.A.

Tu tarea es leer el informe PDF del cliente {cliente} y determinar la calificación según estos criterios:

CRITERIOS PARA {cliente.upper()}:
{criterios_texto}

Respondé ÚNICAMENTE con un objeto JSON válido con esta estructura:
{{
  "contenedor": "código del contenedor",
  "buque": "nombre del buque",
  "variedad": "variedad de fruta",
  "arrival": "fecha de llegada",
  "calificacion": "BUENO|ACEPTABLE|REGULAR|POBRE",
  "scores_detectados": "valores clave encontrados en el informe",
  "razonamiento": "explicación breve en español de por qué corresponde esa calificación"
}}

No incluyas texto fuera del JSON. No uses markdown ni backticks."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{pdf_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        resultado = response.choices[0].message.content.strip()
        resultado = resultado.replace("```json", "").replace("```", "").strip()

        import json
        data = json.loads(resultado)
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)