from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
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

    # 좋아요 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')

    # 조회수 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_ip TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')

    conn.commit()
    conn.close()


@app.route('/')
def index():
    conn = sqlite3.connect('board.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = c.fetchall()
    conn.close()

    # 번호를 추가하여 posts 전달
    numbered_posts = [(idx + 1, *post) for idx, post in enumerate(posts)]

    return render_template('index.html', posts=numbered_posts)


# 새 게시글 작성 페이지
@app.route('/post/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content'].replace('\r\n', '\n')

        conn = sqlite3.connect('board.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (title, content) VALUES (?, ?)", (title, content))
        conn.commit()

        # 방금 삽입한 게시글 ID 가져오기
        post_id = c.lastrowid
        conn.close()

        # 게시글 내용을 분석해 AI 답변 생성
        answer = chatGPT.search_and_generate_answer(content)
        print(answer)  # 디버깅용으로 AI 답변 출력

        if not answer.startswith("정보가"):
            conn2 = sqlite3.connect('board.db')
            conn2.execute(
                'INSERT INTO comments (post_id, content, is_ai) VALUES (?, ?, 1)', 
                (post_id, answer)
            )
            conn2.commit()
            conn2.close()

        return redirect(url_for('index'))

    return render_template('new_post.html')


# 게시글 상세 및 댓글 보기 페이지
@app.route('/post/<int:post_id>', methods=['GET', 'POST', 'DELETE'])
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
                conn2.execute('INSERT INTO comments (post_id, content, parent_id, is_ai) VALUES (?, ?, ?, 1)',
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
    conn.close()

    return render_template('post.html', post=post, comments=structured_comments)


# 좋아요 기능 추가
@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    conn = sqlite3.connect('board.db')
    c = conn.cursor()

    # 게시글이 존재하는지 확인
    c.execute("SELECT id FROM posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # 좋아요 기록 추가
    c.execute("INSERT INTO likes (post_id, user_id) VALUES (?, ?)", (post_id, None))  # 익명 사용자는 user_id가 None
    conn.commit()
    conn.close()

    return jsonify({'message': 'Liked successfully'}), 200


# 조회수 확인 추가
@app.route('/view/<int:post_id>', methods=['POST'])
def record_view(post_id):
    user_ip = request.remote_addr
    conn = sqlite3.connect('board.db')
    c = conn.cursor()

    # 게시글이 존재하는지 확인
    c.execute("SELECT id FROM posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # 동일 IP가 동일 게시글을 최근 5분 내에 조회했는지 확인
    c.execute("""
        SELECT id FROM views 
        WHERE post_id = ? AND user_ip = ? AND created_at > datetime('now', '-5 minutes')
    """, (post_id, user_ip))
    recent_view = c.fetchone()

    if not recent_view:
        # 새로운 조회 기록 추가
        c.execute("INSERT INTO views (post_id, user_ip) VALUES (?, ?)", (post_id, user_ip))
        conn.commit()

    conn.close()
    return jsonify({'message': 'View recorded successfully'}), 200


# 좋아요랑 조회수 값 반환
@app.route('/stats/<int:post_id>', methods=['GET'])
def get_post_stats(post_id):
    conn = sqlite3.connect('board.db')
    c = conn.cursor()

    # 좋아요 수
    c.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
    like_count = c.fetchone()[0]

    # 조회수
    c.execute("SELECT COUNT(*) FROM views WHERE post_id = ?", (post_id,))
    view_count = c.fetchone()[0]

    conn.close()
    return jsonify({'likes': like_count, 'views': view_count}), 200


# 글 삭제
@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    conn = sqlite3.connect('board.db')
    c = conn.cursor()

    # 연관 데이터 삭제
    c.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    c.execute("DELETE FROM likes WHERE post_id = ?", (post_id,))
    c.execute("DELETE FROM views WHERE post_id = ?", (post_id,))
    c.execute("DELETE FROM posts WHERE id = ?", (post_id,))

    conn.commit()
    conn.close()

    return '', 204  # No Content 응답


@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    data = request.get_json()
    post_content = data['content']
    question = data['question']
    try:
       return jsonify({'summary': chatGPT.analyze(post_content, question)})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
