# app.py - Reverse Teaching AI Validator (With Error Detection & Correction)
from flask import Flask, render_template, request, jsonify
from groq import Groq
import os
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Configure Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

class TopicAnalyzer:
    """Analyzes topics to understand their nature and generate appropriate questions"""
    
    @staticmethod
    def analyze_topic(topic):
        topic_lower = topic.lower()
        
        categories = {
            'game': {
                'keywords': ['game', 'chess', 'football', 'soccer', 'basketball', 'poker', 'monopoly', 'video game', 'sport', 'play'],
                'question_focuses': ['rules', 'strategy', 'objectives', 'gameplay', 'tactics', 'scoring'],
                'context': 'This is a game or sport'
            },
            'skill': {
                'keywords': ['playing', 'writing', 'painting', 'coding', 'programming', 'driving', 'cooking', 'singing', 'dancing'],
                'question_focuses': ['techniques', 'learning process', 'practice methods', 'common mistakes', 'mastery'],
                'context': 'This is a skill or ability'
            },
            'historical_event': {
                'keywords': ['war', 'revolution', 'battle', 'election', 'independence', 'empire', 'civilization', 'ancient', 'medieval'],
                'question_focuses': ['causes', 'consequences', 'key figures', 'timeline', 'impact', 'significance'],
                'context': 'This is a historical event or period'
            },
            'scientific_process': {
                'keywords': ['photosynthesis', 'mitosis', 'respiration', 'evolution', 'digestion', 'circulation', 'metabolism'],
                'question_focuses': ['steps', 'mechanisms', 'inputs/outputs', 'purpose', 'conditions', 'variations'],
                'context': 'This is a scientific or biological process'
            },
            'concept': {
                'keywords': ['democracy', 'justice', 'freedom', 'love', 'happiness', 'philosophy', 'theory', 'principle'],
                'question_focuses': ['definition', 'examples', 'applications', 'implications', 'perspectives'],
                'context': 'This is an abstract concept or idea'
            },
            'technology': {
                'keywords': ['smartphone', 'computer', 'internet', 'ai', 'robot', 'software', 'app', 'algorithm'],
                'question_focuses': ['how it works', 'components', 'uses', 'evolution', 'impact', 'future'],
                'context': 'This is technology or a technological system'
            }
        }
        
        for category, info in categories.items():
            if any(keyword in topic_lower for keyword in info['keywords']):
                return {
                    'category': category,
                    'question_focuses': info['question_focuses'],
                    'context': info['context']
                }
        
        return {
            'category': 'general',
            'question_focuses': ['definition', 'examples', 'how it works', 'importance', 'applications'],
            'context': 'This is a general topic'
        }

class ConversationMemory:
    """Manages full conversation memory and context"""
    def __init__(self):
        self.full_conversation = []
        self.asked_questions = set()
        self.last_ai_question = ""
        self.conversation_depth = 0
        self.topic_analysis = None
        self.concepts_covered = set()
        # NEW: Error correction tracking
        self.correction_mode = False
        self.incorrect_concepts = []
        self.verification_questions_asked = 0
        self.verification_answers_correct = 0
        self.current_correction_topic = ""
        
    def set_topic_analysis(self, analysis):
        self.topic_analysis = analysis
        
    def enter_correction_mode(self, incorrect_concept):
        """Enter correction mode for a specific incorrect concept"""
        self.correction_mode = True
        self.current_correction_topic = incorrect_concept
        self.verification_questions_asked = 0
        self.verification_answers_correct = 0
        self.incorrect_concepts.append(incorrect_concept)
        print(f"🔴 Entering correction mode for: {incorrect_concept}")
        
    def exit_correction_mode(self):
        """Exit correction mode and return to normal teaching"""
        self.correction_mode = False
        self.current_correction_topic = ""
        self.verification_questions_asked = 0
        self.verification_answers_correct = 0
        print(f"✅ Exiting correction mode - understanding verified!")
        
    def add_exchange(self, teacher_input, ai_response):
        self.full_conversation.append({
            "role": "user",
            "content": f"Teacher: {teacher_input}"
        })
        self.full_conversation.append({
            "role": "assistant", 
            "content": ai_response
        })
        
        if self.is_question(ai_response):
            self.asked_questions.add(ai_response.lower()[:60])
            self.last_ai_question = ai_response
            
        # Extract key concepts from teacher's input
        if len(teacher_input.split()) > 5:
            key_words = [word.lower() for word in teacher_input.split() if len(word) > 4]
            self.concepts_covered.update(key_words[:3])
            
        self.conversation_depth += 1
        
    def is_question(self, text):
        return '?' in text or any(text.lower().startswith(word) for word in 
                                ['what', 'how', 'why', 'when', 'where', 'which', 'who'])
        
    def get_conversation_for_api(self, system_prompt):
        messages = [{"role": "system", "content": system_prompt}]
        recent_history = self.full_conversation[-8:] if len(self.full_conversation) > 8 else self.full_conversation
        messages.extend(recent_history)
        return messages
        
    def has_asked_similar(self, potential_question):
        question_signature = potential_question.lower()[:60]
        for asked in self.asked_questions:
            if len(set(question_signature.split()) & set(asked.split())) >= 4:
                return True
        return False
        
    def reset(self):
        self.full_conversation = []
        self.asked_questions = set()
        self.last_ai_question = ""
        self.conversation_depth = 0
        self.topic_analysis = None
        self.concepts_covered = set()
        # Reset correction mode
        self.correction_mode = False
        self.incorrect_concepts = []
        self.verification_questions_asked = 0
        self.verification_answers_correct = 0
        self.current_correction_topic = ""

