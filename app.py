from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import subprocess
from werkzeug.utils import secure_filename
import shutil
from pathlib import Path

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'  # セッション管理用のシークレットキー
app.config['UPLOAD_FOLDER'] = 'source'  # アップロード先フォルダ
app.config['OUTPUT_FOLDER'] = 'output'  # 出力先フォルダ
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大アップロードサイズ（16MB）

# 許可するファイル拡張子
ALLOWED_EXTENSIONS = {'jpeg', 'jpg'}

def allowed_file(filename):
    """ファイルの拡張子が許可されているかチェックする"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """トップページを表示"""
    # sourceディレクトリのファイル一覧を取得
    files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        files = sorted([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                 if allowed_file(f) and os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))])
    
    # 出力動画ファイルの存在確認
    output_files = []
    if os.path.exists(app.config['OUTPUT_FOLDER']):
        output_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) 
                      if f.endswith('.mp4') and os.path.isfile(os.path.join(app.config['OUTPUT_FOLDER'], f))]
    
    return render_template('index.html', files=files, output_files=output_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロード処理"""
    if 'files[]' not in request.files:
        flash('ファイルが選択されていません')
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    
    # アップロードフォルダが存在しない場合は作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    successful_uploads = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            successful_uploads += 1
    
    if successful_uploads > 0:
        flash(f'{successful_uploads}個のファイルがアップロードされました')
    else:
        flash('アップロードできませんでした。JPEGファイルのみ対応しています。')
    
    return redirect(url_for('index'))

@app.route('/generate_video', methods=['POST'])
def generate_video():
    """動画生成処理"""
    try:
        # 出力フォルダが存在しない場合は作成
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        # 既存のソースファイル数を確認
        source_dir = app.config['UPLOAD_FOLDER']
        file_count = len([f for f in os.listdir(source_dir) 
                        if allowed_file(f) and os.path.isfile(os.path.join(source_dir, f))])
        
        if file_count == 0:
            flash('ソース画像がありません。先に画像をアップロードしてください。')
            return redirect(url_for('index'))
        
        # リネーム処理（連番に）
        files = sorted([f for f in os.listdir(source_dir) 
                       if allowed_file(f) and os.path.isfile(os.path.join(source_dir, f))])
        
        for i, filename in enumerate(files, start=1):
            old_path = os.path.join(source_dir, filename)
            new_filename = f"image_{i:02}.jpeg"
            new_path = os.path.join(source_dir, new_filename)
            
            # 既に同名ファイルがある場合は上書き
            if old_path != new_path and os.path.exists(new_path):
                os.remove(new_path)
            
            if old_path != new_path:
                shutil.copy2(old_path, new_path)
        
        # 環境変数の設定とexecute.pyの実行
        env_vars = os.environ.copy()
        env_vars['END_IMAGE_NUMBER'] = str(file_count)
        
        # フォームデータから環境変数を設定
        for key in request.form:
            if request.form[key] and request.form[key].strip():
                env_vars[key] = request.form[key]
        
        result = subprocess.run(['python', 'execute.py'], env=env_vars, 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            flash('動画が正常に生成されました')
        else:
            flash(f'動画生成中にエラーが発生しました: {result.stderr}')
        
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/clear_files', methods=['POST'])
def clear_files():
    """ソースディレクトリのファイルをクリア"""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        flash('全てのソースファイルが削除されました')
    except Exception as e:
        flash(f'ファイル削除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    """動画ファイルのダウンロード"""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/preview/<filename>')
def preview_image(filename):
    """画像プレビュー"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/video/<filename>')
def serve_video(filename):
    """動画ファイルの配信"""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    # アップロードフォルダと出力フォルダが存在しない場合は作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000) 