
import streamlit as st
import requests

def change_pass():

    st.title("Change Password")

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
<<<<<<< Updated upstream
=======
            if not token:
                        st.error("Your session has expired. Please log in again.")
                        return 
>>>>>>> Stashed changes

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
