from langchain_groq import ChatGroq
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from io import BytesIO
import base64
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()

# GROQ_API = os.getenv("GROQ_API_KEY")
GROQ_API = st.secrets["GROQ_API_KEY"]
llm = ChatGroq(
    api_key=GROQ_API,
    model="llama-3.2-11b-vision-preview"
)

llm2 = ChatGroq(
    api_key=GROQ_API,
    model="llama-3.1-70b-versatile"
)

# Define the main app function
st.set_page_config(page_title="Pictionary App", page_icon="🎨", layout="wide", initial_sidebar_state="auto")
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
st.header(":red[Pictionary] :green[App] 🎨🖌", divider='rainbow')

# Set the timer duration in seconds
TIMER_DURATION = 120

SYSTEM_PROMPT = "You are a pictionary player. I'll give you an image of a doodle and you must output what this image is."
SYSTEM_PROMPT2 = "You are a pictionary player. Generate a new, random, very easy doodle image concept that the user will draw within 2 minutes. Output only the concept without any additional text. For example: Cat standing on a table, Running horse."

def doodle_image():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT2}
            ]
        }
    ]
    try:
        response = llm2.invoke(messages)
        return response.content.strip()
    except Exception as e:  # Catch potential LLM interaction errors
        print(f"Error getting description: {e}")
        return "Error: Could not describe image."

# Initialize session state for selected word
if 'selected_word' not in st.session_state:
    st.session_state.selected_word = doodle_image()

# Display the word to draw
st.subheader(f"Draw this: **{st.session_state.selected_word}**")

# Specify canvas parameters in application
drawing_mode = st.sidebar.selectbox(
    "Drawing tool:", ("freedraw", "point", "line", "rect", "circle", "polygon", "transform")
)

stroke_width = st.sidebar.slider("Stroke width: ", 1, 25, 3)
if drawing_mode == 'point':
    point_display_radius = st.sidebar.slider("Point display radius: ", 1, 25, 3)
stroke_color = st.sidebar.color_picker("Stroke color hex: ")
bg_color = st.sidebar.color_picker("Background color hex: ", "#eee")
# bg_image = st.sidebar.file_uploader("Background image:", type=["png", "jpg"])
st.sidebar.divider()
st.sidebar.markdown(
    """
    🚀 Created by : **Adrit**
    """,
    unsafe_allow_html=True
)

# Initialize session state for timer
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()
if 'end_time' not in st.session_state:
    st.session_state.end_time = st.session_state.start_time + TIMER_DURATION

# Calculate remaining time
remaining_time = int(st.session_state.end_time - time.time())
if remaining_time > 0:
    mm, ss = divmod(remaining_time, 60)
    st.metric("Countdown", f"{mm:02d}:{ss:02d}")
    st.progress((TIMER_DURATION - remaining_time) / TIMER_DURATION)
else:
    st.metric("Countdown", "00:00")
    st.progress(1.0)
    st.warning("Time's up!")
# Function to save the image
def save_image(image_data, filename="drawing.png"):
    image = Image.fromarray(image_data.astype('uint8'), 'RGBA')
    image.save(filename)
    # st.success(f"Image saved successfully as {filename}!")

def image_to_base64(image_data, size=(300, 300)):
    try:
        img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
        img = img.resize(size)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def describe_image(image_data, options={}):
    image_base64 = image_to_base64(image_data)
    if image_base64 is None:
        return "Error: Could not process image."

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ]
        }
    ]
    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:  # Catch potential LLM interaction errors
        print(f"Error getting description: {e}")
        return "Error: Could not describe image."

# Create a canvas component only if time is remaining
if remaining_time > 0:
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Draw Here**")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_color=bg_color,
            background_image=None,
            update_streamlit=True,
            height=400,
            width=800,
            drawing_mode=drawing_mode,
            display_toolbar=True,
            point_display_radius=point_display_radius if drawing_mode == 'point' else 0,
            key="canvas",
        )

        # Store the image data in session state
        if canvas_result.image_data is not None:
            st.session_state.image_data = canvas_result.image_data

    with col2:
        if 'image_data' in st.session_state:
            st.write("**Preview**")
            st.image(st.session_state.image_data, width=800, use_column_width=True)
            if st.button("Save Image"):
                save_image(st.session_state.image_data)
                st.session_state.end_time = time.time()  # Stop the timer

# Save the image automatically when the timer ends
if remaining_time <= 0 and 'image_data' in st.session_state:
    save_image(st.session_state.image_data)

# Refresh the app every second to keep the timer running
if remaining_time > 0:
    time.sleep(1)
    st.rerun()

# Display the saved image
if 'image_data' in st.session_state:
    st.image(st.session_state.image_data)
with st.spinner("Generating Result..."):
    # Describe the saved image
    if 'image_data' in st.session_state:
        out = describe_image(st.session_state.image_data)

        # Judge the match between the two image concepts
        messages_match = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"""You are the Judge. Based on these two image concepts, determine if the images match. If they match, return "PASS". If they do not match, return "FAIL".
                    Image 1: {out}
                    Image 2: {st.session_state.selected_word}"""},
                ]
            }
        ]
        
        try:
            match_response = llm2.invoke(messages_match)
            match_response2 = match_response.content.strip()
            if match_response2 == "PASS":
                st.success(f"Result: {match_response2}\n\nYour Image: {out}")
            elif match_response2 == "FAIL":
                st.warning(f"Result: {match_response2}\n\nYour Image: {out}")
            else:
                st.error("Unexpected response from the judge.")
        except Exception as e:
            st.error(f"Error judging the images: {e}")
