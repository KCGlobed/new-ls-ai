import json
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.models.students import Students

logger = structlog.get_logger(__name__)

# ── 1. Tool Schemas for OpenAI ──────────────────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_student_data",
            "description": "Fetch detailed academic data for a student. Only use this if the user asks for specific student records, grades, or enrollment status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_user_id": {
                        "type": "string",
                        "description": "The user_id of the student to fetch data for. If the user is asking about themselves, this should be their user_id."
                    }
                },
                "required": ["student_user_id"],
            },
        },
    }
]

# ── 2. Tool Execution Logic ──────────────────────────────────────────────────

def execute_get_student_data(arguments: str, db: Session, current_user_id: str) -> str:
    """
    Executes the 'get_student_data' tool safely.
    Enforces access control so a user can only fetch their own data unless they are an admin.
    """
    try:
        args = json.loads(arguments)
        target_user_id = args.get("student_user_id")

        if not target_user_id:
            return "Error: Missing student_user_id argument."

        # ACCESS CONTROL: Only allow users to query their own data
        # (In a real system, you might check if current_user_id has an 'admin' role)
        if target_user_id != current_user_id:
            logger.warning("unauthorized_tool_access", current_user_id=current_user_id, target_user_id=target_user_id)
            return "Error: You are only authorized to access your own student data."

        # Use SQLAlchemy to safely query the DB (No raw SQL = No SQL Injection!)
        student = db.query(Students).filter(Students.user_id == target_user_id).first()

        if not student:
            return f"No student data found for user ID: {target_user_id}"

        # Format the result nicely for the LLM
        result = {
            "name": student.name,
            "course_id": student.course_id,
            "enrollment_status": student.enrollment_status,
            "performance_data": student.performance_data
        }
        
        logger.info("tool_executed", tool="get_student_data", user_id=current_user_id)
        return json.dumps(result)

    except Exception as e:
        logger.error("tool_execution_failed", tool="get_student_data", error=str(e))
        return f"Database error occurred while fetching student data: {str(e)}"

# ── 3. Tool Dispatcher ───────────────────────────────────────────────────────

def dispatch_tool(tool_call, db: Session, current_user_id: str) -> str:
    """
    Routes the tool call from OpenAI to the correct Python function.
    """
    function_name = tool_call.function.name
    arguments = tool_call.function.arguments

    if function_name == "get_student_data":
        return execute_get_student_data(arguments, db, current_user_id)
    
    return f"Error: Tool '{function_name}' is not implemented."
