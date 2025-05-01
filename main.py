import os
import time
import streamlit as st
from markdown_pdf import MarkdownPdf, Section
from langchain_openai import ChatOpenAI
from build_agents import run_auto_advisor, validate_business_idea, rephrase_business_idea

import warnings
warnings.filterwarnings("ignore")

os.environ["OPENAI_API_KEY"] = ""
os.environ["SERPER_API_KEY"] = ""

TEMPERATURE = 0.5
LLM_MODELS = ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o-mini", "gpt-3.5-turbo"]

def run_crew(idea_input):
    
    # --- Run Crew ---
    with st.spinner("🤖 Running AutoAdvisor to generate business strategy report ..."):
        final_report = run_auto_advisor(idea_input, llm)

    st.session_state["final_report"] = final_report.raw  # Save the raw report
    st.success("✅ Analysis completed!")
    st.markdown("### 📄 Final Business Strategy Report")

    with st.chat_message("assistant"):
        st.write_stream(stream_output(final_report.raw))
    
    file_name = export_pdf(final_report.raw)
    st.session_state["file_name"] = file_name  # Save filename for download

# --- Download the report as a pdf file
def download_report():
    if "final_report" in st.session_state and "file_name" in st.session_state:
        with open(f'reports/{st.session_state["file_name"]}', "rb") as pdf_file:
            PDFbyte = pdf_file.read()
            
        st.download_button(
            type="secondary",
            label="📥 Download Report as PDF",
            data=PDFbyte,
            file_name=st.session_state["file_name"],
            mime='application/octet-stream'
        )

# --- Export and save the generated report as pdf ---
def export_pdf(file, file_name='Business Strategy Report.pdf'):
    os.makedirs("reports", exist_ok=True)
    
    pdf = MarkdownPdf()
    pdf.meta["title"] = 'AI-Powered Business Report'
    pdf.add_section(Section(file, toc=False))
    pdf.save(f'reports/{file_name}')
    
    return file_name

# --- Convert the generated output to a text stream ---
def stream_output(report):
    for word in report.split(" "):
        yield word + " "
        time.sleep(0.02)

# --- Streamlit UI ---
st.set_page_config(page_title="AutoAdvisor", page_icon="🧠", layout="wide")
st.title("🧠 AutoAdvisor — Your AI Business Strategy Assistant")

# Sidebar for configuration
st.sidebar.header("🤖 Configuration")
    
llm_model = st.sidebar.selectbox(
    "✨ Select an LLM Model", 
    options=LLM_MODELS,
    index=None
    )

if llm_model:

    # --- Get LLM API Key ---
    openai_key = st.sidebar.text_input("🔑 Enter OpenAI API Key", type="password")
        
    serperapi_key = st.sidebar.text_input("🔑 Enter a SerperAPI key (Optional)", type="password")
    st.sidebar.info("❗ Use SerperAPI for enabling real time web search, hence expect better report outcome")

    if serperapi_key:
        st.sidebar.success("✅ SerperAPI Key is entered!")
        os.environ["SERPER_API_KEY"] = serperapi_key
    
    if openai_key:
        st.sidebar.success("✅ OpenAI API Key is entered!")
        os.environ["OPENAI_API_KEY"] = openai_key

        st.write("Enter a business idea below to generate a market-ready strategy report:")

        try:

            # --- LLM Configuration ---
            llm = ChatOpenAI(
                model=llm_model, 
                temperature=TEMPERATURE,
                api_key=os.getenv("OPENAI_API_KEY")
                )

            # --- Business Idea Input ---
            user_idea = st.text_area(
                "💡 Enter your business idea", 
                placeholder="e.g. AI-powered wellness coach for remote workers", 
                height=120,
                key="user_idea"
            )
            
            # --- Watch for user_idea change and reset session ---
            if "last_idea" not in st.session_state:
                st.session_state["last_idea"] = user_idea

            if st.session_state["last_idea"] != user_idea:
                st.session_state["last_idea"] = user_idea
                st.session_state.corrected_idea = None
                st.session_state.original_invalid_idea = None
                st.session_state.final_report = None
                st.session_state.file_name = None
            
            if user_idea.strip():
                
                if validate_business_idea(user_idea, llm): # Check if the user idea is a valid business idea
                    if st.button("🚀 Generate Business Strategy"):
                        run_crew(user_idea) # Generate report with original idea
                        download_report()
                        
                else:
                    if "corrected_idea" not in st.session_state or st.session_state.get("original_invalid_idea") != user_idea:
                        corrected_idea = rephrase_business_idea(user_idea, llm)
                        
                        st.session_state["corrected_idea"] = corrected_idea
                        st.session_state["original_invalid_idea"] = user_idea
                    else:
                        corrected_idea = st.session_state["corrected_idea"]

                    if corrected_idea.lower() == "invalid":
                        st.error("🚫 Not a valid business idea and couldn't be auto-corrected.")
                    else:
                        st.warning("⚠️ Rephrased your input into a valid business idea:")
                        st.markdown(f"**💡 Rephrased Idea:** {corrected_idea}")

                        if st.button("🚀 Generate Corrected Business Strategy"):
                            run_crew(corrected_idea)
                            download_report()
                                    
            else:
                st.info("⚠️ Please enter a business idea to proceed.")
            
        except Exception as e:
            if e.status_code == 401: # Raise error if invalid OPENAI API Key is entered
                st.warning("⚠️ Please check your OpenAI API key.")        
    else:
        st.info("Enter OpenAI API Key and optionally a SerperAPI Key !")
else:
    st.info("Select an LLM Model to proceed !")