class TeachingSession:
    def __init__(self):
        self.conversation_memory = ConversationMemory()
        self.teaching_quality_scores = []
        self.topic = ""
        self.ai_confusion_level = 1
        self.session_start = time.time()
        self.exchanges_count = 0
        
    def add_exchange(self, student_explanation, ai_response, quality_score):
        self.conversation_memory.add_exchange(student_explanation, ai_response)
        self.teaching_quality_scores.append(quality_score)
        self.exchanges_count += 1
        
    def reset_session(self):
        self.conversation_memory.reset()
        self.teaching_quality_scores = []
        self.topic = ""
        self.ai_confusion_level = 1
        self.session_start = time.time()
        self.exchanges_count = 0

# Global session
current_session = TeachingSession()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_teaching', methods=['POST'])
def start_teaching():
    try:
        data = request.get_json()
        topic = data.get('topic', 'general concept').strip()
        
        if not topic:
            return jsonify({'error': 'Please provide a topic to teach'}), 400
        
        current_session.reset_session()
        current_session.topic = topic
        
        topic_analysis = TopicAnalyzer.analyze_topic(topic)
        current_session.conversation_memory.set_topic_analysis(topic_analysis)
        
        print(f"Topic '{topic}' analyzed as: {topic_analysis['category']}")
        
        ai_response = generate_response(
            f"I want to learn about {topic}", 
            is_introduction=True
        )
        
        return jsonify({
            'ai_response': ai_response,
            'session_started': True,
            'topic': topic,
            'confusion_level': current_session.ai_confusion_level
        })
        
    except Exception as e:
        print(f"Error starting teaching session: {e}")
        return jsonify({'error': 'Failed to start teaching session'}), 500

@app.route('/teach_step', methods=['POST'])
def teach_step():
    try:
        data = request.get_json()
        student_explanation = data.get('explanation', '').strip()
        
        if not student_explanation:
            return jsonify({'error': 'Please provide an explanation'}), 400
        
        if is_inappropriate_response(student_explanation):
            return jsonify({
                'ai_response': "That's not helpful. Could you explain the concept respectfully?",
                'quality_score': 0.1,
                'session_progress': get_session_progress(),
                'exchanges_count': current_session.exchanges_count
            })
        
        memory = current_session.conversation_memory
        
        # Check if we're in correction mode
        if memory.correction_mode:
            # Handle verification in correction mode
            ai_response, quality_score = handle_correction_mode(student_explanation)
        else:
            # Normal mode: check for errors first
            error_result = detect_factual_errors(student_explanation)
            
            if error_result['has_errors']:
                # Switch to correction mode
                memory.enter_correction_mode(error_result['incorrect_concept'])
                ai_response = generate_correction_response(error_result)
                quality_score = 0.2  # Low score for incorrect explanation
            else:
                # No errors, continue normally
                quality_score = assess_teaching_quality(student_explanation)
                ai_response = generate_response(student_explanation, is_introduction=False)
        
        # Add exchange to session memory
        current_session.add_exchange(student_explanation, ai_response, quality_score)
        
        # Dynamic difficulty adjustment (only if not in correction mode)
        if not memory.correction_mode:
            adjust_confusion_level(quality_score)
        
        return jsonify({
            'ai_response': ai_response,
            'quality_score': quality_score,
            'session_progress': get_session_progress(),
            'exchanges_count': current_session.exchanges_count
        })
        
    except Exception as e:
        print(f"Error in teach_step: {e}")
        return jsonify({'error': 'Failed to process teaching step'}), 500

