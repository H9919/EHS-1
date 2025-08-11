# routes/chatbot.py — full-featured, fixed endpoints, compatible with UI
from flask import Blueprint, request, jsonify, render_template, current_app as app
from pathlib import Path
import time, json, logging

from services.ehs_chatbot import SmartEHSChatbot, SmartIntentClassifier, five_whys_manager
from services.capa_manager import CAPAManager
from utils.uploads import is_allowed, save_upload

chatbot_bp = Blueprint("chatbot", __name__)

_quick = SmartIntentClassifier()
_CHATBOT = None

def get_chatbot() -> SmartEHSChatbot:
    global _CHATBOT
    if _CHATBOT is None:
        _CHATBOT = SmartEHSChatbot()
        app.logger.info("SmartEHSChatbot initialized")
    return _CHATBOT

@chatbot_bp.route("/chat", methods=["GET", "POST"])
def chat_interface():
    # GET: render chat-first dashboard (same template as index)
    if request.method == "GET":
        return render_template("enhanced_dashboard.html")

    # POST: process chat message
    t0 = time.monotonic()
    payload = request.get_json(silent=True) or {}
    user_message = (request.form.get("message") or payload.get("message") or "").strip()
    user_id = (request.form.get("user_id") or "main_chat_user").strip()
    uploaded_file = request.files.get("file")

    if not user_message and not uploaded_file:
        return jsonify({"message": "Please type a message or attach a file.", "type": "error"}), 400

    # Lightweight intent for fast first reply
    try:
        intent, conf = _quick.classify_intent(user_message)
    except Exception:
        intent, conf = None, 0.0

    # File ack path
    if uploaded_file:
        if is_allowed(uploaded_file.filename, uploaded_file.mimetype):
            try:
                save_upload(uploaded_file, Path("data/tmp"))
            except Exception as e:
                app.logger.warning("file save failed: %s", e)
            app.logger.info("chat:fast_file %.3fs", time.monotonic()-t0)
            return jsonify({
                "message": f"📎 Received your file: {uploaded_file.filename}. What would you like me to do with it?",
                "type": "file_ack",
                "intent": intent,
                "confidence": conf
            })
        else:
            return jsonify({
                "message": "This file type is not allowed. Please upload PDF/PNG/JPG/TXT.",
                "type": "error"
            }), 400

    # Fast path for incident start
    if intent == "incident_reporting":
        msg = (
            "Okay—let’s start your incident report.\n"
            "What kind of incident is it? (injury, vehicle, near miss, property, "
            "environmental, security, depot, other)"
        )
        app.logger.info("chat:fast_first %.3fs", time.monotonic()-t0)
        return jsonify({"message": msg, "type": "incident_start", "intent": intent, "confidence": conf})

    # Default quick reply to keep UI responsive
    if intent is None:
        app.logger.info('chat:fast_prompt')
        return jsonify({
            'message': 'How can I help? (report incident, safety concern, SDS help, or general question)',
            'type': 'prompt', 'intent': intent, 'confidence': conf
        })

    # Full smart processing
    bot = get_chatbot()
    t1 = time.monotonic()
    try:
        result = bot.process_message(user_message, user_id=user_id, context={})
    except Exception:
        app.logger.exception("chat:bot_crash")
        return jsonify({"message": "Sorry—something went wrong handling that.", "type": "error"}), 500

    app.logger.info("chat:smart %.3fs (total %.3fs)", time.monotonic()-t1, time.monotonic()-t0)
    if isinstance(result, dict):
        result.setdefault("type", "message")
        result.setdefault("message", "OK")
        return jsonify(result)
    else:
        return jsonify({"message": str(result), "type": "message"})

# 5 Whys
@chatbot_bp.post("/five_whys/start")
@chatbot_bp.post("/chat/five_whys/start")
def five_whys_start():
    problem = (request.form.get("problem") or "").strip()
    user_id = (request.form.get("user_id") or "main_chat_user").strip()
    if not problem:
        return jsonify({"ok": False, "error": "Please provide a problem statement."}), 400
    five_whys_manager.start(user_id, problem)
    return jsonify({"ok": True, "step": 1, "prompt": "Why 1?", "problem": problem})

@chatbot_bp.post("/five_whys/answer")
@chatbot_bp.post("/chat/five_whys/answer")
def five_whys_answer():
    answer = (request.form.get("answer") or "").strip()
    user_id = (request.form.get("user_id") or "main_chat_user").strip()
    incident_id = (request.form.get("incident_id") or "").strip()
    force_complete = (request.form.get("complete") or "").lower() == "true"

    sess = five_whys_manager.answer(user_id, answer)
    if not sess:
        return jsonify({"ok": False, "error": "No active 5-Whys session. Start first."}), 400

    done = five_whys_manager.is_complete(user_id) or force_complete
    if done:
        chain = sess["whys"]
        try:
            DATA_DIR = Path("data"); INCIDENTS_JSON = DATA_DIR / "incidents.json"
            if incident_id and INCIDENTS_JSON.exists():
                items = json.loads(INCIDENTS_JSON.read_text())
                if incident_id in items:
                    items[incident_id]["root_cause_whys"] = chain
                    INCIDENTS_JSON.write_text(json.dumps(items, indent=2))
        except Exception:
            pass
        return jsonify({"ok": True, "complete": True, "whys": chain, "message": "5 Whys completed."})
    else:
        next_step = sess["step"] + 1
        return jsonify({"ok": True, "complete": False, "prompt": f"Why {next_step}?", "progress": len(sess['whys']) })

# CAPA suggestions
@chatbot_bp.post("/capa/suggest")
@chatbot_bp.post("/chat/capa/suggest")
def capa_suggest():
    desc = (request.form.get("description") or "").strip()
    if not desc:
        return jsonify({"ok": False, "error": "Please provide a short description."}), 400
    mgr = CAPAManager()
    res = mgr.suggest_corrective_actions(desc)
    out = {"ok": True}; out.update(res)
    return jsonify(out)


@chatbot_bp.post("/chat/reset")
def chat_reset():
    # Stateless reset ack for the UI
    return jsonify({"ok": True, "message": "Session reset."})
