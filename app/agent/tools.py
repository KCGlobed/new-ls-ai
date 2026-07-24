import json
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import text

from sqlalchemy.sql import func
from app.database.models.lms import PracticeTest, TestQuestion, QuestionOption, AssessmentTest, CourseRestriction

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

def execute_get_student_tests_dashboard(arguments: str, db: Session, current_user_id: str) -> str:
    """Read-only query to fetch student tests dashboard aggregates."""
    try:
        args = json.loads(arguments) if arguments else {}
        target_user_id = args.get("student_user_id", current_user_id)
        
        try:
            target_user_id_int = int(target_user_id)
        except ValueError:
            return f"Error: Invalid student ID format: {target_user_id}"

        # Practice Tests Aggregation
        pt_completed = db.query(func.count(PracticeTest.id)).filter(PracticeTest.user_id == target_user_id_int, PracticeTest.status == True).scalar() or 0
        pt_pending = db.query(func.count(PracticeTest.id)).filter(PracticeTest.user_id == target_user_id_int, PracticeTest.status == False).scalar() or 0
        pt_avg_score = db.query(func.avg(PracticeTest.score)).filter(PracticeTest.user_id == target_user_id_int).scalar() or 0

        # Mock (Assessment) Tests Aggregation
        mt_completed = db.query(func.count(AssessmentTest.id)).filter(AssessmentTest.user_id == target_user_id_int, AssessmentTest.status == True).scalar() or 0
        mt_avg_score = db.query(func.avg(AssessmentTest.score)).filter(AssessmentTest.user_id == target_user_id_int).scalar() or 0

        result = {
            "practice_tests": {
                "completed": pt_completed,
                "pending": pt_pending,
                "average_score": round(pt_avg_score, 2)
            },
            "mock_tests": {
                "completed": mt_completed,
                "average_score": round(mt_avg_score, 2)
            }
        }
            
        logger.info("tool_executed", tool="get_student_tests_dashboard", user_id=current_user_id)
        return json.dumps(result)
    except Exception as e:
        logger.error("tool_execution_failed", tool="get_student_tests_dashboard", error=str(e))
        return f"Database error occurred: {str(e)}"

def execute_get_student_overall_progress(arguments: str, db: Session, current_user_id: str) -> str:
    """Read-only query to fetch student overall progress and assigned courses."""
    try:
        args = json.loads(arguments) if arguments else {}
        target_user_id = args.get("student_user_id", current_user_id)
        
        try:
            target_user_id_int = int(target_user_id)
        except ValueError:
            return f"Error: Invalid student ID format: {target_user_id}"

        # Assigned Courses
        courses_assigned = db.query(func.count(CourseRestriction.id)).filter(CourseRestriction.user_id == target_user_id_int).scalar() or 0
        
        # Overall Performance (average of practice and mock)
        pt_avg = db.query(func.avg(PracticeTest.score)).filter(PracticeTest.user_id == target_user_id_int).scalar() or 0
        mt_avg = db.query(func.avg(AssessmentTest.score)).filter(AssessmentTest.user_id == target_user_id_int).scalar() or 0
        
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


def execute_get_question_solution(arguments: str, db: Session, current_user_id: str) -> str:
    """Read-only query to fetch the correct option for a question."""
    try:
        args = json.loads(arguments)
        question_id = args.get("question_id")
        
        if not question_id:
            return "Error: Missing question_id argument."

        # Safe SQLAlchemy read-only query
        question = db.query(TestQuestion).filter(TestQuestion.id == question_id).first()
        
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
            correct_option = db.query(QuestionOption).filter(QuestionOption.id == question.right_option_id).first()
            if correct_option:
                result["solution_text"] = correct_option.option
            else:
                result["solution_text"] = f"Correct option ID {question.right_option_id} could not be found in the database."
                
        logger.info("tool_executed", tool="get_question_solution", user_id=current_user_id, question_id=question_id)
        return json.dumps(result)
    except Exception as e:
        logger.error("tool_execution_failed", tool="get_question_solution", error=str(e))
        return f"Database error occurred: {str(e)}"

# ── 3. Tool Dispatcher ───────────────────────────────────────────────────────

def dispatch_tool(tool_call, db: Session, current_user_id: str) -> str:
    """Routes the tool call from OpenAI to the correct Python function."""
    function_name = tool_call.function.name
    arguments = tool_call.function.arguments

    if function_name == "get_student_tests_dashboard":
        return execute_get_student_tests_dashboard(arguments, db, current_user_id)
    elif function_name == "get_student_overall_progress":
        return execute_get_student_overall_progress(arguments, db, current_user_id)
    elif function_name == "get_question_solution":
        return execute_get_question_solution(arguments, db, current_user_id)
        
    return f"Error: Tool '{function_name}' is not implemented."