@app.route('/reset_session', methods=['POST'])
def reset_session():
    try:
        current_session.reset_session()
        return jsonify({'status': 'success', 'message': 'Session reset successfully'})
    except Exception as e:
        print(f"Error resetting session: {e}")
        return jsonify({'error': 'Failed to reset session'}), 500

def detect_factual_errors(explanation):
    """Use Groq to detect factual errors in student explanations"""
    
    if len(explanation.split()) < 8:  # Skip very short responses
        return {'has_errors': False}
    
    topic = current_session.topic
    
    system_prompt = f"""You are an expert fact-checker evaluating a student's explanation about {topic}.

Your job is to identify if there are any FACTUAL ERRORS in their explanation.

CRITICAL RULES:
- Only flag CLEAR FACTUAL ERRORS, not incomplete explanations
- Ignore minor wording issues or simplifications
- Focus on scientifically/factually incorrect statements
- If explanation is just incomplete or basic, that's NOT an error

Respond with EXACTLY this JSON format:
{{"has_errors": true/false, "incorrect_concept": "specific wrong concept if any", "correct_explanation": "brief correct version if error found"}}

Examples:
- "Plants eat sunlight" → {{"has_errors": true, "incorrect_concept": "plants eating sunlight", "correct_explanation": "Plants convert sunlight into chemical energy through photosynthesis"}}
- "Photosynthesis uses sunlight" → {{"has_errors": false}}"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Student explanation about {topic}: '{explanation}'"}
            ],
            max_tokens=150,
            temperature=0.3  # Low temperature for consistent fact-checking
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON response
        try:
            result = json.loads(result_text)
            if 'has_errors' in result:
                return result
        except json.JSONDecodeError:
            print(f"Failed to parse fact-check JSON: {result_text}")
        
    except Exception as e:
        print(f"Error in fact-checking: {e}")
    
    # Fallback: assume no errors if fact-checking fails
    return {'has_errors': False}

def generate_correction_response(error_result):
    """Generate a response that corrects the error and provides correct explanation"""
    
    topic = current_session.topic
    incorrect_concept = error_result.get('incorrect_concept', 'that concept')
    correct_explanation = error_result.get('correct_explanation', 'the correct explanation')
    
    correction_templates = [
        f"Actually, I need to correct something about {incorrect_concept}! {correct_explanation}. Let me ask you: can you explain back to me how {topic} actually works based on this correction?",
        
        f"Hold on! There's a small error with {incorrect_concept}. Here's what actually happens: {correct_explanation}. Now, based on this correction, what do you think is the key process in {topic}?",
        
        f"I want to help clarify something! {incorrect_concept} isn't quite right. The correct explanation is: {correct_explanation}. To make sure you understand, can you tell me what the main steps of {topic} are now?"
    ]
    
    return random.choice(correction_templates)

def handle_correction_mode(student_response):
    """Handle student responses during correction/verification mode"""
    
    memory = current_session.conversation_memory
    memory.verification_questions_asked += 1
    
    # Check if their response shows understanding
    understanding_result = assess_understanding(student_response, memory.current_correction_topic)
    
    if understanding_result['shows_understanding']:
        memory.verification_answers_correct += 1
        
        # If they've shown understanding (2+ correct responses or 1 very good one)
        if (memory.verification_answers_correct >= 2 or 
            understanding_result['confidence'] >= 0.8):
            
            memory.exit_correction_mode()
            
            # Generate encouraging response and return to normal teaching
            response = f"Perfect! You've got it now! {understanding_result['encouragement']} Let me continue with a new question about {current_session.topic}."
            
            # Add normal follow-up question
            follow_up = generate_response("corrected understanding verified", is_introduction=False)
            response += f" {follow_up}"
            
            return response, 0.8  # Good score for corrected understanding
    
    # Still need more verification
    verification_response = generate_verification_question(memory.current_correction_topic, memory.verification_questions_asked)
    return verification_response, 0.4

def assess_understanding(response, correction_topic):
    """Assess if student's response shows they understand the corrected concept"""
    
    if len(response.split()) < 3:
        return {'shows_understanding': False, 'confidence': 0.1}
    
    try:
        system_prompt = f"""You are assessing if a student understood a correction about "{correction_topic}".

Respond with EXACTLY this JSON format:
{{"shows_understanding": true/false, "confidence": 0.0-1.0, "encouragement": "brief encouraging comment"}}

High understanding = uses correct terminology, shows grasp of concept
Low understanding = still confused, incorrect facts, vague response"""
        
        api_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Student response: '{response}'"}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        result_text = api_response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        if all(key in result for key in ['shows_understanding', 'confidence']):
            return result
            
    except Exception as e:
        print(f"Error assessing understanding: {e}")
    
    # Fallback assessment
    return {
        'shows_understanding': len(response.split()) > 10,
        'confidence': 0.5,
        'encouragement': "Good effort!"
    }

