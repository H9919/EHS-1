# routes/chatbot.py - ENHANCED VERSION with smart chatbot integration
import json
import os
import time
from pathlib import Path
from werkzeug.utils import secure_filename
from utils.uploads import is_allowed, save_upload
from services.ehs_chatbot import SmartIntentClassifier
from flask import Blueprint, request, jsonify, render_template

chatbot_bp = Blueprint("chatbot", __name__)

# Lightweight classifier for fast first-turn routing
quick_intent_classifier = SmartIntentClassifier()

# Global chatbot instance - lazy loaded with better error handling
_chatbot_instance = None
_chatbot_creation_attempted = False

# --- replace your get_chatbot() with this ---
def get_chatbot():
    """Get or create chatbot instance with comprehensive error handling"""
    global _chatbot_instance, _chatbot_creation_attempted

    # If we don't have a bot, always (re)attempt creation
    if _chatbot_instance is None:
        try:
            from services.ehs_chatbot import create_chatbot  # preferred path
            _chatbot_instance = create_chatbot()
            _chatbot_creation_attempted = True
            print("✓ Smart chatbot loaded via factory")
        except Exception as e1:
            print(f"⚠ create_chatbot not available ({e1}); trying direct class...")
            try:
                from services.ehs_chatbot import SmartEHSChatbot
                _chatbot_instance = SmartEHSChatbot()
                _chatbot_creation_attempted = True
                print("✓ Smart chatbot loaded via direct class")
            except Exception as e2:
                print(f"❌ Smart chatbot loading error: {e2}")
                _chatbot_instance = None

    return _chatbot_instance


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
UPLOAD_FOLDER = Path("static/uploads")


def ensure_upload_dir():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

@chatbot_bp.route("/chat", methods=["GET", "POST"])
def chat_interface():
    """Enhanced chat interface with smart conversation management"""
    if request.method == "GET":
        return render_template("enhanced_dashboard.html")
    
    try:    t0 = time.monotonic()

        # Parse request data with enhanced validation
        user_message, user_id, context, uploaded_file = parse_request_data_comprehensive()
        
        print(f"DEBUG: Chat request - message: '{user_message[:100]}...', has_file: {bool(uploaded_file)}")
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        if not chatbot:
            return jsonify(get_enhanced_fallback_response(user_message, uploaded_file))
        
        try:
            # Process with smart chatbot
            response = chat
        # Fast path for incident start: instant response without heavy processing
        try:
            intent, conf = quick_intent_classifier.classify(user_message)
        except Exception:
            intent, conf = None, 0.0
        
        if intent == "incident_reporting":
            app_msg = ("Okay—let’s start your incident report.\n"
                       "What kind of incident is it? (injury, vehicle, near miss, property, "
                       "environmental, security, depot, other)")
            # Log timing for fast path
            try:
                import logging
                logging.getLogger(__name__).info("chat:fast_first %.3fs", time.monotonic() - t0)
            except Exception:
                pass
            return jsonify({"ok": True, "message": app_msg, "type": "incident_start", "intent": intent, "confidence": conf})
