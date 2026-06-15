// ======================================================
// Wesiya AI Translation
// Uses Flask backend + Gemini API.
// Caches translations in localStorage.
// Does NOT translate buttons, links, forms, or clickable areas.
// ======================================================

const originalTextMap = new Map();

function getPageName() {
    return window.location.pathname || "/";
}

function getCacheKey(targetLanguage) {
    return `wesiya_translation_${getPageName()}_${targetLanguage}`;
}

function getTranslatableElements() {
    return Array.from(
        document.querySelectorAll("h1, h2, h3, h4, p, label, span, small")
    ).filter((element) => {
        const text = element.innerText.trim();

        if (!text) return false;
        if (text.length > 350) return false;

        // Do not translate language bar
        if (element.closest(".no-translate")) return false;
        if (element.classList.contains("no-translate")) return false;

        // Do not translate elements that contain clickable controls
        if (element.querySelector("a, button, input, textarea, select")) return false;

        return true;
    });
}

function saveOriginalTexts() {
    getTranslatableElements().forEach((element) => {
        if (!originalTextMap.has(element)) {
            originalTextMap.set(element, element.innerText.trim());
        }
    });
}

function restoreEnglish() {
    getTranslatableElements().forEach((element) => {
        if (originalTextMap.has(element)) {
            element.innerText = originalTextMap.get(element);
        }
    });

    document.documentElement.dir = "ltr";
    document.body.classList.remove("rtl-page");
}

function applyTranslations(translations, targetLanguage) {
    const elements = getTranslatableElements();

    translations.forEach((translatedText, index) => {
        if (elements[index] && translatedText) {
            elements[index].innerText = translatedText;
        }
    });

    if (targetLanguage === "Arabic") {
        document.documentElement.dir = "rtl";
        document.body.classList.add("rtl-page");
    } else {
        document.documentElement.dir = "ltr";
        document.body.classList.remove("rtl-page");
    }
}

function setTranslationLoading(isLoading) {
    const select = document.getElementById("wesiyaLanguageSelect");
    const status = document.getElementById("translationStatus");

    if (!select || !status) return;

    select.disabled = isLoading;
    status.innerText = isLoading ? "Translating..." : "";
}

async function translatePage(targetLanguage) {
    saveOriginalTexts();
    localStorage.setItem("wesiya_selected_language", targetLanguage);

    if (targetLanguage === "English") {
        restoreEnglish();
        return;
    }

    const cacheKey = getCacheKey(targetLanguage);
    const cachedTranslations = localStorage.getItem(cacheKey);

    if (cachedTranslations) {
        try {
            applyTranslations(JSON.parse(cachedTranslations), targetLanguage);
            return;
        } catch (error) {
            localStorage.removeItem(cacheKey);
        }
    }

    const elements = getTranslatableElements();

    const texts = elements.map((element) => {
        return originalTextMap.get(element) || element.innerText.trim();
    });

    if (texts.length === 0) {
        return;
    }

    try {
        setTranslationLoading(true);

        const response = await fetch("/api/translate-page", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                target_language: targetLanguage,
                texts: texts,
            }),
        });

        const data = await response.json();

        if (!data.success) {
            console.log("Translation failed:", data.message);
            alert(data.message || "Translation failed. Please try again.");
            return;
        }

        localStorage.setItem(cacheKey, JSON.stringify(data.translations));
        applyTranslations(data.translations, targetLanguage);

    } catch (error) {
        console.log("Translation error:", error);
        alert("Translation failed. Please try again.");
    } finally {
        setTranslationLoading(false);
    }
}

function addLanguageBar() {
    if (document.querySelector(".language-bar")) {
        return;
    }

    const bar = document.createElement("div");
    bar.className = "language-bar no-translate";

    bar.innerHTML = `
        <span>Language</span>
        <select id="wesiyaLanguageSelect" onchange="translatePage(this.value)">
            <option value="English">English</option>
            <option value="Amharic">Amharic</option>
            <option value="Arabic">Arabic</option>
            <option value="Chinese">Chinese</option>
            <option value="Turkish">Turkish</option>
            <option value="French">French</option>
            <option value="Spanish">Spanish</option>
        </select>
        <small id="translationStatus"></small>
    `;

    document.body.prepend(bar);
}

document.addEventListener("DOMContentLoaded", () => {
    addLanguageBar();
    saveOriginalTexts();

    const savedLanguage = localStorage.getItem("wesiya_selected_language") || "English";
    const select = document.getElementById("wesiyaLanguageSelect");

    if (select) {
        select.value = savedLanguage;
    }

    if (savedLanguage !== "English") {
        translatePage(savedLanguage);
    }
});