def generate_verification_question(correction_topic, question_number):
    """Generate questions to verify understanding of corrected concept"""
    
    topic = current_session.topic
    
    if question_number == 1:
        templates = [
            f"Great! Now can you explain to me how {correction_topic} actually works in {topic}?",
            f"Perfect! So based on that correction, what's the key thing that happens with {correction_topic} during {topic}?",
            f"Excellent! Now tell me, what role does {correction_topic} play in the process of {topic}?"
        ]
    else:
        templates = [
            f"I want to make sure this is clear - can you give me an example of {correction_topic} in {topic}?",
            f"Let me ask differently - what would happen if {correction_topic} didn't work properly during {topic}?",
            f"One more check - why is {correction_topic} important for {topic}?"
        ]
    
    return random.choice(templates)

def is_teacher_asking_question(teacher_input):
    """Detect if teacher is asking the AI a clarifying question"""
    teacher_lower = teacher_input.lower().strip()
    
    if teacher_input.strip().endswith('?'):
        return True
    
    question_starters = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'can you', 'could you']
    if any(teacher_lower.startswith(starter) for starter in question_starters):
        return True
    
    clarification_patterns = ['what kind of', 'what type of', 'like what', 'such as what', 'for example']
    if any(pattern in teacher_lower for pattern in clarification_patterns):
        return True
        
    return False

def generate_response(teacher_input, is_introduction=False):
    """Generate appropriate response based on current mode"""
    
    memory = current_session.conversation_memory
    
    # If in correction mode, this shouldn't be called (handled separately)
    if memory.correction_mode:
        return "I'm focusing on understanding the correction first!"
    
    # Normal ChatGPT-style response generation
    depth = memory.conversation_depth
    topic_analysis = memory.topic_analysis
    quality_level = current_session.ai_confusion_level
    
    teacher_is_asking = is_teacher_asking_question(teacher_input) and not is_introduction
    
    if teacher_is_asking:
        system_prompt = f"""You are an enthusiastic student learning about {current_session.topic}.

The teacher asked you a clarifying question about: "{memory.last_ai_question}"

Answer their question helpfully, then ask ONE follow-up question about {current_session.topic}. Be enthusiastic and curious."""
        
    elif is_introduction:
        category = topic_analysis['category'] if topic_analysis else 'general'
        system_prompt = f"""You are an excited student who wants to learn about {current_session.topic}.

TOPIC TYPE: {category}

Ask ONE enthusiastic opening question that shows genuine curiosity about {current_session.topic}. Be conversational and excited."""
        
    else:
        difficulty_instructions = {
            1: "Ask basic, foundational questions",
            2: "Ask detailed questions about how things work", 
            3: "Ask sophisticated questions about applications and complex scenarios"
        }
        
        system_prompt = f"""You are an enthusiastic student learning about {current_session.topic}. 

Exchange #{depth}, Difficulty level: {quality_level}/3

{difficulty_instructions[quality_level]}. Ask ONE question that builds on their latest explanation. Reference something specific they just said. Be excited about learning.

Never repeat questions you've asked before."""
    
    messages = memory.get_conversation_for_api(system_prompt)
    
    if teacher_is_asking:
        messages.append({
            "role": "user", 
            "content": f"""Teacher asked: "{teacher_input}"

Answer their question, then ask ONE follow-up about {current_session.topic}."""
        })
    else:
        messages.append({
            "role": "user", 
            "content": f"""Teacher explained: "{teacher_input}"

Ask ONE enthusiastic question at difficulty level {quality_level}."""
        })
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=120,
            temperature=0.9,
            top_p=0.95
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        if not teacher_is_asking and memory.has_asked_similar(ai_response) and depth > 0:
            return get_fallback_response(teacher_input, depth, teacher_is_asking, quality_level)
            
        return ai_response
        
    except Exception as e:
        print(f"Error generating response: {e}")
        return get_fallback_response(teacher_input, depth, teacher_is_asking, quality_level)

