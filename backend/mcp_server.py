from mcp.server.fastmcp import FastMCP
from ocr_logic import perform_ocr
import sys
import io

# Forcer UTF-8 globalement
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ─────────────────────────────────────────────
# Initialisation du serveur MCP
# ─────────────────────────────────────────────
mcp = FastMCP(
    "DocScan-Assistant",
    instructions=(
        "Tu es un assistant spécialisé dans l'extraction et l'analyse de texte dans des documents. "
        "Utilise les outils disponibles pour lire des images ou des documents via une URL ou un fichier. "
        "Précise toujours à l'utilisateur les limites du service (taille, format, langue)."
    )
)


# ─────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────

@mcp.tool(
    name="extract_text_from_url",
    description=(
        "Extrait tout le texte visible d'un document ou d'une image accessible via une URL publique, "
        "en utilisant Azure Computer Vision OCR (v3.2).\n\n"
        "**Paramètres :**\n"
        "- url (str) : URL publique complète de l'image (doit commencer par http:// ou https://).\n\n"
        "**Formats supportés :** JPEG, PNG, BMP, PDF (une seule page).\n\n"
        "**Limites à connaître :**\n"
        "- L'URL doit être publiquement accessible (pas de lien privé ou protégé).\n"
        "- Taille maximale : 4 Mo.\n"
        "- Dimensions minimales de l'image : 50 × 50 pixels.\n"
        "- Ne fonctionne pas avec des images floutées, très sombres ou très inclinées.\n"
        "- Les PDFs multi-pages ne sont pas supportés par cette version de l'API.\n"
        "- Langues reconnues : anglais, français, allemand, espagnol, portugais, et autres langues latines. "
        "L'arabe, le chinois et le japonais peuvent avoir des résultats partiels."
    )
)
async def extract_text_from_url(url: str) -> dict:
    result = await perform_ocr(image_url=url)
    if "error" in result:
        return {"error": result["error"]}
    return {
        "text":    result.get("text", "Aucun texte détecté."),
        "regions": result.get("regions", 0)
    }


@mcp.tool(
    name="detect_language_from_url",
    description=(
        "Détecte la langue principale du texte dans un document ou une image accessible via une URL publique, "
        "en utilisant Azure Computer Vision OCR (v3.2).\n\n"
        "**Paramètres :**\n"
        "- url (str) : URL publique complète de l'image (doit commencer par http:// ou https://).\n\n"
        "**Formats supportés :** JPEG, PNG, BMP.\n\n"
        "**Limites à connaître :**\n"
        "- Azure retourne un seul code de langue (ex: 'fr', 'en', 'de'), même si le document est multilingue.\n"
        "- La détection peut être imprécise si le texte est court (moins de 5 mots).\n"
        "- Les documents avec peu de texte ou du texte manuscrit peuvent retourner 'unknown'.\n"
        "- Taille maximale : 4 Mo, dimensions minimales : 50 × 50 pixels."
    )
)
async def detect_language_from_url(url: str) -> dict:
    result = await perform_ocr(image_url=url)
    if "error" in result:
        return {"error": result["error"]}
    return {"language": result.get("language", "unknown")}


@mcp.tool(
    name="detect_language_from_content",
    description=(
        "Détecte la langue principale du texte dans une image transmise sous forme de bytes bruts (upload direct).\n\n"
        "**Paramètres :**\n"
        "- content_hex (str) : contenu de l'image encodé en hexadécimal.\n\n"
        "**Formats supportés :** JPEG, PNG, BMP.\n\n"
        "**Limites à connaître :**\n"
        "- Taille maximale : 4 Mo.\n"
        "- Dimensions minimales : 50 × 50 pixels.\n"
        "- La détection peut être imprécise pour les textes courts ou manuscrits.\n"
        "- Un seul code de langue est retourné même pour les documents multilingues.\n"
        "- L'encodage hexadécimal peut augmenter significativement la taille des données transmises."
    )
)
async def detect_language_from_content(content_hex: str) -> dict:
    try:
        content = bytes.fromhex(content_hex)
    except ValueError:
        return {"error": "Le paramètre 'content_hex' n'est pas un encodage hexadécimal valide."}

    if len(content) > 4 * 1024 * 1024:
        return {"error": "Fichier trop volumineux. La limite Azure est de 4 Mo."}

    result = await perform_ocr(content=content)
    if "error" in result:
        return {"error": result["error"]}
    return {"language": result.get("language", "unknown")}


