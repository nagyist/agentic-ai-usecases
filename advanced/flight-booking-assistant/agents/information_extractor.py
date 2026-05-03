import json
from utils.prompts import SYSTEM_PERSONA, EXTRACTION_PROMPT
from utils.llm import call_llm_json

def information_extractor_agent(state):
    """
    Extract structured booking information from user input.
    This agent focuses solely on information extraction and updating the state.
    """
    print(f"\n[DEBUG] information_extractor_agent called")
    print(f"[DEBUG] Current state: {state}")
    
    user_input = state.get("last_user_input", "")
    print(f"[DEBUG] User input: '{user_input}'")
    
    if not user_input:
        print(f"[DEBUG] No user input to extract from")
        return state
    
    # Extract information from user input
    extraction_prompt = EXTRACTION_PROMPT.format(
        system=SYSTEM_PERSONA,
        user_input=user_input
    )
    print(f"[DEBUG] Running extraction prompt")
    
    try:
        extracted = call_llm_json(extraction_prompt)
        print(f"[DEBUG] Extracted data: {extracted}")
        
        # Smart city assignment logic
        if extracted.get("departure_city") or extracted.get("destination_city"):
            extracted_city = extracted.get("departure_city") or extracted.get("destination_city")
            
            # If we already have a destination but this is a different city, it's likely departure
            if extracted_city and state.get("destination_city") and extracted_city != state.get("destination_city"):
                print(f"[DEBUG] Reassigning '{extracted_city}' to departure_city (we already have destination)")
                extracted["departure_city"] = extracted_city
                extracted["destination_city"] = None
            # If we already have departure but this is different, it's likely destination
            elif extracted_city and state.get("departure_city") and extracted_city != state.get("departure_city"):
                print(f"[DEBUG] Reassigning '{extracted_city}' to destination_city (we already have departure)")
                extracted["destination_city"] = extracted_city
                extracted["departure_city"] = None
        
        # Update state with extracted information
        extracted_count = 0
        for key, value in extracted.items():
            if value:
                print(f"[DEBUG] Updating {key} = {value}")
                state[key] = value
                extracted_count += 1
        
        print(f"[DEBUG] Successfully extracted {extracted_count} pieces of information")
        
    except Exception as e:
        print(f"[DEBUG] Extraction error: {e}")
    
    # Track extraction in state for debugging
    state["extraction_attempted"] = True
    state["step"] = "EXTRACTED"
    
    print(f"[DEBUG] State after extraction: {state}")
    return state
