from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, flash
import os
import random
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

# Import module functions
from moduleA import run_moduleA, sentences as moduleA_sentences
from moduleB import run_moduleB, sentences as moduleB_sentences
from moduleC import run_moduleC, topics
from moduleD import get_quiz, submit_answers

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_audio'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')
app.config['USER_DB'] = os.path.join(os.path.dirname(__file__), 'users_temp.db')

# Create temp directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ===== DATABASE FUNCTIONS =====

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(app.config['USER_DB'])
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db():
    """Initialize user authentication database"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def init_performance_db():
    """Initialize performance tracking database"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            module TEXT NOT NULL,
            question_number INTEGER,
            score REAL,
            max_score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

init_user_db()
init_performance_db()
# ===== USER MANAGEMENT FUNCTIONS =====

def create_user(email, username, password):
    """Create a new user account"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                    (email.lower().strip(), username.strip(), generate_password_hash(password)))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Email already registered"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def verify_user(email, password):
    """Verify user credentials"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, email, username, password_hash FROM users WHERE email = ?", 
                   (email.lower().strip(),))
        row = cur.fetchone()
        if not row:
            return False, "Invalid credentials"
        if not check_password_hash(row["password_hash"], password):
            return False, "Invalid credentials"
        return True, {"id": row["id"], "email": row["email"], "username": row["username"]}
    finally:
        conn.close()


# ===== PERFORMANCE TRACKING FUNCTIONS =====

def save_performance(user_id, session_id, module, question_number, score, max_score):
    """Save performance data for a question"""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_performance (user_id, session_id, module, question_number, score, max_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, session_id, module, question_number, score, max_score))
        conn.commit()
    finally:
        conn.close()


def get_session_report(user_id, session_id):
    """Generate comprehensive performance report"""
    conn = get_db()
    cur = conn.cursor()
    
    # Get all performance data for this session grouped by module
    cur.execute("""
        SELECT module, AVG(score) as avg_score, AVG(max_score) as max_score, COUNT(*) as attempts
        FROM user_performance
        WHERE user_id = ? AND session_id = ?
        GROUP BY module
        ORDER BY module
    """, (user_id, session_id))
    
    results = cur.fetchall()
    conn.close()
    
    report = {
        'modules': [],
        'overall_score': 0,
        'total_questions': 0
    }
    
    total_percentage = 0
    module_count = 0
    
    for row in results:
        percentage = round((row['avg_score'] / row['max_score'] * 100) if row['max_score'] > 0 else 0, 1)
        module_data = {
            'name': row['module'],
            'average_score': round(row['avg_score'], 2),
            'max_score': round(row['max_score'], 2),
            'percentage': percentage,
            'questions_completed': row['attempts']
        }
        report['modules'].append(module_data)
        total_percentage += percentage
        module_count += 1
        report['total_questions'] += row['attempts']
    
    report['overall_score'] = round(total_percentage / module_count if module_count > 0 else 0, 1)
    
    return report


# ===== AUTHENTICATION DECORATOR =====

def login_required(view_func):
    """Decorator to require login for routes"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # For API clients, return 401 JSON. For browser, redirect to login.
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper


# ===== AUTHENTICATION ROUTES =====

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup"""
    if request.method == 'GET':
        return render_template('signup.html')
    
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not email or not username or not password:
        msg = 'All fields are required'
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('signup'))

    ok, err = create_user(email, username, password)
    if not ok:
        if request.is_json:
            return jsonify({'success': False, 'error': err}), 400
        flash(err, 'error')
        return redirect(url_for('signup'))

    if request.is_json:
        return jsonify({'success': True, 'message': 'Signup successful'})
    flash('Signup successful. Please log in.', 'success')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not email or not password:
        msg = 'Email and password are required'
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('login'))

    ok, user = verify_user(email, password)
    if not ok:
        if request.is_json:
            return jsonify({'success': False, 'error': user}), 401
        flash(user, 'error')
        return redirect(url_for('login'))

    session['user_id'] = user['id']
    session['email'] = user['email']
    session['username'] = user['username']
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Login successful'})
    return redirect(url_for('index'))


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """Handle user logout"""
    session.clear()
    if request.is_json or request.method == 'POST':
        return jsonify({'success': True, 'message': 'Logged out'})
    return redirect(url_for('login'))


# ===== PAGE ROUTES =====

@app.route('/')
@login_required
def index():
    """Module A - Read & Speak landing page"""
    # Create a new session ID if not exists
    if 'current_session_id' not in session:
        session['current_session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/moduleB')
@login_required
def moduleB_page():
    """Module B - Listen & Repeat landing page"""
    return render_template('moduleB.html')


@app.route('/moduleC')
@login_required
def moduleC_page():
    """Module C - Topic Speaking landing page"""
    return render_template('moduleC.html')


@app.route('/moduleD')
@login_required
def moduleD_page():
    """Module D - Grammar Quiz landing page"""
    return render_template('moduleD.html')


@app.route('/report')
@login_required
def performance_report():
    """Performance report page"""
    session_id = session.get('current_session_id')
    if not session_id:
        flash('No session data found', 'error')
        return redirect(url_for('index'))
    
    report = get_session_report(session['user_id'], session_id)
    return render_template('report.html', report=report)


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


# ===== API ENDPOINTS - GET CONTENT =====

