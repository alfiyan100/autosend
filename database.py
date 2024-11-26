from pymongo import MongoClient

# URL koneksi MongoDB
mongo_url = 'mongodb+srv://alfiyanaw:alfiyan100@cluster0.duveelu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'

# Buat klien MongoDB dan pilih database serta koleksi
mongo_client = MongoClient(mongo_url)
db = mongo_client['userbot_db']
media_collection = db['media']
temp_media_collection = db['temp_media']

def save_media(file_id, file_type, file_date, file_path):
    media_collection.insert_one({
        'file_id': file_id,
        'file_type': file_type,
        'file_date': file_date,
        'file_path': file_path
    })

def get_all_media():
    return list(media_collection.find())

def save_temp_media(file_id, file_type, file_date, file_path):
    temp_media_collection.insert_one({
        'file_id': file_id,
        'file_type': file_type,
        'file_date': file_date,
        'file_path': file_path
    })

def get_temp_media_by_id(file_id):
    return temp_media_collection.find_one({'file_id': file_id})

def get_all_temp_media():
    return list(temp_media_collection.find())

def clear_temp_media():
    temp_media_collection.delete_many({})
