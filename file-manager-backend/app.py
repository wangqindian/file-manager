import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'files.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            size INTEGER,
            parent_id TEXT,
            created_at TEXT,
            modified_at TEXT,
            path TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT,
            created_at TEXT,
            modified_at TEXT,
            path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def dict_from_row(row, columns):
    return dict(zip(columns, row))

def get_file_columns():
    return ['id', 'name', 'type', 'size', 'parent_id', 'created_at', 'modified_at', 'path']

def get_folder_columns():
    return ['id', 'name', 'parent_id', 'created_at', 'modified_at', 'path']

init_db()

@app.route('/api/files', methods=['GET'])
def get_files():
    parent_id = request.args.get('parent_id', None)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if parent_id is None:
        c.execute('SELECT * FROM files WHERE parent_id IS NULL')
    else:
        c.execute('SELECT * FROM files WHERE parent_id = ?', (parent_id,))

    files = [dict_from_row(row, get_file_columns()) for row in c.fetchall()]
    conn.close()

    return jsonify(files)

@app.route('/api/folders', methods=['GET'])
def get_folders():
    parent_id = request.args.get('parent_id', None)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if parent_id is None:
        c.execute('SELECT * FROM folders WHERE parent_id IS NULL')
    else:
        c.execute('SELECT * FROM folders WHERE parent_id = ?', (parent_id,))

    folders = [dict_from_row(row, get_folder_columns()) for row in c.fetchall()]
    conn.close()

    return jsonify(folders)

@app.route('/api/folders/<folder_id>', methods=['GET'])
def get_folder(folder_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
    folder = c.fetchone()
    conn.close()

    if folder is None:
        return jsonify({'error': 'Folder not found'}), 404

    return jsonify(dict_from_row(folder, get_folder_columns()))

@app.route('/api/folders', methods=['POST'])
def create_folder():
    data = request.json
    name = data.get('name')
    parent_id = data.get('parent_id', None)

    if not name:
        return jsonify({'error': 'Folder name is required'}), 400

    folder_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if parent_id:
        c.execute('SELECT path FROM folders WHERE id = ?', (parent_id,))
        parent = c.fetchone()
        if parent:
            path = parent[0] + '/' + name
        else:
            path = '/' + name
    else:
        path = '/' + name

    c.execute('''
        INSERT INTO folders (id, name, parent_id, created_at, modified_at, path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (folder_id, name, parent_id, now, now, path))

    conn.commit()
    conn.close()

    return jsonify({
        'id': folder_id,
        'name': name,
        'parent_id': parent_id,
        'created_at': now,
        'modified_at': now,
        'path': path
    })

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
    c.execute('DELETE FROM files WHERE parent_id = ?', (folder_id,))

    conn.commit()
    affected = c.rowcount
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Folder not found'}), 404

    return jsonify({'message': 'Folder deleted'})

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('SELECT path FROM files WHERE id = ?', (file_id,))
    file = c.fetchone()

    if file and file[0]:
        file_path = os.path.join(UPLOAD_FOLDER, file[0])
        if os.path.exists(file_path):
            os.remove(file_path)

    c.execute('DELETE FROM files WHERE id = ?', (file_id,))

    conn.commit()
    affected = c.rowcount
    conn.close()

    if affected == 0:
        return jsonify({'error': 'File not found'}), 404

    return jsonify({'message': 'File deleted'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    parent_id = request.form.get('parent_id', None)

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    original_filename = file.filename

    filename = f"{file_id}_{original_filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(file_path)

    file_size = os.path.getsize(file_path)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if parent_id:
        c.execute('SELECT path FROM folders WHERE id = ?', (parent_id,))
        parent = c.fetchone()
        if parent:
            path = parent[0] + '/' + original_filename
        else:
            path = '/' + original_filename
    else:
        path = '/' + original_filename

    c.execute('''
        INSERT INTO files (id, name, type, size, parent_id, created_at, modified_at, path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_id, original_filename, 'file', file_size, parent_id, now, now, path))

    conn.commit()
    conn.close()

    return jsonify({
        'id': file_id,
        'name': original_filename,
        'type': 'file',
        'size': file_size,
        'parent_id': parent_id,
        'created_at': now,
        'modified_at': now,
        'path': path
    })

@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT name, path FROM files WHERE id = ?', (file_id,))
    file = c.fetchone()
    conn.close()

    if file is None:
        return jsonify({'error': 'File not found'}), 404

    filename, stored_path = file

    return send_from_directory(
        UPLOAD_FOLDER,
        stored_path.lstrip('/'),
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/rename', methods=['POST'])
def rename_item():
    data = request.json
    item_type = data.get('type')
    item_id = data.get('id')
    new_name = data.get('name')

    if not item_type or not item_id or not new_name:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    now = datetime.now().isoformat()

    if item_type == 'folder':
        c.execute('UPDATE folders SET name = ?, modified_at = ? WHERE id = ?', (new_name, now, item_id))
    else:
        c.execute('UPDATE files SET name = ?, modified_at = ? WHERE id = ?', (new_name, now, item_id))

    conn.commit()
    affected = c.rowcount
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Item not found'}), 404

    return jsonify({'message': 'Renamed successfully'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)