def get_fallback_response(teacher_input, depth, teacher_is_asking, quality_level):
    """Generate fallback responses when API fails"""
    
    topic = current_session.topic
    
    if teacher_is_asking:
        fallbacks = [
            f"I meant the key aspects of {topic}! What's the most important part?",
            f"The main elements that make {topic} work! Which one should I focus on?",
            f"Let me clarify - I was curious about how {topic} actually functions!"
        ]
    else:
        if quality_level == 1:
            fallbacks = [
                f"That's fascinating! What's the main purpose of {topic}?",
                f"Wow! How does {topic} actually work?",
                f"Interesting! What makes {topic} happen?"
            ]
        elif quality_level == 2:
            fallbacks = [
                f"Great explanation! How do the different parts of {topic} connect?",
                f"That's helpful! What controls how {topic} works?",
                f"I see! What happens if conditions change in {topic}?"
            ]
        else:
            fallbacks = [
                f"Excellent! What are some real-world applications of {topic}?",
                f"Amazing! How has {topic} evolved over time?",
                f"Brilliant! How does {topic} compare to similar processes?"
            ]
    
    return random.choice(fallbacks)

def is_inappropriate_response(text):
    inappropriate_words = ['idiot', 'stupid', 'dumb', 'shut up', 'moron']
    return any(word in text.lower() for word in inappropriate_words)

def assess_teaching_quality(explanation):
    if not explanation or len(explanation) < 5:
        return 0.1
    
    if is_teacher_asking_question(explanation) and len(explanation.split()) <= 6:
        return 0.4
    
    quality_indicators = {
        'detailed': len(explanation.split()) >= 12,
        'uses_examples': any(word in explanation.lower() for word in ['example', 'like', 'such as']),
        'explains_reasoning': any(word in explanation.lower() for word in ['because', 'since', 'reason']),
        'step_by_step': any(word in explanation.lower() for word in ['first', 'then', 'step']),
        'engaging': any(word in explanation.lower() for word in ['you', 'imagine'])
    }
    
    base_score = sum(quality_indicators.values()) / len(quality_indicators)
    
    if len(explanation.split()) > 25:
        base_score += 0.2
    
    return round(min(base_score, 1.0), 2)

def adjust_confusion_level(quality_score):
    current_level = current_session.ai_confusion_level
    
    if quality_score >= 0.75 and current_session.exchanges_count >= 2:
        current_session.ai_confusion_level = min(3, current_level + 1)
        if current_session.ai_confusion_level > current_level:
            print(f"🔥 AI difficulty increased to level {current_session.ai_confusion_level}!")
    
    elif quality_score <= 0.35 and current_session.exchanges_count >= 4:
        recent_scores = current_session.teaching_quality_scores[-3:]
        if all(score <= 0.4 for score in recent_scores):
            current_session.ai_confusion_level = max(1, current_level - 1)

def get_session_progress():
    if not current_session.teaching_quality_scores:
        return {
            'average_quality': 0,
            'exchanges': 0,
            'improvement_trend': 'neutral',
            'confusion_level': current_session.ai_confusion_level,
            'session_duration': 0,
            'correction_mode': current_session.conversation_memory.correction_mode
        }
    
    avg_quality = sum(current_session.teaching_quality_scores) / len(current_session.teaching_quality_scores)
    
    if len(current_session.teaching_quality_scores) >= 3:
        recent_avg = sum(current_session.teaching_quality_scores[-2:]) / 2
        early_avg = sum(current_session.teaching_quality_scores[:2]) / 2
        
        if recent_avg > early_avg + 0.2:
            trend = 'improving'
        elif recent_avg < early_avg - 0.2:
            trend = 'declining'  
        else:
            trend = 'stable'
    else:
        trend = 'neutral'
    
    duration = (time.time() - current_session.session_start) / 60
    
    return {
        'average_quality': round(avg_quality, 2),
        'exchanges': current_session.exchanges_count,
        'improvement_trend': trend,
        'confusion_level': current_session.ai_confusion_level,
        'session_duration': round(duration, 1),
        'latest_score': current_session.teaching_quality_scores[-1] if current_session.teaching_quality_scores else 0,
        'correction_mode': current_session.conversation_memory.correction_mode,
        'corrections_made': len(current_session.conversation_memory.incorrect_concepts)
    }

if __name__ == '__main__':
    print("🚀 Starting GROQ-POWERED Reverse Teaching AI (WITH ERROR CORRECTION)...")
    print("🔗 Open your browser to: http://localhost:5000") 
    print("⚡ Using Groq's Llama 3.1 8B Instant model!")
    print("🤩 Enthusiastic AI student with dynamic difficulty!")
    print("🔍 NEW: Factual error detection and correction!")
    print("📚 NEW: Understanding verification system!")
    
    if not os.getenv('GROQ_API_KEY'):
        print("❌ WARNING: GROQ_API_KEY not found in environment variables!")
        print("   Create a .env file with: GROQ_API_KEY=your_groq_key_here")
    else:
        print("✅ Groq API key found")
    
    app.run(debug=True, host='0.0.0.0', port=5000)