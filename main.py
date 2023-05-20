from flask import Flask, jsonify
from flask import request
import flask_ngrok
from flasgger import Swagger, LazyJSONEncoder, LazyString, swag_from
import re
import pandas as pd
import sqlite3

app = Flask(__name__)
app.json_encoder = LazyJSONEncoder
swagger_template = dict(
info = {
    'title': LazyString(lambda:'API for Data Cleansing'),
    'version': LazyString(lambda:'1.0.0'),
    'description': LazyString(lambda:'API untuk Cleansing Data'),
    },
    host = LazyString(lambda:request.host)
)
swagger_config = {
    'headers':[],
    'specs':[
        {
            'endpoint': 'docs',
            'route': '/docs.json',
        }
    ],
    'static_url_path':'/flasgger_static',
    'swagger_ui': 'True',
    'specs_route': '/'
}
swagger = Swagger(app,template=swagger_template,config=swagger_config)

def create_table():
    conn = sqlite3.connect('D:\data_jazmi\database_hate.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS cleaning 
                            (
                              text         VARCHAR(255),
                              text_bersih  VARCHAR(255)  
                            );''')
    conn.commit()
    conn.close()



def insert_teks(text,text_bersih):
    conn = sqlite3.connect('D:\data_jazmi\database_hate.db')
    cur = conn.cursor()
    cur.execute('''INSERT INTO cleaning (text, text_bersih) VALUES (?,?)''',(text, text_bersih))

    conn.commit()
    conn.close()



def bersihkan(text):
    text = text.lower()
    replacements = [
            ("(user)",""), #titik, tanda pagar#, dan $$ termasuk not word characters
            ("(rt)",""),
            ("(url)",""),
            (r"https://t.co/\w+"," "),
            (r"\\n",""),
            ("\n",""),
            (r"\\x.."," "),
            (r"#\w+",""),
            ("\W"," "),
            ("( ){2,15}"," ")
            ]
    
    for old, new in replacements:
        text = re.sub(old, new, text)
    
    return text


def setelah_bersih(text):
    text_bersih = bersihkan(text)
    insert_teks(text, text_bersih)


def pembersihan(cleaned):
    #tambahan pembersihan untuk bagian text-processing-file
    cleaned = re.sub(r'(\b[0-1{12}]\b)','',cleaned)
    cleaned = re.sub(r'( ){13}','',cleaned)
    
    return cleaned

#bagian untuk memanggil isi tabel kata alay dan kata kasar
conn = sqlite3.connect('database_hate.db')
call_alay = pd.read_sql_query('SELECT * FROM kamus_alay',conn)
call_kasar = pd.read_sql_query('SELECT * FROM kata_kasar',conn)

alay = dict(zip(call_alay['kata_alay'],call_alay['kata_normal']))

#fungsi untuk mengganti kata alay ke normal
def normalize(text):
    hasil = []
    splitting = text.split(' ')
    for kata in splitting:
        if kata in alay:
            hasil.append(alay[kata])
        else:
            hasil.append(kata)
    
    return ' '.join(hasil)

list_abusive = call_kasar['abusive'].str.lower().tolist()

def sensor(text):
    text = text.lower()
    list_word = text.split()

    hasil = []
    for text in list_word:
        if text in list_abusive:
            text = text.replace(text[-3:],'***')
            hasil.append(text)
        else:
            hasil.append(text)

    return ' '.join(hasil)    

        
#endpoint untuk mencoba saja
@swag_from('docs/text_processing_trial.yml', methods=['POST'])
@app.route('/text-processing-trial',methods=['POST'])
def text_processing_trial():

    text = request.form.get('text')
    text = bersihkan(text)
    text = normalize(text)
    text = sensor(text)    

    return text


#endpoint untuk otomatis insert ke database
@swag_from('docs/text_processing.yml', methods=['POST'])
@app.route('/text-processing',methods=['POST'])
def text_processing():

    text = request.form.get('text')
    text = bersihkan(text)
    text = normalize(text)
    text = sensor(text)
    setelah_bersih(text)

    return text


@swag_from('docs/text_processing_file.yml', methods=['POST'])
@app.route('/text-processing-file',methods=['POST'])
def text_processing_file():

    file = request.files.getlist('file')[0]

    original_text_list = []
    cleaned_text_list = []
    for text in file:
        text = bytes.decode(text, 'latin-1')
        cleaned = bersihkan(text)
        text_bersih = pembersihan(cleaned)

        text_bersih = normalize(text_bersih)
        text_bersih = sensor(text_bersih)
        
        insert_teks(text,text_bersih)
        original_text_list.append(text)
        cleaned_text_list.append(text_bersih)


    with open('original.txt','w') as fo:
        for line in original_text_list[1:]:
            fo.write(line)
            fo.write('\n')

    with open('cleaned_from_original.txt','w') as fo:
        for lines in cleaned_text_list[1:]:
            fo.write(lines)
            fo.write('\n')   

    with open('cleaned_from_original.txt','r') as f:
        cleaned_data = f.read()  


    json_response = {
        'status_code':200,
        'description': 'Teks setelah diproses',
        'data': cleaned_text_list[1:], #baris ini untuk menampilkan hasil dalam bentuk list
        #'data': cleaned_data, #baris ini untuk menampilkan hasil dalam bentuk file I/O
    }

    response = jsonify(json_response)
    return response

#menjalankan flask    
if __name__ == '__main__':
    create_table()
    app.run(debug=True)

#mengecek apakah sudah masuk ke tabel cleaning di database_hate atau belum
#output dari script bawah ini akan muncul setelah menekan ctrl+c untuk keluar dari flask
conn = sqlite3.connect('database_hate.db')

print(pd.read_sql_query('SELECT * FROM cleaning',conn))
#hasilnya atau output akan memunculkan tabel cleaning sebanyak 2 kali
#(masih tidak tahu kenapa bisa 2 kali)
