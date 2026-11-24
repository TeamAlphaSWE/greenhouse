"""Conversational interface for the Greenhouse Assistant's Ask capability (issue #135)."""
import requests
import streamlit as st

from assistant_api import ask
from theme import page_header

st.set_page_config(
    page_title="Ask | Greenhouse",
    page_icon="🌱",
    layout="wide"
)

page_header("Ask the Greenhouse", "Ask Sprout about your zones, sensors, or alerts.")

st.session_state.setdefault("assistant_history", [])
history = st.session_state["assistant_history"]

if not history:
    with st.chat_message("assistant", avatar="🌱"):
        st.markdown("Hey, I'm Sprout. Ask me anything about your greenhouse.")

for turn in history:
    avatar = "🌱" if turn["role"] == "assistant" else None
    with st.chat_message(turn["role"], avatar=avatar):
        st.markdown(turn["content"])

prompt = st.chat_input("Ask the greenhouse...")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌱"):
        with st.spinner("Thinking..."):
            try:
                answer = ask(prompt, history)
            except requests.HTTPError as error:
                status = error.response.status_code
                if status == 401:
                    st.error("You're not signed in or your session has ended. Please sign in again.")
                else:
                    st.error(error.response.json().get("error", "Couldn't reach the assistant. Please try again."))
            except requests.RequestException:
                st.error("Couldn't reach the server. Please try again.")
            else:
                if answer:
                    st.markdown(answer)
                    history.append({"role": "user", "content": prompt})
                    history.append({"role": "assistant", "content": answer})
                else:
                    st.info("Sprout didn't have anything to add. Try asking a different way.")
