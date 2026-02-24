import streamlit as st
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from schema import InterviewSnapshot

# 1. Load Environment & Key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. The Master System Prompt (The Bouncer)
SYSTEM_PROMPT = """
You are an elite, highly aggressive Product Management Coach specializing in Teresa Torres' Continuous Discovery Habits. 
Your objective is to ingest raw user interview transcripts and act as a ruthless gatekeeper.

RULES FOR SYNTHESIS:
1. The Story Test: Good interviews collect specific stories about past behavior. Bad interviews ask speculative questions ("Would you use this?", "What do you typically do?"). You must aggressively flag speculative questions and deduct points from the Quality Score.
2. The Opportunity Test: An opportunity is an unmet need, pain point, or desire. IT IS NEVER A SOLUTION. If the user asks for a feature, reframe it as the underlying need.
3. No Hallucinations: If the transcript is shallow, the output must be shallow. Do not invent context or infer missing goals.
"""

# 3. Streamlit UI Build
st.set_page_config(layout="wide", page_title="The Catalyst: Discovery Bouncer")
st.title("The Catalyst: Discovery Bouncer (Gemini 2.5 Pro)")
st.markdown("Upload a raw transcript. The engine will grade your interview technique and extract opportunities based on continuous discovery habits.")

uploaded_file = st.file_uploader("Upload raw transcript (.txt or .md)", type=["txt", "md"])

if uploaded_file is not None:
    transcript_text = uploaded_file.read().decode("utf-8")
    
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("Raw Transcript")
        st.text_area("Transcript Data", transcript_text, height=600, label_visibility="collapsed")
        
    with col2:
        st.subheader("Synthesis & Critique")
        if st.button("Run Blindspot Interrogator", type="primary", use_container_width=True):
            with st.spinner("Analyzing transcript logic and extracting opportunities..."):
                try:
                    # Initialize Gemini 2.5 Pro
                    model = genai.GenerativeModel('gemini-2.5-pro')
                    
                    # API Call with Structured Outputs and Safety Overrides
                    response = model.generate_content(
                        f"{SYSTEM_PROMPT}\n\nTranscript:\n{transcript_text}",
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=InterviewSnapshot,
                        ),
                        safety_settings={
                            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                        }
                    )
                    
                    # Parse the flawless JSON
                    result = json.loads(response.text)
                    
                    # --- RENDER THE OUTPUT ---
                    score = result["quality_check"]["score"]
                    color = "red" if score < 7 else "green"
                    
                    st.markdown(f"### Quality Score: :{color}[{score}/10]")
                    st.write("**The Catalyst's Feedback:**", result["quality_check"]["feedback"])
                    
                    if result["quality_check"]["flagged_questions"]:
                        st.error("**Flagged Speculative Questions:**\n" + "\n".join([f"- {q}" for q in result["quality_check"]["flagged_questions"]]))
                    
                    st.divider()
                    
                    st.markdown("### Interview Snapshot")
                    st.markdown(f"> *\"{result['memorable_quote']}\"*")
                    
                    st.markdown("**Quick Facts:**")
                    for fact in result["quick_facts"]:
                        st.markdown(f"- {fact}")
                        
                    st.markdown("**Experience Map Steps:**")
                    for step in result["experience_map_steps"]:
                        st.markdown(f"- {step}")
                        
                    st.markdown("**Validated Opportunities:**")
                    for opp in result["opportunities"]:
                        with st.expander(opp['opportunity_statement']):
                            st.caption("Source Quote:")
                            st.write(f"*{opp['source_quote']}*")

                except Exception as e:
                    st.error(f"Engine Failure: {e}")