# core/definitions.py
from pydantic import BaseModel, Field
from typing import Dict, Any

class SkillSchema(BaseModel):
    """
    Standard data structure for the skill registry.
    LLM must populate this structure when generating new skills.
    """
    name: str = Field(..., description="Name of the skill function, e.g., 'get_weather_data'")
    description: str = Field(..., description="Natural language description of the skill, used for Router matching")
    file_name: str = Field(..., description="Filename to save, e.g., 'get_weather.py'")
    parameters: Dict[str, Any] = Field(..., description="Parameter Schema following the OpenAI Function Calling standard")
    
    # This is a Pydantic trick to ensure LLM generates JSON matching the Schema
    class Config:
        json_schema_extra = {
            "example": {
                "name": "calculate_sum",
                "description": "Calculate the sum of two numbers",
                "file_name": "math_tools.py",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            }
        }