bot.process_message(user_message, user_id, context)
            
            # Validate and enhance response
            response = validate_and_enhance_response(response, user_message, uploaded_file)
            
            print(f"DEBUG: Smart response generated: {response.get('type')
            try:
                import logging
                logging.getLogger(__name__).info(\"chat:smart %.3fs\", time.monotonic() - t0)
            except Exception:
                pass
}")
            return jsonify(response)
            
        except Exception as e:
            print(f"ERROR: Smart chatbot processing failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify(get_enhanced_fallback_response(user_message, uploaded_file, str(e)))
    
    except Exception as e:
        print(f"ERROR: Chat route exception: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "message": "🔧 **I'm having trouble processing your request.**\n\nLet's try a different approach - you can use the navigation menu or try asking in a different way.",
            "type": "system_error",
            "actions": [
                {"text": "🚨 Report Incident", "action": "navigate", "url": "/incidents/new"},
                {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"},
                {"text": "🔄 Try Again", "action": "retry"}
            ],
            "quick_replies": [
                "Report incident",
                "Main menu",
                "Try again",
                "Contact support"
            ]
        })

def parse_request_data_comprehensive():
    """Enhanced request data parsing with comprehensive validation"""
    try:
        user_message = ""
        user_id = "default_user"
        context = {}
        uploaded_file = None
        
        if request.is_json:
            # JSON request
            data = request.get_json() or {}
            user_message = str(data.get("message", "")).strip()
            user_id = str(data.get("user_id", "default_user"))
            context = data.get("context", {})
            
            if not isinstance(context, dict):
                context = {}
                
        else:
            # Form request
            user_message = str(request.form.get("message", "")).strip()
            user_id = str(request.form.get("user_id", "default_user"))
            
            # Parse context from form if provided
            context_str = request.form.get("context", "{}")
            try:
                context = json.loads(context_str) if context_str else {}
            except json.JSONDecodeError:
                context = {}
            
            # Handle file upload
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename and is_allowed(file.filename):
                    uploaded_file = handle_file_upload_secure(file)
        
        # Add file info to context
        if uploaded_file:
            context["uploaded_file"] = uploaded_file
            if not user_message:
                user_message = f"I've uploaded a file: {uploaded_file.get('filename', 'unknown')}"
        
        # Validate message length and content
        if len(user_message) > 5000:
            user_message = user_message[:5000] + "..."
        
        # Add request metadata to context
        context.update({
            "timestamp": time.time(),
            "request_method": request.method,
            "user_agent": request.headers.get("User-Agent", "")[:100]  # Truncate for safety
        })
        
        return user_message, user_id, context, uploaded_file
        
    except Exception as e:
        print(f"ERROR: Failed to parse request data: {e}")
        return "", "default_user", {}, None

def handle_file_upload_secure(file):
    """Secure file upload handling with enhanced validation"""
    try:
        ensure_upload_dir()
        
        filename = secure_filename(file.filename)
        if not filename:
            return None
        
        # Validate file size (16MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 16 * 1024 * 1024:  # 16MB
            print(f"ERROR: File too large: {file_size} bytes")
            return None
        
        # Add timestamp to avoid conflicts
        timestamp = str(int(time.time()))
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        file_path = UPLOAD_FOLDER / unique_filename
        
        # Save file securely
        file.save(file_path)
        
        file_info = {
            "filename": filename,
            "unique_filename": unique_filename,
            "path": str(file_path),
            "type": file.content_type or "application/octet-stream",
            "size": file_size,
            "upload_timestamp": timestamp
        }
        
        print(f"DEBUG: File uploaded successfully: {file_info['filename']} ({file_size} bytes)")
        return file_info
        
    except Exception as e:
        print(f"ERROR: File upload failed: {e}")
        return None

def validate_and_enhance_response(response, original_message, uploaded_file):
    """Validate and enhance chatbot response"""
    try:
        # Ensure response is a dictionary
        if not isinstance(response, dict):
            response = {"message": str(response), "type": "text_response"}
        
        # Ensure required fields exist
        if "message" not in response or not response["message"]:
            response["message"] = "I processed your request, but couldn't generate a proper response. Let me help you differently."
        
        if "type" not in response:
            response["type"] = "general_response"
        
        # Add helpful actions if none exist and it's not an error
        if "actions" not in response and response["type"] not in ["incident_completed", "emergency"]:
            response["actions"] = [
                {"text": "🏠 Main Menu", "action": "continue_conversation", "message": "Show me the main menu"},
                {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"}
            ]
        
        # Add conversation continuity hints for completed incidents
        if response["type"] == "incident_completed":
            if "quick_replies" not in response:
                response["quick_replies"] = [
                    "Report another incident",
                    "View my reports",
                    "What happens next?",
                    "Main menu"
                ]
        
        # Add file context if file was uploaded
        if uploaded_file and "file_context" not in response:
            response["file_context"] = {
                "filename": uploaded_file.get("filename"),
                "size": uploaded_file.get("size"),
                "type": uploaded_file.get("type")
            }
        
        return response
        
    except Exception as e:
        print(f"ERROR: Response validation failed: {e}")
        return {
            "message": "I encountered an issue processing your request, but I'm still here to help!",
            "type": "validation_error",
            "actions": [
                {"text": "🔄 Try Again", "action": "retry"},
                {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"}
            ]
        }

def get_enhanced_fallback_response(message, uploaded_file=None, error_msg=""):
    """Generate intelligent fallback response with enhanced context awareness"""
    try:
        message_lower = message.lower() if message else ""
        
        # Handle file uploads intelligently
        if uploaded_file:
            filename = uploaded_file.get("filename", "")
            file_type = uploaded_file.get("type", "")
            
            if file_type.startswith('image/'):
                return {
                    "message": f"📸 **Image received: {filename}**\n\nI can help you use this image for incident reporting or safety documentation.\n\nWhat would you like to do with this image?",
                    "type": "file_upload_guidance",
                    "actions": [
                        {"text": "🚨 Report Incident with Photo", "action": "continue_conversation", "message": "I want to report an incident with this photo"},
                        {"text": "🛡️ Safety Concern with Photo", "action": "continue_conversation", "message": "I have a safety concern with this photo"},
                        {"text": "📋 Document Safety Issue", "action": "navigate", "url": "/safety-concerns/new"}
                    ],
                    "quick_replies": [
                        "Report incident with photo",
                        "Safety concern with photo",
                        "What can I do with images?"
                    ]
                }
            elif file_type == 'application/pdf':
                return {
                    "message": f"📄 **PDF received: {filename}**\n\nThis could be a Safety Data Sheet or safety documentation.\n\nHow would you like to proceed?",
                    "type": "file_upload_guidance",
                    "actions": [
                        {"text": "📋 Add to SDS Library", "action": "navigate", "url": "/sds/upload"},
                        {"text": "📊 Upload to System", "action": "navigate", "url": "/dashboard"}
                    ]
                }
        
        # Intelligent keyword-based responses
        if any(word in message_lower for word in ["incident", "accident", "injury", "hurt", "damage", "spill", "report"]):
            return {
                "message": "🚨 **I'll help you report this incident properly.**\n\nTo ensure we capture all necessary details for investigation and follow-up, let me guide you through the process step by step.\n\n**What type of incident would you like to report?**",
                "type": "incident_guidance",
                "actions": [
                    {"text": "🩹 Injury/Medical Incident", "action": "continue_conversation", "message": "I need to report a workplace injury"},
                    {"text": "🚗 Vehicle Incident", "action": "continue_conversation", "message": "I need to report a vehicle incident"},
                    {"text": "🌊 Environmental/Spill", "action": "continue_conversation", "message": "I need to report an environmental incident"},
                    {"text": "💔 Property Damage", "action": "continue_conversation", "message": "I need to report property damage"},
                    {"text": "⚠️ Near Miss", "action": "continue_conversation", "message": "I need to report a near miss"},
                    {"text": "📝 Other Incident", "action": "continue_conversation", "message": "I need to report another type of incident"}
                ],
                "quick_replies": [
                    "Workplace injury",
                    "Property damage",
                    "Chemical spill",
                    "Near miss incident",
                    "Vehicle accident"
                ]
            }
        
        elif any(word in message_lower for word in ["safety", "concern", "unsafe", "hazard", "dangerous"]):
            return {
                "message": "🛡️ **Thank you for speaking up about safety!**\n\nEvery safety observation helps create a safer workplace for everyone. I can help you submit this concern properly.\n\n**How would you like to proceed?**",
                "type": "safety_guidance",
                "actions": [
                    {"text": "⚠️ Submit Safety Concern", "action": "navigate", "url": "/safety-concerns/new"},
                    {"text": "📞 Anonymous Report", "action": "navigate", "url": "/safety-concerns/new?anonymous=true"},
                    {"text": "🚨 This is urgent", "action": "continue_conversation", "message": "This is an urgent safety issue"}
                ],
                "quick_replies": [
                    "Submit safety concern",
                    "Report anonymously",
                    "This is urgent",
                    "What types can I report?"
                ]
            }
        
        elif any(word in message_lower for word in ["sds", "chemical", "safety data sheet", "msds", "find"]):
            # Try to extract chemical name
            chemical_name = extract_chemical_name_simple(message)
            base_message = "📄 **I'll help you find Safety Data Sheets.**\n\nOur SDS library contains safety information for workplace chemicals."
            
            if chemical_name:
                base_message += f"\n\n💡 I noticed you mentioned **{chemical_name}** - I can help you find that specific SDS."
            
            return {
                "message": base_message,
                "type": "sds_guidance",
                "actions": [
                    {"text": "🔍 Search SDS Library", "action": "navigate", "url": "/sds"},
                    {"text": "📤 Upload New SDS", "action": "navigate", "url": "/sds/upload"}
                ],
                "quick_replies": [
                    f"Find {chemical_name} SDS" if chemical_name else "Search by chemical name",
                    "Browse all SDS",
                    "Upload new SDS",
                    "How to use QR codes"
                ]
            }
        
        elif any(word in message_lower for word in ["emergency", "911", "fire", "urgent", "help"]):
            return {
                "message": "🚨 **EMERGENCY SUPPORT**\n\n**FOR LIFE-THREATENING EMERGENCIES:**\n🆘 **CALL 911 IMMEDIATELY**\n\n**Site Emergency Contacts:**\n📞 Site Emergency: (555) 123-4567\n🔒 Security: (555) 123-4568\n\n**After ensuring safety, I can help you report the incident.**",
                "type": "emergency_guidance",
                "actions": [
                    {"text": "📞 Call Emergency Services", "action": "external", "url": "tel:911"},
                    {"text": "📝 Report Emergency Incident", "action": "navigate", "url": "/incidents/new?type=emergency"}
                ]
            }
        
        else:
            # General help response
            return {
                "message": "🤖 **I'm your Smart EHS Assistant!**\n\nI can help you with:\n\n🚨 **Report incidents** and accidents step-by-step\n🛡️ **Submit safety concerns** and observations\n📋 **Find safety data sheets** and chemical information\n📊 **Navigate the EHS system** and find what you need\n🔄 **Get guidance** on EHS procedures and policies\n\n**What would you like to work on today?**",
                "type": "general_help",
                "actions": [
                    {"text": "🚨 Report Incident", "action": "continue_conversation", "message": "I need to report a workplace incident"},
                    {"text": "🛡️ Safety Concern", "action": "continue_conversation", "message": "I want to report a safety concern"},
                    {"text": "📋 Find SDS", "action": "continue_conversation", "message": "I need to find a safety data sheet"},
                    {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"}
                ],
                "quick_replies": [
                    "Report an incident",
                    "Safety concern",
                    "Find SDS",
                    "What can you help with?",
                    "Emergency contacts"
                ]
            }
    
    except Exception as e:
        print(f"ERROR: Fallback response generation failed: {e}")
        return {
            "message": "🤖 **I'm here to help with EHS matters.**\n\nUse the navigation menu to access specific features, or try asking me about incidents, safety concerns, or finding SDS documents.",
            "type": "basic_fallback",
            "actions": [
                {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"},
                {"text": "🚨 Report Incident", "action": "navigate", "url": "/incidents/new"}
            ]
        }

def extract_chemical_name_simple(message):
    """Simple chemical name extraction"""
    import re
    # Look for chemical patterns
    patterns = [
        r'(?:sds for|find|need|looking for)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
        r'([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:sds|safety data sheet)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            chemical = match.group(1).strip()
            if len(chemical) > 2 and chemical not in ['the', 'and', 'for', 'with', 'this', 'that']:
                return chemical.title()
    
    return None

@chatbot_bp.route("/chat/reset", methods=["POST"])
def reset_chat():
    """Reset chat session with enhanced state management"""
    try:
        chatbot = get_chatbot()
        if chatbot:
            chatbot._reset_state()
            return jsonify({
                "status": "success",
                "message": "Chat session reset successfully",
                "timestamp": time.time()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Chatbot not available for reset"
            })
    except Exception as e:
        print(f"ERROR: Chat reset failed: {e}")
        return jsonify({
            "status": "error",
            "message": "Reset failed - technical issue"
        })

@chatbot_bp.route("/chat/status")
def chat_status():
    """Get comprehensive chat system status"""
    try:
        chatbot = get_chatbot()
        
        # Test basic functionality
        test_successful = False
        if chatbot:
            try:
                test_response = chatbot.process_message("test system")
                test_successful = isinstance(test_response, dict) and "message" in test_response
            except:
                test_successful = False
        
        return jsonify({
            "timestamp": time.time(),
            "chatbot_available": chatbot is not None,
            "chatbot_functional": test_successful,
            "current_mode": getattr(chatbot, 'current_mode', 'unavailable') if chatbot else 'unavailable',
            "features": {
                "smart_incident_reporting": True,
                "file_upload": True,
                "safety_concerns": True,
                "sds_lookup": True,
                "emergency_detection": True,
                "conversation_continuity": True,
                "slot_validation": True
            },
            "system_info": {
                "python_version": os.sys.version.split()[0],
                "data_directory_exists": os.path.exists("data"),
                "uploads_directory_exists": os.path.exists("static/uploads"),
                "incidents_file_exists": os.path.exists("data/incidents.json")
            },
            "performance": {
                "creation_attempted": _chatbot_creation_attempted,
                "instance_created": _chatbot_instance is not None,
                "test_passed": test_successful
            }
        })
    except Exception as e:
        print(f"ERROR: Status check failed: {e}")
        return jsonify({
            "timestamp": time.time(),
            "chatbot_available": False,
            "error": str(e),
            "status": "system_error"
        }), 500

@chatbot_bp.route("/chat/debug", methods=["GET"])
def chat_debug():
    """Enhanced debug endpoint for comprehensive troubleshooting"""
    try:
        chatbot = get_chatbot()
        
        debug_info = {
            "timestamp": time.time(),
            "chatbot_available": chatbot is not None,
            "chatbot_type": type(chatbot).__name__ if chatbot else None,
            "current_mode": getattr(chatbot, 'current_mode', 'unknown') if chatbot else None,
            "current_context": getattr(chatbot, 'current_context', {}) if chatbot else {},
            "slot_filling_state": getattr(chatbot, 'slot_filling_state', {}) if chatbot else {},
            "conversation_length": len(getattr(chatbot, 'conversation_history', [])) if chatbot else 0,
            "environment": {
                "flask_env": os.environ.get("FLASK_ENV", "production"),
                "python_version": os.sys.version,
                "creation_attempted": _chatbot_creation_attempted
            },
            "file_system": {
                "data_dir_exists": os.path.exists("data"),
                "uploads_dir_exists": os.path.exists("static/uploads"),
                "incidents_file_exists": os.path.exists("data/incidents.json"),
                "sds_dir_exists": os.path.exists("data/sds")
            }
        }
        
        # Test basic functionality with detailed results
        if chatbot:
            try:
                # Test intent classification
                intent_test = chatbot.intent_classifier.classify_intent("I need to report an incident")
                debug_info["tests"] = {
                    "intent_classification": {
                        "success": True,
                        "intent": intent_test[0],
                        "confidence": intent_test[1]
                    }
                }
                
                # Test message processing
                test_response = chatbot.process_message("test message")
                debug_info["tests"]["message_processing"] = {
                    "success": True,
                    "response_type": test_response.get("type", "unknown"),
                    "has_message": bool(test_response.get("message"))
                }
                
            except Exception as e:
                debug_info["tests"] = {
                    "error": str(e),
                    "success": False
                }
        
        return jsonify(debug_info)
    
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": time.time(),
            "status": "debug_failed"
        }), 500

@chatbot_bp.route("/chat/health")
def chat_health():
    """Health check specifically for chat functionality"""
    try:
        chatbot = get_chatbot()
        
        if not chatbot:
            return jsonify({
                "status": "unhealthy",
                "reason": "Chatbot instance not available",
                "timestamp": time.time()
            }), 503
        
        # Quick functional test
        try:
            test_response = chatbot.process_message("health check")
            if not isinstance(test_response, dict) or "message" not in test_response:
                raise Exception("Invalid response format")
        except Exception as e:
            return jsonify({
                "status": "degraded",
                "reason": f"Chatbot functional test failed: {str(e)}",
                "timestamp": time.time()
            }), 503
        
        return jsonify({
            "status": "healthy",
            "chatbot_mode": getattr(chatbot, 'current_mode', 'general'),
            "features_available": True,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "reason": str(e),
            "timestamp": time.time()
        }), 500

# Additional utility endpoints for enhanced chat experience

@chatbot_bp.route("/chat/suggestions")
def get_chat_suggestions():
    """Get contextual chat suggestions"""
    try:
        suggestions = [
            {
                "category": "Incident Reporting",
                "suggestions": [
                    "I need to report a workplace injury",
                    "There was a chemical spill",
                    "Property damage occurred",
                    "I witnessed a near miss"
                ]
            },
            {
                "category": "Safety Concerns",
                "suggestions": [
                    "I have a safety concern",
                    "I observed unsafe conditions",
                    "There's a potential hazard",
                    "I want to report anonymously"
                ]
            },
            {
                "category": "Information Lookup",
                "suggestions": [
                    "Find safety data sheet for acetone",
                    "What are emergency contacts?",
                    "How do I report incidents?",
                    "Show me the dashboard"
                ]
            }
        ]
        
        return jsonify({
            "suggestions": suggestions,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "suggestions": []
        }), 500

@chatbot_bp.route("/chat/examples")
def get_chat_examples():
    """Get example conversations for user guidance"""
    try:
        examples = [
            {
                "title": "Reporting a Workplace Injury",
                "messages": [
                    {"role": "user", "text": "I need to report a workplace injury"},
                    {"role": "assistant", "text": "I'll help you report this injury step by step. First, please describe what happened in detail..."}
                ]
            },
            {
                "title": "Finding Chemical Information",
                "messages": [
                    {"role": "user", "text": "I need the safety data sheet for acetone"},
                    {"role": "assistant", "text": "I'll help you find the acetone SDS. Let me search our library..."}
                ]
            },
            {
                "title": "Reporting Safety Concerns",
                "messages": [
                    {"role": "user", "text": "I have a safety concern about equipment"},
                    {"role": "assistant", "text": "Thank you for speaking up about safety! I can help you submit this concern..."}
                ]
            }
        ]
        
        return jsonify({
            "examples": examples,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "examples": []
        }), 500


# --- Local helpers to attach 5 Whys to incidents (optional) ---
from pathlib import Path
import json, time

DATA_DIR = Path("data")
INCIDENTS_JSON = DATA_DIR / "incidents.json"

def _load_incidents_for_chatbot():
    if INCIDENTS_JSON.exists():
        try:
            return json.loads(INCIDENTS_JSON.read_text())
        except Exception:
            return {}
    return {}

def _save_incidents_for_chatbot(obj: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INCIDENTS_JSON.write_text(json.dumps(obj, indent=2))


@chatbot_bp.post("/five_whys/start")
def five_whys_start():
    """Start a 5-Whys session with a problem statement."""
    problem = (request.form.get("problem") or "").strip()
    user_id = (request.form.get("user_id") or "default_user").strip()
    if not problem:
        return jsonify({"ok": False, "error": "Please provide a problem statement."}), 400
    five_whys_manager.start(user_id, problem)
    return jsonify({"ok": True, "step": 1, "prompt": "Why 1?", "problem": problem})

@chatbot_bp.post("/five_whys/answer")
def five_whys_answer():
    """Append an answer to 5-Whys; return next step or completion and optionally attach to incident."""
    answer = (request.form.get("answer") or "").strip()
    user_id = (request.form.get("user_id") or "default_user").strip()
    incident_id = (request.form.get("incident_id") or "").strip()
    force_complete = (request.form.get("complete") or "").lower() == "true"

    sess = five_whys_manager.answer(user_id, answer)
    if not sess:
        return jsonify({"ok": False, "error": "No active 5-Whys session. Start first."}), 400

    done = five_whys_manager.is_complete(user_id) or force_complete
    if done:
        chain = sess["whys"]
        # attach to incident if provided
        if incident_id:
            items = _load_incidents_for_chatbot()
            rec = items.get(incident_id)
            if rec:
                rec["root_cause_whys"] = chain
                items[incident_id] = rec
                _save_incidents_for_chatbot(items)
        return jsonify({"ok": True, "complete": True, "whys": chain, "message": "5 Whys completed."})
    else:
        next_step = sess["step"] + 1
        return jsonify({"ok": True, "complete": False, "prompt": f"Why {next_step}?", "progress": len(sess["whys"]) })


@chatbot_bp.post("/capa/suggest")
def capa_suggest():
    """Return top CAPA suggestions for a description with confidence and rationale."""
    desc = (request.form.get("description") or "").strip()
    if not desc:
        return jsonify({"ok": False, "error": "Please provide a short description."}), 400
    mgr = CAPAManager()
    res = mgr.suggest_corrective_actions(desc)
    return jsonify({"ok": True, **res})
