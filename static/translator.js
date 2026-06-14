const originalTextMap = new Map();

function getPageName() {
    return window.location.pathname || "/";
}

function getCacheKey(targetLanguage) {
    return `wesiya_translation_${getPageName()}_${targetLanguage}`;
}

function getTranslatableElements() {
    return Array.from(
        document.querySelectorAll(
            "h1, h2, h3, h4, p, label, button, a, span, small"
        )
    ).filter((element) => {
        const text = element.innerText.trim();

        if (!text) return false;
        if (element.closest(".no-translate")) return false;
        if (element.classList.contains("no-translate")) return false;
        if (text.length > 500) return false;

        return true;
    });
}

function saveOriginalTexts() {
    const elements = getTranslatableElements();

    elements.forEach((element) => {
        if (!originalTextMap.has(element)) {
            originalTextMap.set(element, element.innerText.trim());
        }
    });
}

function restoreEnglish() {
    const elements = getTranslatableElements();

    elements.forEach((element) => {
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
        if (elements[index]) {
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
    const label = document.getElementById("translationStatus");

    if (!select || !label) return;

    if (isLoading) {
        select.disabled = true;
        label.innerText = "Translating...";
    } else {
        select.disabled = false;
        label.innerText = "";
    }
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
        const translations = JSON.parse(cachedTranslations);
        applyTranslations(translations, targetLanguage);
        return;
    }

    const elements = getTranslatableElements();

    const texts = elements.map((element) => {
        return originalTextMap.get(element) || element.innerText.trim();
    });

    try {
        setTranslationLoading(true);

        const response = await fetch("/api/translate-page", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                target_language: targetLanguage,
                texts: texts
            })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message || "Translation failed.");
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