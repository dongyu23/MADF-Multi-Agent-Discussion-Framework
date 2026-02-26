from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Annotated

from app.db.session import get_db
from app.schemas import PersonaResponse, GodGenerateRequest, PersonaCreate
from app.crud import create_persona
from app.models import User
from app.api.deps import get_current_user
from app.agent.god import God

router = APIRouter()
god = God()

@router.post("/generate", response_model=List[PersonaResponse])
def generate_personas(
    request: GodGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Generate personas based on natural language prompt using the God agent.
    """
    try:
        # Generate personas using the God agent
        generated_data = god.generate_personas(request.prompt, n=request.n)
        
        if not generated_data:
            raise HTTPException(status_code=500, detail="Failed to generate personas from prompt")
            
        created_personas = []
        for p_data in generated_data:
            # Create Pydantic model from dict
            try:
                # Ensure theories is a list of strings
                if isinstance(p_data.get('theories'), str):
                     # This shouldn't happen if parse_json_from_response works correctly, but safety first
                     import json
                     try:
                        p_data['theories'] = json.loads(p_data['theories'])
                     except:
                        p_data['theories'] = []
                
                persona_create = PersonaCreate(**p_data)
                
                # If user is admin/god, maybe set is_public=True? Default to False for safety
                persona_create.is_public = False 
                
                # Save to DB
                db_persona = create_persona(db=db, persona=persona_create, owner_id=current_user.id)
                created_personas.append(db_persona)
            except Exception as e:
                print(f"Error saving generated persona: {e}")
                continue
                
        if not created_personas:
             raise HTTPException(status_code=500, detail="Failed to save any generated personas")
             
        return created_personas
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"God agent error: {str(e)}")
