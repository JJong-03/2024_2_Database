from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import openai
import langchain
from GptApi import GptApi

app = Flask(__name__)
chatGPT = GptApi()

# 데이터베이스 초기화 함수
def init_db():
    conn = sqlite3.connect('board.db')
    cursor = conn.cursor()

    # 게시글 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 댓글 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_ai INTEGER DEFAULT 0,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            FOREIGN KEY (parent_id) REFERENCES comments (id)
        )
    ''')

    conn.commit()
    conn.close()
    
    
@app.route('/')
def index():
    conn = sqlite3.connect('board.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    posts = c.fetchall()
    conn.close()
    return render_template('index.html', posts=posts)    

# 새 게시글 작성 페이지
@app.route('/post/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content'].replace('\r\n', '\\n')

        conn = sqlite3.connect('board.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (title, content) VALUES (?, ?)", (title, content))
        conn.commit()
        conn.close()
        answer = chatGPT.search_and_generate_answer(content)
        print(answer)
        if not answer.startswith("정보가"):
            print(c.lastrowid)
            conn2 = sqlite3.connect('board.db')
            conn2.execute('INSERT INTO comments (post_id, content,is_ai) VALUES (?, ?,1)',(c.lastrowid, answer))
            conn2.commit()
            conn2.close()
        return redirect(url_for('index'))
    return render_template('new_post.html')

# 게시글 상세 및 댓글 보기 페이지
@app.route('/post/<int:post_id>', methods=['GET', 'POST','DELETE'])
def post(post_id):
    conn = sqlite3.connect('board.db')

    if request.method == 'POST':
        content = request.form['content']
        parent_id = request.form.get('parent_id')

        if parent_id:
            conn.execute('INSERT INTO comments (post_id, content, parent_id) VALUES (?, ?, ?)',
                         (post_id, content, parent_id))
            conn.commit()
            conn.close()
        else:
            c = conn.cursor()
            c.execute('INSERT INTO comments (post_id, content) VALUES (?, ?)',
                         (post_id, content))
            conn.commit()
            conn.close()
            answer = chatGPT.search_and_generate_answer(content)
            print(answer)
            if not answer.startswith("정보가"):
                conn2 = sqlite3.connect('board.db')
                conn2.execute('INSERT INTO comments (post_id, content, parent_id,is_ai) VALUES (?, ?, ?,1)',
                             (post_id, answer, c.lastrowid))
                conn2.commit()
                conn2.close()
        return redirect(url_for('post', post_id=post_id))
    post = conn.cursor().execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()



    comments = conn.cursor().execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at', (post_id,)).fetchall()

    # 댓글과 대댓글을 구조화하기
    structured_comments = {}
    for comment in comments:
        if comment[3] not in structured_comments:  # parent_id
            structured_comments[comment[3]] = []
        structured_comments[comment[3]].append(comment)
    print(structured_comments)
    conn.close()
    return render_template('post.html', post=post, comments=structured_comments)

@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    data = request.get_json()
    post_content = data['content']
    question = data['question']
    try:
       return jsonify({'summary':chatGPT.analyze(post_content, question)})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)