const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".mobile-toggle");
  const nav = document.querySelector(".nav-links");
  if(toggle && nav) toggle.addEventListener("click", () => nav.classList.toggle("open"));

  const year = document.querySelector("#year");
  if(year) year.textContent = new Date().getFullYear();

  const lang = document.querySelector("#language");
  if(lang) lang.addEventListener("change", () => {
    localStorage.setItem("ipSaktiLanguage", lang.value);
  });
});

async function apiPost(path, payload){
  const res = await fetch(API_BASE + path, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload)
  });
  if(!res.ok){
    let detail = "Backend request failed.";
    try { const d = await res.json(); detail = d.detail || detail; } catch(e){}
    throw new Error(detail);
  }
  return res.json();
}

async function apiGet(path){
  const res = await fetch(API_BASE + path);
  if(!res.ok) throw new Error("Backend request failed.");
  return res.json();
}

function showResult(el, html){
  el.innerHTML = html;
  el.classList.add("show");
}
function escapeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}
function safeSourceUrl(url){
  try{
    const parsed = new URL(String(url || ""));
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "";
  }catch(e){ return ""; }
}
function sourcesHtml(sources=[]){
  if(!sources.length) return "";
  return `<div style="margin-top:22px"><h3>Evidence & Sources</h3>${
    sources.map((s,i)=>{
      const url=safeSourceUrl(s.url);
      return `<div class="source">
        <strong>[${i+1}] ${escapeHtml(s.title)}</strong>
        <div class="muted">${escapeHtml(s.authority || "")}</div>
        <div style="margin-top:5px">${escapeHtml(s.relevance || "")}</div>
        <small class="muted">Version/Date: ${escapeHtml(s.version || "Not specified")}</small>
        ${url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">🔗 Open official source</a>` : `<small class="muted">Official link not available in this record.</small>`}
      </div>`;
    }).join("")
  }</div>`;
}
