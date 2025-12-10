import os
import json
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Type

load_dotenv()

# --- CONFIGURATION ---
try:
    client_gemini = genai.Client(api_key=os.environ.get("DEEPSEEK_API_KEY")) # Or GEMINI_API_KEY
    MODEL_NAME = "gemini-2.5-flash"
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None

# --- DATA MODELS ---

class CardioSession(BaseModel):
    distance_km: float = Field(description="Total distance traveled in kilometers")
    duration_minutes: float = Field(description="Total duration in minutes")
    avg_speed_kmh: float = Field(description="Average speed in km/h")
    calories_burned: int = Field(description="Total calories burned")
    user_goal: Optional[str] = Field(default="general fitness", description="User's goal (e.g., fat loss, marathon prep)")

class CardioInsight(BaseModel):
    headline: str = Field(description="A punchy, encouraging summary title")
    performance_analysis: str = Field(description="Detailed analysis of pace and effort")
    health_benefit: str = Field(description="Specific physiological benefit of this session")
    recovery_tip: str = Field(description="Actionable recovery advice")


def analyze_cardio_session(session_data: CardioSession) -> Optional[CardioInsight]:
    if not client_gemini:
        return None

    user_prompt = f"""
    Analyze this cardio session:
    - Distance: {session_data.distance_km} km
    - Duration: {session_data.duration_minutes} minutes
    
    Provide specific feedback comparing this to average standards and giving recovery advice.
    """

    try:
        response = client_gemini.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            config=GenerateContentConfig(
                temperature=0.3,
                response_schema=CardioInsight,
                response_mime_type="application/json"
            )
        )
        
        raw_json = response.text.strip()
        
        # Robust cleanup (handling markdown wrapping)
        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "").strip()
            
        insight = CardioInsight.model_validate_json(raw_json)
        return insight

    except Exception as e:
        print(f"Error analyzing cardio session: {e}")
        return None

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Simulate data coming from the frontend
    # Example: 5k run in 30 mins
    fake_session = CardioSession(
        distance_km=5.02,
        duration_minutes=30.5,
    )

    print("🏃 Analyzing Run...")
    result = analyze_cardio_session(fake_session)

    if result:
        print("\n" + "="*50)
        print(f"📢 {result.headline.upper()}")
        print("="*50)
        print(f"📊 Analysis: {result.performance_analysis}")
        print(f"❤️ Benefit:  {result.health_benefit}")
        print(f"zzz Recovery: {result.recovery_tip}")
        print("-" * 50)
    else:
        print("Analysis failed.")