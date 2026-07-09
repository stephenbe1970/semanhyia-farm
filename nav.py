import streamlit as st

def show_sidebar():
    # Streamlit automatically handles the path to files in the /pages folder.
    # Use the filename exactly as it appears in the folder.
    st.sidebar.page_link("pages/Dashboard.py", label="Dashboard")
    st.sidebar.page_link("pages/Recharge.py", label="Recharge")
    st.sidebar.page_link("pages/Withdraw.py", label="Withdraw")
    st.sidebar.page_link("pages/mine.py", label="Profile")

    # Only show Admin links to you
    if st.session_state.get('user_mobile') == "0505162314":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Admin Tools") # Removed "pages/" from header label
        st.sidebar.page_link("pages/Admin_Hub.py", label="Admin Hub")
        st.sidebar.page_link("pages/Admin_Recharge.py", label="Admin Recharge")
        st.sidebar.page_link("pages/Admin_Withdrawals.py", label="Admin Withdrawals")