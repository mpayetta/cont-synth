import os
import google.generativeai as genai
from sqlmodel import Session, create_engine, select
from cont_synth.models import Opportunity
from dotenv import load_dotenv

# Initialize Gemini
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
flash_model = genai.GenerativeModel('gemini-2.5-flash')

# Connect directly to your local Reflex database
engine = create_engine("sqlite:///reflex.db")

def run_backfill():
    print("Initiating AI Data Backfill...")
    with Session(engine) as session:
        # Find all un-themed opportunities
        stale_opps = session.exec(select(Opportunity).where(Opportunity.theme == "Uncategorized")).all()
        
        if not stale_opps:
            print("Everything is already categorized!")
            return

        for opp in stale_opps:
            # The ultra-strict classification prompt
            prompt = f"""
            You are a Product Manager. Read the following user unmet need and categorize it into a strict 1-3 word high-level theme (e.g., Data Privacy, Version Control, PPT Formatting, Reporting Speed).
            Output ONLY the 1-3 word theme. No punctuation, no explanation.

            Unmet Need: {opp.statement}
            """
            
            # Ask Flash to categorize it
            response = flash_model.generate_content(prompt)
            new_theme = response.text.strip().replace('"', '')
            
            print(f"Mapping: '{opp.statement[:40]}...'  =>  [{new_theme}]")
            
            # Update the database
            opp.theme = new_theme
            session.add(opp)
        
        # Save all changes to SQLite
        session.commit()
        print("\nBackfill complete! Refresh your browser.")

if __name__ == "__main__":
    run_backfill()