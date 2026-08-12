"""Atlas GTS knowledge portal — Streamlit front end over the FastAPI layer.

Design brief (owner requirements + 2026 chat-UX research, see build plan):
minimal corporate-intranet look; chat is a PERSISTENT right-hand panel (not
button-activated); a document-library section with per-document links;
every citation offers "open the document" (PDFs land on the exact page);
guided sample questions above free text; capability transparency stated up
front. Talks to the API over HTTP only — the UI has no direct access to the
pipeline, proving the API is sufficient.

Run:  uvicorn doc_qa.api.main:app          (from the repo root)
      streamlit run src/doc_qa/ui/streamlit_app.py
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.environ.get("DOC_QA_API_URL", "http://localhost:8000")

SAMPLE_QUESTIONS = [
    "What is the impeller wear ring clearance for the AF-4520?",
    "A customer says their pump is screaming — what should I check?",
    "How many PTO days can I carry over?",
    "What was the order backlog in Q2 2026?",
]

st.set_page_config(page_title="Atlas GTS Knowledge Portal", page_icon="🔧", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.5rem; max-width: 1200px; }
      #MainMenu, footer { visibility: hidden; }
      .atlas-header { border-bottom: 3px solid #0f3557; padding-bottom: 0.6rem; }
      .atlas-header h1 { color: #0f3557; font-size: 1.6rem; margin: 0; }
      .atlas-header p { color: #5a6a7a; margin: 0.2rem 0 0 0; font-size: 0.95rem; }
      .source-card { border: 1px solid #d5dde5; border-left: 4px solid #0f3557;
                     border-radius: 4px; padding: 0.45rem 0.7rem; margin: 0.25rem 0;
                     font-size: 0.85rem; background: #f7f9fb; }
      .source-card a { color: #0f3557; font-weight: 600; text-decoration: none; }
      .provider-note { color: #8a97a5; font-size: 0.75rem; }
    </style>
    <div class="atlas-header">
      <h1>Atlas Fluid Systems — Global Technical Services</h1>
      <p>Engineering knowledge portal · pumps, valves &amp; compressor packages since 1978</p>
    </div>
    """,
    unsafe_allow_html=True,
)

main_col, chat_col = st.columns([3, 2], gap="large")

# ---------------------------------------------------------------- main column
with main_col:
    st.subheader("Technical Documentation Library")
    st.caption(
        "The pilot corpus for the AF-4500 pump series and GTS internal content. "
        "Open any document directly, or ask the assistant on the right — every "
        "answer cites its source document and page/slide."
    )
    try:
        documents = httpx.get(f"{API_URL}/documents", timeout=10).json()
    except httpx.HTTPError:
        documents = None
        st.error(f"API not reachable at {API_URL} — start it with: uvicorn doc_qa.api.main:app")

    if documents:
        by_category: dict[str, list[dict]] = {}
        for doc in documents:
            by_category.setdefault(doc["category"], []).append(doc)
        for category in sorted(by_category):
            with st.expander(category.replace("_", " ").title(), expanded=False):
                for doc in by_category[category]:
                    st.markdown(
                        f"`{doc['format']}` &nbsp; [{doc['name']}]({API_URL}{doc['href']})"
                    )

    st.divider()
    with st.expander("Add a document to the knowledge base"):
        uploaded = st.file_uploader(
            "Supported: PDF, DOCX, PPTX, CSV, TXT", key="uploader", label_visibility="collapsed"
        )
        if uploaded is not None and st.button("Index document"):
            response = httpx.post(
                f"{API_URL}/upload",
                files={"file": (uploaded.name, uploaded.getvalue())},
                timeout=120,
            )
            if response.status_code == 201:
                st.success(f"Indexed {uploaded.name}: {response.json()['chunks_indexed']} chunks")
            else:
                st.error(response.json().get("detail", "upload failed"))

# ---------------------------------------------------------------- chat column
with chat_col:
    st.subheader("Ask the documentation")
    st.caption(
        "Answers come only from the indexed Atlas documents and always cite "
        "their source. Questions the corpus can't answer are declined."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    pending = None
    chip_cols = st.columns(2)
    for i, sample in enumerate(SAMPLE_QUESTIONS):
        if chip_cols[i % 2].button(sample, key=f"chip{i}", use_container_width=True):
            pending = sample

    history = st.container(height=430)
    with history:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["text"])
                for citation in message.get("citations", []):
                    st.markdown(
                        f'<div class="source-card">📄 {citation["source"]} — '
                        f'{citation["locator"]} &nbsp;·&nbsp; '
                        f'<a href="{API_URL}{citation["href"]}" target="_blank">'
                        f"open document ↗</a></div>",
                        unsafe_allow_html=True,
                    )
                if message.get("provider"):
                    st.markdown(
                        f'<span class="provider-note">served by {message["provider"]}'
                        f'/{message["model"]}</span>',
                        unsafe_allow_html=True,
                    )

    typed = st.chat_input("e.g. What torque for AF-4520 casing bolts?")
    question = typed or pending
    if question:
        st.session_state.messages.append({"role": "user", "text": question})
        try:
            body = httpx.post(
                f"{API_URL}/query", json={"question": question}, timeout=120
            ).json()
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "text": body["text"],
                    "citations": body["citations"],
                    "provider": body["provider"],
                    "model": body["model"],
                }
            )
        except httpx.HTTPError as exc:
            st.session_state.messages.append(
                {"role": "assistant", "text": f"⚠️ API error: {exc}"}
            )
        st.rerun()
