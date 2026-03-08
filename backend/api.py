from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ocr_logic import perform_ocr
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="DocScan API",
    description="API d'extraction de texte via Azure Computer Vision.",
    version="1.0.0"
)

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "DocScan API", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Vérifie que le service est opérationnel et que la clé Azure est configurée."""
    key_set = bool(os.getenv("AZURE_KEY"))
    return {
        "status": "ok" if key_set else "misconfigured",
        "azure_key_configured": key_set
    }

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """
    Extrait le texte d'une image (JPG, PNG) ou d'un PDF via Azure Computer Vision.
    Retourne le texte extrait et la langue détectée.
    """
    if not os.getenv("AZURE_KEY"):
        raise HTTPException(status_code=500, detail="La clé Azure n'est pas configurée (AZURE_KEY manquante).")

    # Validation du type de fichier
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Type de fichier non supporté : {file.content_type}. Formats acceptés : JPG, PNG, PDF.")

    content = await file.read()

    # Limite de taille : Azure accepte max 4 MB
    if len(content) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux. La limite Azure est de 4 Mo.")

    result = await perform_ocr(content=content)

    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Erreur Azure : {result['error']}")

    return result

@app.post("/ocr-url")
async def ocr_from_url(payload: dict):
    """
    Extrait le texte d'un document accessible via une URL publique.
    L'URL doit pointer vers une image JPG, PNG ou BMP publiquement accessible.
    """
    if not os.getenv("AZURE_KEY"):
        raise HTTPException(status_code=500, detail="La clé Azure n'est pas configurée (AZURE_KEY manquante).")

    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Le champ 'url' est requis.")
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="L'URL doit commencer par http:// ou https://.")

    result = await perform_ocr(image_url=url)

    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Erreur Azure : {result['error']}")

    return result