@app.route('/api/moduleA/sentence', methods=['GET'])
@login_required
def get_moduleA_sentence():
    """Get a random sentence for Module A - Read & Speak"""
    try:
        sentence_id = random.randint(0, len(moduleA_sentences) - 1)
        sentence = moduleA_sentences[sentence_id]
        return jsonify({
            'sentence_id': sentence_id,
            'sentence': sentence,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleA/sentence: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleB/sentence', methods=['GET'])
@login_required
def get_moduleB_sentence():
    """Get a random sentence for Module B - Listen & Repeat"""
    try:
        sentence_id = random.randint(0, len(moduleB_sentences) - 1)
        sentence = moduleB_sentences[sentence_id]
        return jsonify({
            'sentence_id': sentence_id,
            'sentence': sentence,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleB/sentence: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleC/topic', methods=['GET'])
@login_required
def get_moduleC_topic():
    """Get a random topic for Module C - Topic Speaking"""
    try:
        topic_id = random.randint(0, len(topics) - 1)
        topic = topics[topic_id]
        return jsonify({
            'topic_id': topic_id,
            'topic': topic,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleC/topic: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleD/quiz', methods=['GET'])
@login_required
def api_get_quiz():
    """Get a new quiz for Module D"""
    try:
        quiz = get_quiz()
        return jsonify(quiz)
    except Exception as e:
        print(f"Error in moduleD/quiz: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


# ===== API ENDPOINTS - SUBMIT AUDIO/ANSWERS =====

@app.route('/api/moduleA', methods=['POST'])
@login_required
def api_moduleA():
    """Process audio for Module A - Read & Speak"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided', 'success': False}), 400

        file = request.files['audio']
        sentence_id = request.form.get('sentence_id', type=int)

        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400

        if sentence_id is None:
            return jsonify({'error': 'Sentence ID is required', 'success': False}), 400

        filename = secure_filename(f"moduleA_{os.urandom(8).hex()}.wav")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        result = run_moduleA(filepath, sentence_id)

        # Save performance
        save_performance(
            user_id=session['user_id'],
            session_id=session.get('current_session_id'),
            module='Module A - Read & Speak',
            question_number=sentence_id,
            score=result.get('pronunciation_score', 0),
            max_score=100
        )

        # Clean up the file
        if os.path.exists(filepath):
            os.remove(filepath)

        # Map backend field names to frontend expectations
        response = {
            'success': True,
            'score': result.get('pronunciation_score', 0),
            'transcription': result.get('transcribed_text', ''),
            'feedback': result.get('feedback', ''),
            'sentence_id': result.get('sentence_id', sentence_id),
            'expected': result.get('target_sentence', ''),
            'pronunciation_score': result.get('pronunciation_score', 0),
            'fluency_score': result.get('fluency_score', 0),
            'duration_sec': result.get('duration_sec', 0),
            'wps': result.get('wps', 0)
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error in moduleA: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleB', methods=['POST'])
@login_required
def api_moduleB():
    """Process audio for Module B - Listen & Repeat"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided', 'success': False}), 400

        file = request.files['audio']
        sentence_id = request.form.get('sentence_id', type=int)

        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400

        if sentence_id is None:
            return jsonify({'error': 'Sentence ID is required', 'success': False}), 400

        filename = secure_filename(f"moduleB_{os.urandom(8).hex()}.wav")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Call moduleB
        try:
            result = run_moduleB(filepath, sentence_id)
        except TypeError:
            result = run_moduleB(filepath)
            result['sentence_id'] = sentence_id

        # Save performance
        save_performance(
            user_id=session['user_id'],
            session_id=session.get('current_session_id'),
            module='Module B - Listen & Repeat',
            question_number=sentence_id,
            score=result.get('pronunciation_score', result.get('score', 0)),
            max_score=100
        )

        # Clean up the file
        if os.path.exists(filepath):
            os.remove(filepath)

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleB: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleC', methods=['POST'])
@login_required
def api_moduleC():
    """Process audio for Module C - Topic Speaking"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided', 'success': False}), 400

        file = request.files['audio']
        topic_id = request.form.get('topic_id', type=int)

        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400

        if topic_id is None:
            return jsonify({'error': 'Topic ID is required', 'success': False}), 400

        filename = secure_filename(f"moduleC_{os.urandom(8).hex()}.wav")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        result = run_moduleC(filepath)
        result['topic_id'] = topic_id

        # Save performance
        save_performance(
            user_id=session['user_id'],
            session_id=session.get('current_session_id'),
            module='Module C - Topic Speaking',
            question_number=topic_id,
            score=result.get('score', 0),
            max_score=100
        )

        # Clean up the file
        if os.path.exists(filepath):
            os.remove(filepath)

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleC: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleD/submit', methods=['POST'])
@login_required
def api_submit_quiz():
    """Submit quiz answers for Module D"""
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'Invalid request data', 'success': False}), 400

        result = submit_answers(data['answers'])

        # Save performance for each question
        if result.get('review'):
            for item in result['review']:
                save_performance(
                    user_id=session['user_id'],
                    session_id=session.get('current_session_id'),
                    module='Module D - Grammar Quiz',
                    question_number=item.get('question_number', 0),
                    score=100 if item.get('correct') else 0,
                    max_score=100
                )

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleD/submit: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


# ===== APPLICATION INITIALIZATION =====

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
