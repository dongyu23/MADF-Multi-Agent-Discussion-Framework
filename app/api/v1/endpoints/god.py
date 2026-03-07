from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Any
import json

from app.db.session import get_db
from app.schemas import PersonaResponse, GodGenerateRequest, PersonaCreate
from app.crud import create_persona
from app.api.deps import get_current_user
from app.agent.god import God
from app.agent.real_god import RealGodAgent
from app.core.async_utils import async_generator_wrapper

router = APIRouter()
god = God()

@router.post("/generate", response_model=List[PersonaResponse])
def generate_personas(
    request: GodGenerateRequest,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    """
    Generate personas based on natural language prompt using the God agent.
    """
    try:
        # First determine the count N using LLM
        n = god.get_persona_count(request.prompt, default_n=request.n)
        
        # Generate personas using the God agent
        generated_data = god.generate_personas(request.prompt, n=n)
        
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

@router.post("/generate_real")
async def generate_real_personas(
    request: GodGenerateRequest,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    """
    Generate personas using RealGodAgent with internet search capabilities.
    Each persona is generated sequentially to ensure high quality and deep research.
    Returns a StreamingResponse with SSE events.
    """
    agent = RealGodAgent()
    user_id = current_user.id
    
    # 1. Fetch all existing persona names from DB for global deduplication
    try:
        rs = db.execute("SELECT name FROM personas")
        # rs.fetchall() returns list of Row objects or tuples?
        # fetch_all returns list of RowObject
        from app.db.client import fetch_all
        rows = fetch_all(rs)
        db_existing_names = [r.name for r in rows if hasattr(r, 'name')]
    except Exception as e:
        print(f"Error fetching existing names: {e}")
        db_existing_names = []

    async def event_generator():
        try:
            # Delegate loop control to RealGodAgent
            # Pass user prompt, let agent determine N (pass None)
            # Pass db_existing_names
            generated_names_in_session = []
            
            # Run the agent
            # Note: agent.run is a synchronous generator. To avoid blocking the event loop for too long,
            # we should iterate it. If individual steps are slow (network calls), they will block.
            # Ideally, we run this in a thread, but for simplicity with StreamingResponse, 
            # direct iteration is often acceptable if concurrency isn't massive.
            # Or we can use run_in_threadpool if we restructure agent.run.
            # For now, we iterate directly as it yields frequently.
            
            # Use n=None to allow the agent to auto-detect count from prompt
            # But respect request.n if it is > 1 (explicitly set)
            target_n = request.n if request.n > 1 else None
            
            async for event in async_generator_wrapper(agent.run(request.prompt, n=target_n, generated_names=generated_names_in_session, db_existing_names=db_existing_names)):
                
                # If result, save to DB
                if event["type"] == "result":
                    personas_data = event["content"]
                    saved_personas = []
                    
                    # Ensure it's a list
                    if isinstance(personas_data, dict):
                        personas_data = [personas_data]
                        
                    for p_data in personas_data:
                        # Add name to session list
                        if p_data.get('name'):
                            generated_names_in_session.append(p_data['name'])
                        
                        try:
                            if isinstance(p_data.get('theories'), str):
                                try:
                                    p_data['theories'] = json.loads(p_data['theories'])
                                except:
                                    p_data['theories'] = []
                            
                            persona_create = PersonaCreate(**p_data)
                            persona_create.is_public = False
                            
                            db_persona = create_persona(db=db, persona=persona_create, owner_id=user_id)
                            
                            # Convert to dict for JSON serialization
                            saved_personas.append({
                                "id": db_persona.id,
                                "name": db_persona.name,
                                "title": db_persona.title,
                                "bio": db_persona.bio,
                                "theories": db_persona.theories,
                                "stance": db_persona.stance,
                                "system_prompt": db_persona.system_prompt,
                                "is_public": db_persona.is_public
                            })
                        except Exception as e:
                            print(f"Error saving real persona: {e}")
                    
                    # Update content with saved personas (including IDs)
                    event["content"] = saved_personas
                
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # Final message after all generations are done
            final_msg = f"✅ 所有智能体角色已生成并保存完毕。已停止生成。"
            yield f"data: {json.dumps({'type': 'thought', 'content': final_msg}, ensure_ascii=False)}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