# ─────────────────────────────────────────────
# RESOURCES
# ─────────────────────────────────────────────

@mcp.resource("config://service-info")
def get_service_info() -> str:
    """Informations générales sur le service DocScan."""
    return (
        "Service : DocScan\n"
        "Version : 1.0.0\n"
        "Moteur OCR : Azure Computer Vision v3.2\n"
        "Statut : Opérationnel\n"
        "Langues supportées : anglais, français, allemand, espagnol, portugais, et autres écritures latines.\n"
        "Formats supportés : JPEG, PNG, BMP, PDF (1 page).\n"
        "Taille maximale : 4 Mo par fichier."
    )

@mcp.resource("config://limits")
def get_limits() -> str:
    """Limites techniques du service Azure Computer Vision utilisé par DocScan."""
    return (
        "=== Limites Azure Computer Vision v3.2 ===\n\n"
        "Taille maximale du fichier : 4 Mo\n"
        "Dimensions minimales : 50 × 50 pixels\n"
        "Dimensions maximales : 4200 × 4200 pixels\n"
        "Formats acceptés : JPEG, PNG, BMP, PDF (une page)\n"
        "Quota gratuit (F0) : 20 appels/minute, 5 000 appels/mois\n"
        "Quota standard (S1) : 10 appels/seconde\n"
        "Délai d'attente : 30 secondes par requête\n\n"
        "Note : les images floues, très inclinées ou de mauvaise qualité peuvent réduire la précision de l'OCR."
    )

@mcp.resource("config://supported-languages")
def get_supported_languages() -> str:
    """Langues supportées par Azure Computer Vision OCR v3.2."""
    return (
        "=== Langues supportées par Azure OCR v3.2 ===\n\n"
        "Excellent support : anglais (en), français (fr), allemand (de), espagnol (es),\n"
        "                    italien (it), portugais (pt), néerlandais (nl).\n\n"
        "Support partiel  : arabe (ar), chinois simplifié (zh-Hans), chinois traditionnel (zh-Hant),\n"
        "                   japonais (ja), coréen (ko), russe (ru).\n\n"
        "Note : Pour les documents manuscrits, les résultats peuvent être moins précis quelle que soit la langue."
    )


# ─────────────────────────────────────────────
# PROMPTS (divisés en deux)
# ─────────────────────────────────────────────

@mcp.prompt(name="guide_extraction")
def prompt_extraction() -> str:
    """Guide d'utilisation pour l'extraction de texte."""
    return (
        "=== Guide : Extraction de texte avec DocScan ===\n\n"
        "Pour extraire le texte d'un document via son URL :\n"
        "  → Utilisez l'outil 'extract_text_from_url'\n"
        "  → Fournissez une URL publique directe vers l'image (JPG, PNG, BMP ou PDF 1 page).\n"
        "  → Exemple : https://example.com/document.jpg\n\n"
        "Le résultat contiendra :\n"
        "  - 'text'    : le texte extrait, structuré ligne par ligne.\n"
        "  - 'regions' : le nombre de zones de texte détectées dans l'image.\n\n"
        "Conseils :\n"
        "  - Privilégiez des images nettes, bien éclairées et droites.\n"
        "  - Évitez les images de moins de 50 × 50 pixels.\n"
        "  - Vérifiez que l'URL est publiquement accessible (sans authentification)."
    )


@mcp.prompt(name="guide_detection_langue")
def prompt_detection_langue() -> str:
    """Guide d'utilisation pour la détection de langue."""
    return (
        "=== Guide : Détection de langue avec DocScan ===\n\n"
        "Pour détecter la langue d'un document via son URL :\n"
        "  → Utilisez l'outil 'detect_language_from_url'\n"
        "  → Fournissez une URL publique directe vers l'image.\n\n"
        "Pour détecter la langue depuis un fichier local (bytes) :\n"
        "  → Utilisez l'outil 'detect_language_from_content'\n"
        "  → Encodez le contenu du fichier en hexadécimal avant de l'envoyer.\n\n"
        "Le résultat contiendra :\n"
        "  - 'language' : le code ISO de la langue détectée (ex: 'fr', 'en', 'de').\n\n"
        "Limites :\n"
        "  - Un seul code de langue est retourné même si le document est multilingue.\n"
        "  - La détection est moins fiable pour les textes courts (moins de 5 mots).\n"
        "  - Retourne 'unknown' si aucune langue n'est identifiée avec certitude."
    )


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()