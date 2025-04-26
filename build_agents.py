import os
from crewai import Agent, Task, Crew
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import serpapi

# --- Web search utility function ---
def perform_web_search(query: str) -> str:
    results = serpapi.search({
        "q": query,
        "api_key": os.getenv("SERPAPI_KEY"),
    })
    top = results.get("organic_results", [])[:5]
    return "\n".join([f"{r['title']}: {r['link']}" for r in top])

# --- Validating the business idea ---
def validate_business_idea(user_input, llm):
    prompt_template = """
        You are a startup consultant. 
        Is the following input a valid business idea with having a specific context and reasonable background story?
        Respond only with 'yes' or 'no'.\n\n
        Input: {idea}
        """
    
    prompt = PromptTemplate(
        input_variables=['idea'], template=prompt_template
    )
    
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(user_input).strip().lower()
        
    if response == "yes":
        return True
    else:
        return False

# --- Rephrase the given business idea input for better results ---
def rephrase_business_idea(user_input, llm):
    prompt_template = """
    Rephrase the following input into a viable startup idea. 
    If it's totally irrelevant or empty, write only 'INVALID'.
    
    Input: {idea}"
    """
    
    prompt = PromptTemplate(
        input_variables=['idea'], template=prompt_template
    )

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(user_input).strip()
        
    return response

# --- Build Agents Crew ---
def build_agents(llm):
    return {
        "market_analyst": Agent(
            role="Market Analyst",
            goal="Analyze the market and summarize top competitors",
            backstory="Expert in identifying industry trends and players.",
            llm=llm,
            verbose=False
        ),
        "swot_analyst": Agent(
            role="SWOT Analyst",
            goal="Perform SWOT analysis on the given business idea",
            backstory="Skilled in strategic assessment of business plans.",
            llm=llm,
            verbose=False
        ),
        "orchestrator": Agent(
            role="Orchestrator",
            goal="Combine all outputs into a strategic summary report",
            backstory="Executive advisor skilled in strategy reporting.",
            llm=llm,
            verbose=False
        )
    }

# --- Run Crew ---
def run_auto_advisor(user_idea: str, llm):
    
    agents = build_agents(llm)
    
    if os.getenv("SERPAPI_KEY"):
        try:
            research = perform_web_search(user_idea)
        except:
            research = None
    else:
        research = None

    tasks = [
        Task(
            description=f"Analyze the market and competitors for '{user_idea}'. Use web search (if provided):\n{research}.",
            agent=agents["market_analyst"],
            expected_output="Top 2–3 competitors, gaps, and industry trends."
        ),
        Task(
            description=f"Create a SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) for this idea:\n'{user_idea}'",
            agent=agents["swot_analyst"],
            expected_output="Full SWOT breakdown in bullet format."
        ),
        Task(
            description=f"""
            You are the orchestrator. Combine:
            1. Web research (if provided): {research}, 
            2. Market analysis including major competitors from Market Analyst Agent
            3. SWOT analysis from SWOT Analyst Agent

            Create a strategic business report with the following sections:
            - Executive summary
            - SWOT Analysis
            - Market insight
            - Strategic recommendation

            Write the section header names as bold text.
            Write SWOT sub-headers as italic text and their content as bullet points.
            Write 'SWOT Analysis' header and 'Strengths' sub-header to different lines
            """,
            agent=agents["orchestrator"],
            expected_output="Complete business strategy report with SWOT analysis."
        )
    ]

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=False
    )

    return crew.kickoff()