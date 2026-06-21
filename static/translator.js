// ======================================================
// Wesiya AI Translation + Theme Toggle
// Stable version:
// - Translates text and form placeholders
// - Saves selected language and theme
// - Does NOT cache translated text
// - Keeps layout stable
// ======================================================

const originalTextMap = new Map();

function getTranslatableItems() {
    const items = [];

    const textElements = Array.from(
        document.querySelectorAll("h1, h2, h3, h4, p, label, span, small, button, a")
    ).filter((element) => {
        const text = element.innerText.trim();

        if (!text) return false;
        if (text.length > 350) return false;

        // Do not translate language/theme bar
        if (element.closest(".no-translate")) return false;
        if (element.classList.contains("no-translate")) return false;

        // Allow links and buttons themselves
        if (element.matches("a, button")) return true;

        // Do not translate parent elements that contain controls
        if (element.querySelector("a, button, input, textarea, select")) return false;

        return true;
    });

    textElements.forEach((element) => {
        items.push({
            element: element,
            type: "text",
            value: element.innerText.trim()
        });
    });

    const placeholderElements = Array.from(
        document.querySelectorAll("input[placeholder], textarea[placeholder]")
    ).filter((element) => {
        const placeholder = element.getAttribute("placeholder");

        if (!placeholder) return false;
        if (!placeholder.trim()) return false;
        if (placeholder.length > 200) return false;

        // Do not translate language bar controls
        if (element.closest(".no-translate")) return false;

        // Do not translate hidden/file inputs
        if (element.type === "hidden") return false;
        if (element.type === "file") return false;

        return true;
    });

    placeholderElements.forEach((element) => {
        items.push({
            element: element,
            type: "placeholder",
            value: element.getAttribute("placeholder").trim()
        });
    });

    return items;
}

function saveOriginalTexts() {
    getTranslatableItems().forEach((item) => {
        if (!originalTextMap.has(item.element)) {
            if (item.type === "placeholder") {
                originalTextMap.set(item.element, {
                    type: "placeholder",
                    value: item.element.getAttribute("placeholder")
                });
            } else {
                originalTextMap.set(item.element, {
                    type: "text",
                    value: item.element.innerText.trim()
                });
            }
        }
    });
}

function restoreEnglish() {
    getTranslatableItems().forEach((item) => {
        const original = originalTextMap.get(item.element);

        if (!original) return;

        if (original.type === "placeholder") {
            item.element.setAttribute("placeholder", original.value);
        } else {
            item.element.innerText = original.value;
        }

        item.element.removeAttribute("dir");
        item.element.classList.remove("translated-rtl-text");
    });

    document.documentElement.dir = "ltr";
    document.body.classList.remove("rtl-page");
}

function applyTranslations(translations) {
    const items = getTranslatableItems();

    translations.forEach((translatedText, index) => {
        const item = items[index];

        if (!item || !translatedText) return;

        if (item.type === "placeholder") {
            item.element.setAttribute("placeholder", translatedText);
        } else {
            item.element.innerText = translatedText;
        }

        // Keep layout stable
        item.element.removeAttribute("dir");
        item.element.classList.remove("translated-rtl-text");
    });

    document.documentElement.dir = "ltr";
    document.body.classList.remove("rtl-page");
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

    restoreEnglish();
    saveOriginalTexts();

    const items = getTranslatableItems();

    const texts = items.map((item) => {
        const original = originalTextMap.get(item.element);
        return original ? original.value : item.value;
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

        applyTranslations(data.translations);

    } catch (error) {
        console.log("Translation error:", error);
        alert("Translation failed. Please try again.");
    } finally {
        setTranslationLoading(false);
    }
}

// ======================================================
// Theme Toggle
// ======================================================

function applySavedTheme() {
    const savedTheme = localStorage.getItem("wesiya_theme") || "light";
    const themeToggleBtn = document.getElementById("themeToggleBtn");

    if (savedTheme === "dark") {
        document.body.classList.add("dark-theme");

        if (themeToggleBtn) {
            themeToggleBtn.innerText = "Light";
        }
    } else {
        document.body.classList.remove("dark-theme");

        if (themeToggleBtn) {
            themeToggleBtn.innerText = "Dark";
        }
    }
}

function toggleTheme() {
    const isDark = document.body.classList.contains("dark-theme");

    if (isDark) {
        localStorage.setItem("wesiya_theme", "light");
    } else {
        localStorage.setItem("wesiya_theme", "dark");
    }

    applySavedTheme();
}

// ======================================================
// Language Bar
// ======================================================

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
            <option value="Somali">Somali</option>
            <option value="Oromo">Oromo</option>
            <option value="Tigrinya">Tigrinya</option>
            <option value="Urdu">Urdu</option>
            <option value="Hindi">Hindi</option>
            <option value="French">French</option>
            <option value="Spanish">Spanish</option>
            <option value="Swahili">Swahili</option>
        </select>

        <button
            type="button"
            id="themeToggleBtn"
            class="theme-toggle-btn"
            onclick="toggleTheme()"
        >
            Dark
        </button>

        <small id="translationStatus"></small>
    `;

    document.body.prepend(bar);
}

document.addEventListener("DOMContentLoaded", () => {
    addLanguageBar();
    applySavedTheme();
    saveOriginalTexts();

    const savedLanguage = localStorage.getItem("wesiya_selected_language") || "English";
    const select = document.getElementById("wesiyaLanguageSelect");

    if (select) {
        select.value = savedLanguage;
    }

    if (savedLanguage !== "English") {
        setTimeout(() => {
            translatePage(savedLanguage);
        }, 300);
    }
});