import os
import httpx
from dotenv import load_dotenv

load_dotenv()

AZURE_KEY      = os.getenv("AZURE_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://evision.cognitiveservices.azure.com/")

async def perform_ocr(content: bytes = None, image_url: str = None) -> dict:
    """
    Logique partagée pour l'OCR Azure Computer Vision v3.2.

    Paramètres :
    - content    : bytes d'une image (JPG, PNG) envoyée en upload
    - image_url  : URL publique d'une image ou d'un PDF

    Retourne un dict avec :
    - text     : texte extrait (str)
    - language : code de langue détecté (str, ex: 'fr', 'en')
    - regions  : nombre de régions de texte détectées (int)
    """
    if not AZURE_KEY:
        return {"error": "La variable d'environnement AZURE_KEY n'est pas définie."}

    if content is None and image_url is None:
        return {"error": "Vous devez fournir soit 'content' (bytes), soit 'image_url' (str)."}

    url = f"{AZURE_ENDPOINT.rstrip('/')}/vision/v3.2/ocr"

    if content:
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/octet-stream"
        }
        body = content
        is_json = False
    else:
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/json"
        }
        body = {"url": image_url}
        is_json = True

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if is_json:
                response = await client.post(url, headers=headers, json=body)
            else:
                response = await client.post(url, headers=headers, content=body)

        if response.status_code == 400:
            return {"error": "Requête invalide. Vérifiez que le fichier est une image valide (JPG, PNG, BMP) de moins de 4 Mo."}
        if response.status_code == 401:
            return {"error": "Clé Azure invalide ou expirée. Vérifiez votre AZURE_KEY."}
        if response.status_code == 415:
            return {"error": "Format de fichier non supporté par Azure. Utilisez JPG, PNG ou BMP."}
        if response.status_code != 200:
            return {"error": f"Erreur Azure ({response.status_code}) : {response.text}"}

        data = response.json()

        # Extraction du texte ligne par ligne
        lines = []
        region_count = 0
        for region in data.get("regions", []):
            region_count += 1
            for line in region.get("lines", []):
                line_text = " ".join(w["text"] for w in line.get("words", []))
                if line_text.strip():
                    lines.append(line_text)

        extracted_text = "\n".join(lines) if lines else "Aucun texte détecté."

        return {
            "text":     extracted_text,
            "language": data.get("language", "unknown"),
            "regions":  region_count
        }

    except httpx.TimeoutException:
        return {"error": "Délai d'attente dépassé. Le service Azure n'a pas répondu dans les 30 secondes."}
    except httpx.RequestError as e:
        return {"error": f"Erreur réseau : {str(e)}"}