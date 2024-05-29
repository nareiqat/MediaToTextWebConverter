from flask import Flask, render_template, request, redirect, url_for, send_file
import os
from pydub import AudioSegment
import whisper
import shutil
from fpdf import FPDF

app = Flask(__name__)

# Set the folder to save uploaded files
UPLOAD_FOLDER = 'uploads'
TRANSCRIPTION_FOLDER = 'transcriptions'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSCRIPTION_FOLDER'] = TRANSCRIPTION_FOLDER

# Ensure the upload and transcription folders exist
for folder in [UPLOAD_FOLDER, TRANSCRIPTION_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Allowed extensions
ALLOWED_EXTENSIONS = {'mp4', 'wav', 'mp3', 'm4a', 'flac', 'aac', 'ogg', 'wma', 'webm', 'mkv', 'avi', 'mov'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clear_folders(*folders):
    for folder1 in folders:
        for filename in os.listdir(folder1):
            file_path = os.path.join(folder1, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')


def save_transcription(transcription, format):
    if format == 'txt':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.txt')
        with open(file_path, 'w', encoding='utf-8') as f:  # Specify encoding as utf-8
            f.write(transcription)
    elif format == 'pdf':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.pdf')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        # pdf.set_font("Arial", size=12)
        pdf.add_font('NotoSans', '', './fonts/NotoSans.ttf', uni=True)
        pdf.set_font('NotoSans', '', 14)
        pdf.multi_cell(0, 10, transcription)
        pdf.output(file_path)
    elif format == 'srt':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.srt')
        with open(file_path, 'w', encoding='utf-8') as f:  # Specify encoding as utf-8
            f.write(transcription_to_srt(transcription))
    return file_path


def transcription_to_srt(transcription):
    # Mock SRT conversion - replace this with actual timestamp logic if available
    lines = transcription.split('\n')
    srt_content = ''
    for i, line in enumerate(lines):
        start_time = f"00:00:{i * 5:02d},000"
        end_time = f"00:00:{(i + 1) * 5:02d},000"
        srt_content += f"{i + 1}\n{start_time} --> {end_time}\n{line}\n\n"
    return srt_content


@app.route('/')
def index():
    return render_template('index.html', show_reset_button=False)


@app.route('/upload', methods=['POST'])
def upload_file():
    # Clear the upload folder after processing
    clear_folders(app.config['UPLOAD_FOLDER'], app.config['TRANSCRIPTION_FOLDER'])
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Convert the file to WAV
        audio = AudioSegment.from_file(file_path)
        wav_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.wav')
        audio.export(wav_path, format='wav')

        # Transcribe audio to text using Whisper
        try:
            model = whisper.load_model("base")
            result = model.transcribe(wav_path, fp16=False)
            transcription = result['text']
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            transcription = "Error: Unable to transcribe audio"

        # Save transcription in different formats
        txt_file_path = save_transcription(transcription, 'txt')
        pdf_file_path = save_transcription(transcription, 'pdf')
        srt_file_path = save_transcription(transcription, 'srt')

        return render_template('index.html', transcription=transcription, txt_file_path=txt_file_path,
                               pdf_file_path=pdf_file_path, srt_file_path=srt_file_path, show_reset_button=True)
    else:
        return 'File type not allowed'


@app.route('/download/<file_format>')
def download_file(file_format):
    if file_format == 'txt':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.txt')
    elif file_format == 'pdf':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.pdf')
    elif file_format == 'srt':
        file_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], 'transcription.srt')
    else:
        return 'Invalid format'
    return send_file(file_path, as_attachment=True)


@app.route('/clear_folders')
def clear_folders_route():
    clear_folders(app.config['UPLOAD_FOLDER'], app.config['TRANSCRIPTION_FOLDER'])
    return 'Folders cleared successfully'


if __name__ == '__main__':
    app.run(debug=True)
