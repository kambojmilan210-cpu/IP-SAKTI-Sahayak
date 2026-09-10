const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://127.0.0.1:8000"
  : "https://ip-sakti-backend-project.onrender.com";

const HI = {
  "Home": "होम",
  "About": "हमारे बारे में",
  "Projects": "प्रोजेक्ट्स",
  "Contact": "संपर्क",
  "Ask Sahayak": "सहायक से पूछें",
  "Innovation IP Checker": "इनोवेशन IP चेकर",
  "Patent & Prior-Art Explorer": "पेटेंट और प्रायर-आर्ट एक्सप्लोरर",
  "Formulation Explorer": "फॉर्मुलेशन एक्सप्लोरर",
  "Regulatory Navigator": "रेगुलेटरी नेविगेटर",
  "Regulatory Journey": "रेगुलेटरी जर्नी",
  "Knowledge Explorer": "नॉलेज एक्सप्लोरर",
  "Evidence & Sources": "साक्ष्य और स्रोत",
  "International": "अंतरराष्ट्रीय",
  "India": "भारत",
  "English": "अंग्रेज़ी",
  "Hindi": "हिन्दी",
  "हिन्दी": "हिन्दी",
  "Submit": "सबमिट करें",
  "Check": "जाँच करें",
  "Explore": "एक्सप्लोर करें",
  "Search": "खोजें",
  "Results": "परिणाम",
  "Official Sources": "आधिकारिक स्रोत",
  "Open official source": "आधिकारिक स्रोत खोलें",
  "Version/Date:": "संस्करण/दिनांक:",
  "Not specified": "निर्दिष्ट नहीं",
  "Backend request failed.": "बैकएंड अनुरोध विफल हुआ।",
  "No result available.": "कोई परिणाम उपलब्ध नहीं है।",
  "Patent": "पेटेंट",
  "Trademark": "ट्रेडमार्क",
  "Traditional Knowledge": "पारंपरिक ज्ञान",
  "Regulatory": "रेगुलेटरी",
  "Disclaimer": "अस्वीकरण",
  "Possible IP Routes": "संभावित IP मार्ग",
  "Recommendations": "सुझाव",
  "Attention Level": "ध्यान स्तर",
  "Preliminary Indicator": "प्रारंभिक संकेतक",
  "More evidence needed": "अधिक साक्ष्य की आवश्यकता है"
};

function isHindi() {
  const lang = localStorage.getItem("ipSaktiLanguage") || "English";
  return lang === "Hindi" || lang === "हिन्दी";
}

function currentLanguage() {
  return localStorage.getItem("ipSaktiLanguage") || "English";
}

function translateValue(value) {
  if (!isHindi()) return value;
  return HI[value] || value;
}

function applyLanguage() {
  if (!isHindi()) return;

  document.querySelectorAll("body *").forEach(el => {
    if (el.children.length === 0 && el.textContent.trim()) {
      const original = el.textContent.trim();
      if (HI[original]) {
        el.textContent = HI[original];
      }
    }
  });

  document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach(el => {
    const original = el.getAttribute("placeholder");
    if (HI[original]) {
      el.setAttribute("placeholder", HI[original]);
    }
  });

  document.querySelectorAll("button").forEach(btn => {
    const original = btn.textContent.trim();
    if (HI[original]) {
      btn.textContent = HI[original];
    }
  });
}

function translateDynamicContent() {
  if (!isHindi()) return;

  document.querySelectorAll(".source h3").forEach(el => {
    if (HI[el.textContent.trim()]) {
      el.textContent = HI[el.textContent.trim()];
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".mobile-toggle");
  const nav = document.querySelector(".nav-links");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      nav.classList.toggle("open");
    });
  }

  const year = document.querySelector("#year");

  if (year) {
    year.textContent = new Date().getFullYear();
  }

  const lang = document.querySelector("#language");

  if (lang) {
    const savedLanguage = currentLanguage();

    if ([...lang.options].some(o => o.value === savedLanguage || o.text === savedLanguage)) {
      lang.value = savedLanguage;
    }

    lang.addEventListener("change", () => {
      localStorage.setItem("ipSaktiLanguage", lang.value);
      window.location.reload();
    });
  }

  applyLanguage();

  const observer = new MutationObserver(() => {
    translateDynamicContent();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
});

async function apiPost(path, payload) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    let detail = "Backend request failed.";

    try {
      const d = await res.json();
      detail = d.detail || detail;
    } catch (e) {}

    throw new Error(detail);
  }

  return res.json();
}

async function apiGet(path) {
  const res = await fetch(API_BASE + path);

  if (!res.ok) {
    throw new Error(
      isHindi()
        ? "बैकएंड अनुरोध विफल हुआ।"
        : "Backend request failed."
    );
  }

  return res.json();
}

function showResult(el, html) {
  el.innerHTML = html;
  el.classList.add("show");
  translateDynamicContent();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[c]));
}

function safeSourceUrl(url) {
  try {
    const parsed = new URL(String(url || ""));

    return ["http:", "https:"].includes(parsed.protocol)
      ? parsed.href
      : "";
  } catch (e) {
    return "";
  }
}

function sourcesHtml(sources = []) {
  if (!sources.length) return "";

  const title = isHindi()
    ? "साक्ष्य और स्रोत"
    : "Evidence & Sources";

  const openText = isHindi()
    ? "🔗 आधिकारिक स्रोत खोलें"
    : "🔗 Open official source";

  const versionText = isHindi()
    ? "संस्करण/दिनांक:"
    : "Version/Date:";

  const notSpecified = isHindi()
    ? "निर्दिष्ट नहीं"
    : "Not specified";

  const unavailable = isHindi()
    ? "इस रिकॉर्ड में आधिकारिक लिंक उपलब्ध नहीं है।"
    : "Official link not available in this record.";

  return `
    <div style="margin-top:22px">
      <h3>${title}</h3>

      ${
        sources.map((s, i) => {
          const url = safeSourceUrl(s.url);

          return `
            <div class="source">
              <strong>[${i + 1}] ${escapeHtml(s.title)}</strong>

              <div class="muted">
                ${escapeHtml(s.authority || "")}
              </div>

              <div style="margin-top:5px">
                ${escapeHtml(s.relevance || "")}
              </div>

              <small class="muted">
                ${versionText}
                ${escapeHtml(s.version || notSpecified)}
              </small>

              ${
                url
                  ? `
                    <a
                      class="source-link"
                      href="${escapeHtml(url)}"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      ${openText}
                    </a>
                  `
                  : `
                    <small class="muted">
                      ${unavailable}
                    </small>
                  `
              }
            </div>
          `;
        }).join("")
      }
    </div>
  `;
}
