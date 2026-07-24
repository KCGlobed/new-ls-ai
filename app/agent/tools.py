import json
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = structlog.get_logger(__name__)

# ── 1. Tool Schemas for OpenAI ──────────────────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_student_tests_dashboard",
            "description": "Fetch a summary of a student's practice tests and mock tests (assessments). This gives counts of completed/pending tests and average scores. Use this when the user asks about their test performance, pending tests, or mock tests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_user_id": {
                        "type": "string",
                        "description": "The integer ID of the student. If not provided, defaults to current user."
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_overall_progress",
            "description": "Fetch the student's overall learning progress, overall performance, and number of courses assigned. Use this when a user asks for overall progress, overall performance, or assigned courses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_user_id": {
                        "type": "string"
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_question_solution",
            "description": "Fetch the correct solution/option for a specific test question by its ID. Use this when a user asks for the answer or solution to a question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "integer",
                        "description": "The unique integer ID of the question."
                    }
                },
                "required": ["question_id"],
            },
        },
    }
]

# ── 2. Tool Execution Logic ──────────────────────────────────────────────────

def execute_get_student_tests_dashboard(arguments: str, lms_db: Session, current_user_id: str) -> str:
    """Read-only raw SQL query to fetch student tests dashboard aggregates from LMS DB."""
    try:
        args = json.loads(arguments) if arguments else {}
        target_user_id = args.get("student_user_id", current_user_id)
        
        try:
            target_user_id_int = int(target_user_id)
        except ValueError:
            return f"Error: Invalid student ID format: {target_user_id}"

        # Practice Tests Aggregation
        pt_res = lms_db.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = true) as completed,
                COUNT(*) FILTER (WHERE status = false) as pending,
                AVG(score) as avg_score
            FROM practice_practicetests
            WHERE user_id = :uid
        """), {"uid": target_user_id_int}).fetchone()

        pt_completed = pt_res.completed or 0
        pt_pending = pt_res.pending or 0
        pt_avg_score = pt_res.avg_score or 0

        # Mock (Assessment) Tests Aggregation
        mt_res = lms_db.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = true) as completed,
                AVG(score) as avg_score
            FROM assessment_assessmenttests
            WHERE user_id = :uid
        """), {"uid": target_user_id_int}).fetchone()

        mt_completed = mt_res.completed or 0
        mt_avg_score = mt_res.avg_score or 0

        result = {
            "practice_tests": {
                "completed": pt_completed,
                "pending": pt_pending,
                "average_score": round(float(pt_avg_score), 2)
            },
            "mock_tests": {
                "completed": mt_completed,
                "average_score": round(float(mt_avg_score), 2)
            }
        }
            
        logger.info("tool_executed", tool="get_student_tests_dashboard", user_id=current_user_id)
        return json.dumps(result)
    except Exception as e:
        logger.error("tool_execution_failed", tool="get_student_tests_dashboard", error=str(e))
        return f"Database error occurred: {str(e)}"

def execute_get_student_overall_progress(arguments: str, lms_db: Session, current_user_id: str) -> str:
    """Read-only raw SQL query to fetch student overall progress and assigned courses from LMS DB."""
    try:
        args = json.loads(arguments) if arguments else {}
        target_user_id = args.get("student_user_id", current_user_id)
        
        try:
            target_user_id_int = int(target_user_id)
        except ValueError:
            return f"Error: Invalid student ID format: {target_user_id}"

        # Assigned Courses
        courses_assigned = lms_db.execute(text("""
            SELECT COUNT(id) FROM subscription_coursesubjectrestriction WHERE user_id = :uid
        """), {"uid": target_user_id_int}).scalar() or 0
        
        # Overall Performance (average of practice and mock)
        pt_avg = lms_db.execute(text("""
            SELECT AVG(score) FROM practice_practicetests WHERE user_id = :uid
        """), {"uid": target_user_id_int}).scalar() or 0
        
        mt_avg = lms_db.execute(text("""
            SELECT AVG(score) FROM assessment_assessmenttests WHERE user_id = :uid
        """), {"uid": target_user_id_int}).scalar() or 0
        
        pt_avg = float(pt_avg) if pt_avg else 0
        mt_avg = float(mt_avg) if mt_avg else 0

        overall_performance = (pt_avg + mt_avg) / 2 if (pt_avg and mt_avg) else (pt_avg or mt_avg or 0)

        result = {
            "overall_performance_score": round(overall_performance, 2),
            "courses_assigned": courses_assigned,
            "overall_learning_progress": "Progress calculation requires chapter tracking tables which are currently unknown.",
            "videos_watched": "Video tracking table unknown.",
            "study_plan": "Study plan table unknown."
        }
            
        logger.info("tool_executed", tool="get_student_overall_progress", user_id=current_user_id)
        return json.dumps(result)
    except Exception as e:
        logger.error("tool_execution_failed", tool="get_student_overall_progress", error=str(e))
        return f"Database error occurred: {str(e)}"


def execute_get_question_solution(arguments: str, lms_db: Session, current_user_id: str) -> str:
    """Read-only raw SQL query to fetch the correct option for a question from LMS DB."""
    try:
        args = json.loads(arguments)
        question_id = args.get("question_id")
        
        if not question_id:
            return "Error: Missing question_id argument."

        question = lms_db.execute(text("""
            SELECT id, question_type, level, right_option_id 
            FROM questions_testquestions 
            WHERE id = :qid
        """), {"qid": question_id}).fetchone()
        
        if not question:
            return f"No question found with ID: {question_id}"
            
        result = {
            "question_id": question.id,
            "question_type": question.question_type,
            "level": question.level
        }
        
        # Handle questions without options (simulations/essays)
        if not question.right_option_id:
            result["solution_text"] = "This question does not have a multiple choice correct option (it may be a simulation or essay)."
        else:
            correct_option = lms_db.execute(text("""
                SELECT option 
                FROM questions_questionoptions 
                WHERE id = :opt_id
            """), {"opt_id": question.right_option_id}).scalar()
            
            if correct_option:
                result["solution_text"] = correct_option
            else:
                result["solution_text"] = f"Correct option ID {question.right_option_id} could not be found in the database."
                
        logger.info("tool_executed", tool="get_question_solution", user_id=current_user_id, question_id=question_id)
        return json.dumps(result)
    except Exception as e:
        logger.error("tool_execution_failed", tool="get_question_solution", error=str(e))
        return f"Database error occurred: {str(e)}"

# ── 3. Tool Dispatcher ───────────────────────────────────────────────────────

def dispatch_tool(tool_call, lms_db: Session, current_user_id: str) -> str:
    """Routes the tool call from OpenAI to the correct Python function."""
    function_name = tool_call.function.name
    arguments = tool_call.function.arguments

    if function_name == "get_student_tests_dashboard":
        return execute_get_student_tests_dashboard(arguments, lms_db, current_user_id)
    elif function_name == "get_student_overall_progress":
        return execute_get_student_overall_progress(arguments, lms_db, current_user_id)
    elif function_name == "get_question_solution":
        return execute_get_question_solution(arguments, lms_db, current_user_id)
        
    return f"Error: Tool '{function_name}' is not implemented."
