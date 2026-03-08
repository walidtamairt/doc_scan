// ===== ÉLÉMENTS DU DOM =====
const fileInput       = document.getElementById("fileInput");
const fileName        = document.getElementById("fileName");
const analyzeBtn      = document.getElementById("analyzeBtn");
const resultText      = document.getElementById("resultText");
const copyBtn         = document.getElementById("copyBtn");
const downloadBtn     = document.getElementById("downloadBtn");
const editBtn         = document.getElementById("editBtn");
const languageDisplay = document.getElementById("languageDisplay");
const charCount       = document.getElementById("charCount");
const resultSection   = document.getElementById("resultSection");
const errorBox        = document.getElementById("errorBox");
const dropZone        = document.getElementById("dropZone");
const urlInput        = document.getElementById("urlInput");

document.getElementById("year").textContent = new Date().getFullYear();

let selectedFile = null;
let activeTab    = "upload"; // "upload" ou "url"

// ===== MAPPING DES LANGUES =====
const langues = {
  en: "🇬🇧 Anglais",
  fr: "🇫🇷 Français",
  ar: "🇸🇦 Arabe",
  es: "🇪🇸 Espagnol",
  de: "🇩🇪 Allemand",
  it: "🇮🇹 Italien",
  pt: "🇵🇹 Portugais",
  zh: "🇨🇳 Chinois",
  ja: "🇯🇵 Japonais",
};

// ===== GESTION DES ONGLETS =====
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    // Mettre à jour l'onglet actif
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    activeTab = tab.dataset.tab;

    // Afficher le bon panneau
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
    document.getElementById(`panel-${activeTab}`).classList.remove("hidden");

    // Réinitialiser l'état
    hideError();
    resultSection.classList.add("hidden");
    analyzeBtn.disabled = activeTab === "upload" ? !selectedFile : !urlInput.value.trim();
  });
});

// Activer le bouton quand l'URL est saisie
urlInput.addEventListener("input", () => {
  analyzeBtn.disabled = !urlInput.value.trim();
  hideError();
});

// ===== SÉLECTION DE FICHIER =====
fileInput.addEventListener("change", () => {
  setFile(fileInput.files[0]);
});

function setFile(file) {
  if (!file) return;
  selectedFile = file;
  fileName.textContent = `📎 ${file.name}`;
  analyzeBtn.disabled = false;
  hideError();
  resultSection.classList.add("hidden");
}

// ===== DRAG & DROP =====
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

// ===== ANALYSE =====
analyzeBtn.addEventListener("click", async () => {
  hideError();
  setLoading(true);

  try {
    let data;

    if (activeTab === "upload") {
      // — Analyse par fichier —
      if (!selectedFile) {
        showError("Veuillez sélectionner un fichier.");
        return;
      }
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("http://127.0.0.1:8000/ocr", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Erreur serveur : ${response.status}`);
      }
      data = await response.json();

    } else {
      // — Analyse par URL —
      const url = urlInput.value.trim();
      if (!url) {
        showError("Veuillez entrer une URL.");
        return;
      }
      if (!url.startsWith("http")) {
        showError("L'URL doit commencer par http:// ou https://");
        return;
      }

      const response = await fetch("http://127.0.0.1:8000/ocr-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Erreur serveur : ${response.status}`);
      }
      data = await response.json();
    }

    if (data.error) {
      showError("Erreur Azure : " + data.error);
      return;
    }

    afficherResultat(data);

  } catch (error) {
    console.error(error);
    showError(error.message || "Impossible de joindre le serveur. Vérifiez que le backend est lancé.");
  } finally {
    setLoading(false);
  }
});

// ===== AFFICHAGE RÉSULTAT =====
function afficherResultat(data) {
  const langueLisible = langues[data.language] || ("🌐 " + data.language);
  languageDisplay.textContent = langueLisible;

  const texte = data.text || "Aucun texte détecté.";
  resultText.value = texte;
  resultText.readOnly = true;
  editBtn.textContent = "✏️ Éditer";

  charCount.textContent = `${texte.length} caractères`;
  resultSection.classList.remove("hidden");
}

// ===== ÉDITION =====
editBtn.addEventListener("click", () => {
  if (resultText.readOnly) {
    resultText.readOnly = false;
    editBtn.textContent = "🔒 Verrouiller";
    resultText.focus();
  } else {
    resultText.readOnly = true;
    editBtn.textContent = "✏️ Éditer";
    charCount.textContent = `${resultText.value.length} caractères`;
  }
});

resultText.addEventListener("input", () => {
  charCount.textContent = `${resultText.value.length} caractères`;
});

// ===== COPIER =====
copyBtn.addEventListener("click", async () => {
  if (!resultText.value) return;
  try {
    await navigator.clipboard.writeText(resultText.value);
    copyBtn.textContent = "✅ Copié !";
    setTimeout(() => (copyBtn.textContent = "📋 Copier"), 2000);
  } catch {
    resultText.select();
    document.execCommand("copy");
    copyBtn.textContent = "✅ Copié !";
    setTimeout(() => (copyBtn.textContent = "📋 Copier"), 2000);
  }
});

// ===== TÉLÉCHARGER =====
downloadBtn.addEventListener("click", () => {
  if (!resultText.value) return;
  const blob = new Blob([resultText.value], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  const baseName = selectedFile
    ? selectedFile.name.replace(/\.[^.]+$/, "")
    : "document";
  link.download = `${baseName}_texte.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
});

// ===== UTILITAIRES =====
function setLoading(loading) {
  analyzeBtn.disabled = loading;
  analyzeBtn.querySelector(".btn-text").hidden = loading;
  analyzeBtn.querySelector(".btn-loader").hidden = !loading;
}

function showError(msg) {
  errorBox.textContent = "⚠️ " + msg;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}