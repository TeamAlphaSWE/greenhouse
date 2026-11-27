
import streamlit as st
import requests
from theme import page_header

def change_pass():

    page_header("Change Password", "Update your account password.")

    st.set_page_config(
        page_title="Privacy | Greenhouse",
        page_icon="🌱",
        layout="wide"
    )

    st.markdown("""
    <style>
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background: #f6f7ef !important;
    }
    [data-testid="stMain"] * {
        color: #18372A !important;
    }
    [data-testid="stMain"] .gh-page-hero h1 {
        color: #fffdf4 !important;
    }
    [data-testid="stMain"] .gh-page-hero .gh-page-sub {
        color: #d4af37 !important;
    }
    [data-testid="stMain"] button {
        background: #123d2d !important;
        border-color: #123d2d !important;
    }
    [data-testid="stMain"] button,
    [data-testid="stMain"] button * {
        color: #fffdf4 !important;
        -webkit-text-fill-color: #fffdf4 !important;
    }
    .st-key-password_fields [data-baseweb="input"] > div {
        background: #FFFDF4 !important;
        border-color: #FFFDF4 !important;
    }
    .st-key-password_fields input[type="password"] {
        background: transparent !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    .st-key-password_fields [data-baseweb="input"] button {
        background: #FFFDF4 !important;
        border-color: #FFFDF4 !important;
        color: #000000 !important;
    }
    .st-key-password_fields [data-baseweb="input"] button * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    .st-key-password_fields {
        background: #DCE4D6;
        border: 1px solid #DCE4D6;
        border-radius: 12px;
        padding: 1.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("←", help="Back to Settings"):
            st.switch_page("views/settings.py")

    with st.container(key="password_fields"):
        current_password = st.text_input(
            "Current Password",
            type="password"
        )

        new_password = st.text_input(
            "New Password",
            type="password"
        )

        confirm_password = st.text_input(
            "Confirm New Password",
            type="password"
        )

    if st.button("Update Password"):

        if not current_password or not new_password or not confirm_password:
            st.error("Please fill in all fields.")

        elif new_password != confirm_password:
            st.error("New passwords do not match.")

        elif new_password == current_password:
            st.error("Your new password must be different from your current password.")

        else:
            token = st.session_state["token"]
            if not token:
                st.error("Your sesson expired please login again")
                return 
            
            headers = {
                "Authorization": f"Bearer {token}"
            }

            try:
                response = requests.post(
                    "https://greenhouse.kentcs.org/api/v1/change-password",
                    json={
                        "old_password": current_password,
                        "new_password": new_password
                    },
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    st.success("Your password has been changed successfully!")

                elif response.status_code == 400:
                    st.error(response.json().get("error", "Password change failed."))

                elif response.status_code == 401:
                    st.error("Your session has expired. Please log in again.")

                else:
                    st.error("Something went wrong. Please try again.")

            except requests.exceptions.RequestException:
                st.error("Could not connect to the server. Please try again.")


change_pass()
