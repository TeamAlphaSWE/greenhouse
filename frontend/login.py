from pathlib import Path
import base64
import streamlit as st

st.set_page_config(
    page_title="Greenhouse Dashboard Login",
    layout="wide"
)

ASSETS = Path(__file__).resolve().parent / "assets"

logo_path = ASSETS / "Greenhouse_logo.png"

def to_base64(file_name):
    return base64.b64encode(
        (ASSETS / file_name).read_bytes()
    ).decode()


bg = to_base64("greenhouse.jpg")
logo = to_base64("Greenhouse_logo.png")


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


st.markdown(
    f"""
    <style>

    header, footer, #MainMenu,
    [data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stHeader"] {{
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
    }}

    [data-testid="stDecoration"] {{
        display: none !important;
    }}

    [data-testid="stStatusWidget"] {{
        display: none !important;
    }}

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {{
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }}

    .stApp,
    .stMain {{
        margin: 0 !important;
        padding: 0 !important;
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }}

    .block-container {{
        max-width: 100% !important;
        height: 100vh !important;
        max-height: 100vh !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }}

    /* Fill the whole screen, covering the top bar */
    [data-testid="stHorizontalBlock"] {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 999999 !important;
    }}

    /* Make the photo cover the entire left column */
    [data-testid="stColumn"]:first-child,
    [data-testid="stColumn"]:first-child > div {{
        height: 100vh !important;
        background-size: cover !important;
        background-position: center !important;
    }}

    [data-testid="stColumn"] {{
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }}

    /* LEFT SIDE */
    [data-testid="stColumn"]:first-child {{
        background-image:
            linear-gradient(
                90deg,
                rgba(4,38,22,.9),
                rgba(7,54,31,.45)
            ),
            url("data:image/jpeg;base64,{bg}");

        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-color: #042616;
    }}

    .left-title {{
        padding: 38vh 0 0 6vw;
        color: white;
        font-family: Georgia, serif;
        font-size: 72px;
        font-weight: 700;
        line-height: 1;
    }}

    .left-title span {{
        color: #d4f3a8;
    }}

    # .gold-line {{
    #     width: 95px;
    #     height: 4px;
    #     background: #f0b728;
    #     margin: 28px 0 0 6vw;
    # }}

    /* RIGHT SIDE */

    [data-testid="stColumn"]:nth-child(2) > div {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: #fffefa;
        padding: 0 5vw;
        height: 100vh;
    }}

    .login-header {{
        text-align: center;
        padding-top: 8vh;
    }}

    .login-header img {{
        width: 210px;
    }}

    .university {{
        letter-spacing: 5px;
        color: #163923;
        margin-top: 8px;
        font-size: 14px;
    }}

    .welcome {{
        font-family: Georgia, serif;
        color: #182945;
        font-size: 42px;
        font-weight: 700;
        margin-top: 28px;
    }}

    .subtitle {{
        color: #788087;
        margin: 8px 0 28px;
    }}

    [data-testid="stTextInputRootElement"] {{
        height: 56px !important;
        border-radius: 10px !important;
    }}

    [data-testid="stTextInput"] input {{
        padding: 0 16px !important;
        font-size: 16px;
    }}

    .stButton,
    [data-testid="stButton"] {{
        width: 50% !important;
        display: flex !important;
        justify-content: center !important;
    }}

    .stButton > button {{
        width: 320px !important;
        height: 56px !important;
        margin: 0 auto !important;

        background: #2a5a3a !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
    }}

    .stButton > button:hover {{
        background: #1f472d;
        color: white;
    }}

    @media (max-width: 900px) {{
        [data-testid="stColumn"]:first-child {{
            display: none;
        }}
    }}

    </style>
    """,
    unsafe_allow_html=True
)


left, right = st.columns([1.35, 1])


with left:
    st.markdown(
        """
        <div class="left-title">
            Greenhouse<br>
            <span>Dashboard</span>
        </div>

        <div class="gold-line"></div>
        """,
        unsafe_allow_html=True
    )


with right:
    st.markdown(
        f"""
    <div style="text-align:center;">
        <img
            src="data:image/png;base64,{logo}"
            style="width:220px;"
        >
    </div>
    """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style="text-align:center;">

        <div style="
        letter-spacing:5px;
        color:#163923;
        font-size:14px;
        margin-top:8px;
        ">
        KENT STATE UNIVERSITY
        </div>

        <h1 style="
        color:#182945;
        margin-top:30px;
        margin-bottom:5px;
        ">
        Welcome Back
        </h1>

        <p style="
        color:#788087;
        font-size:16px;
        margin-bottom:30px;
        ">
        Sign in to access the greenhouse dashboard
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    username = st.text_input(
        "Email",
        placeholder="ID",
        label_visibility="collapsed"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Password",
        label_visibility="collapsed"
    )

    username=username.lower()

    if st.button("Sign In →"):
                    
        if username == "admin" and password == "1234":
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()

        else:
            st.error("Invalid email or password.") 