import streamlit as st

st.set_page_config(page_title="Greeting Demo", layout="centered")

st.title("Hello — Welcome")

st.write("Click the button below:")

if st.button("Click me"):
    st.write("Button clicked")


