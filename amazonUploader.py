import boto3, botocore
import os, sys, hashlib
import PIL.Image, PIL.ExifTags
from datetime import datetime
import configparser
import threading
import json
import re

s3 = boto3.resource('s3')
#s3=boto3.resource('s3')
base_bucket_name = "photos.pataky."
hash_file=".amazonUploader" #file contains albumname and file-hash pairs
json_file = "photos.json"
hash_photos = "Photos"
hash_album = "Album"
image_ext = ".jpg", ".jpeg", ".png", ".gif"
video_ext = ".mov", ".avi", ".m4v", ".mp4"
hash_prefix = "sha256_"

def is_valid_path(path):
    """Checks if the given path exists"""
    return os.path.exists(path)

def get_media_files(path):
    """Returns the list of media files are in predefined folder"""
    return [file_name for file_name in os.listdir(path)
            if file_name.lower().endswith(image_ext + video_ext)]

def is_video_file(file_path):
    """Checks if the given file (with path) is a movie file"""
    return file_path.lower().endswith(video_ext)

def get_exif(file_path):
    result = {}
    if is_image_file(file_path):
        img = PIL.Image.open(file_path)
        result = getattr(img, '_getexif', lambda: {})()
        img.close()
    return result if result != None else {}

def is_image_file(file_path):
    """Checks if the given file (with path) is an image"""
    return file_path.lower().endswith(image_ext)

def get_date_taken_from_file_name(file_name):
    result = 0
    match = re.search(r'\d{8}_\d{6}', file_name)
    if match:
        try:
            date = datetime.strptime(match.group(), '%Y%m%d_%H%M%S')
            result = date
        except ValueError as ve:
            pass
    return result

def get_file_info(file_path, file_name):
    """get useful exif info of the file"""
    exif_info = get_exif(file_path)
    result = {}
    #get exif data
    date_taken = exif_info.get(36867, "0000:00:00 00:00:00")
    if date_taken != "0000:00:00 00:00:00":
        date_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
    else:
        date_taken = get_date_taken_from_file_name(file_name)
        if date_taken == 0:
            date_taken = os.path.getctime(file_path)
            date_taken = datetime.fromtimestamp(date_taken)
    result['date_taken'] = datetime.timestamp(date_taken)

    orientation = exif_info.get(274, 1)
    result['orient'] = orientation

    return result

def calculate_hash_of_file(filepath):
    ''' Calculates the Hash code of the file.
        The hash code depends on the file content not the name of it.
        So renamed files have the same hash_code.
        If the content of the file is changed the hash code will be
        differ from the original file.'''
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as afile:
        buffer = afile.read()
        hasher.update(buffer)
    return (hasher.hexdigest())

def get_size(file_path):
    """Returns the size of the given file in MB"""
    precision = 2
    sizes = ((1024*1024, "MB"), (1024, "Kb"), (2, "bytes"), (1, "byte"))
    if not is_valid_path(file_path):
        return '{}{}'.format(0, 'MB')
    size_in_bytes = os.path.getsize(file_path)
    for min_size, abbrev in sizes:
        if size_in_bytes >= min_size:
            return '{} {}'.format(
                    round(size_in_bytes / min_size, precision),
                    abbrev)

def get_photo_data(path, file_name):
    """Sets photo data for the given file."""
    file_path = os.path.join(path, file_name)
    upload_data = {'src': file_name,
            'type': 'vid' if is_video_file(file_name) else 'img',
            'size': get_size(file_path)}
    data = {'upload_data': upload_data,
            'filename': file_name,
            'source': file_path,
            'dirname': path,
            'uploaded': False}
    file_info = get_file_info(file_path, file_name)
    data['upload_data'].update(file_info)
    return data

def clear_hash_data(path):
    config_path = os.path.join(path, hash_file)
    if is_valid_path(config_path):
        f = open(config_path, 'r+')
        f.truncate(0)

def get_config_options_for_section(path, config, section):
    """Returns options for the givem section from the config file.
        If the file demaged, the content of it will be deleted."""
    result = {}
    config_path = os.path.join(path, hash_file)
    if not is_valid_path(config_path):
        return result
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        if section not in config.sections():
            return {}
        options = config.options(section)
        for option in options:
            try:
                result[option.lower()] = (config.get(section, option)).lower()
            except Exception as e:
                #Corrupt hash_file -> clear it
                clear_hash_data(path)
    except configparser.MissingSectionHeaderError as mse:
        #Corrupt hash_file -> clear it
        clear_hash_data(path)
    return result

def read_hash_from_config(path):
    """Reads the (filename, hash_code) pairs from config file"""
    config = configparser.ConfigParser()
    return get_config_options_for_section(path, config, hash_photos)

def read_album_from_config(path):
    """Reads amazon albumname for the given path from config file
        If there is no albumname, it returns empty string"""
    config = configparser.ConfigParser({hash_album: ""})
    options = get_config_options_for_section(path, config, hash_album)
    return options.get(hash_album.lower(), "")

def append_to_hash_file(path, section, option, value):
    """"Saves the given option with the given value under
        the given sectioninto the config file.
        If the config file doesn't exist, it creates it.
        If the given section doesn't exist, it adds to the file."""
    config_path = os.path.join(path, hash_file)

    config = configparser.ConfigParser()

    if not is_valid_path(config_path):
        config.add_section(section)
    else:
        config.read(config_path)
        if section not in config.sections():
            config.add_section(section)
    config.set(section, option, value)
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_album_name(path, album):
    """ Returns the album_name. The rules:
        First check the config file. If the album is set-it will use it. 
        If not, use the given album parameter """
    album_name = read_album_from_config(path)
    return album_name if album_name else album

def set_selectable(path, data_list, is_valid_album):
   """Marks the uploaded data in the datalist """
   datas = data_list
   if is_valid_album:
       hash_name_pairs = read_hash_from_config(path)
       filenames_from_hash = [file_name.lower() for file_name
           in list(hash_name_pairs)]
       for data in datas:
           if data['filename'].lower() in filenames_from_hash:
               data['uploaded'] = True
   else:
       #the hash_file is corrupt --> clear it
       clear_hash_data(path)
   return datas

class ProgressPercentage(object):
    def __init__(self, file_name):
        self._filename = file_name
        self._size = os.path.getsize(file_name)
        self._lock = threading.Lock()
        self._uploaded = 0

    def byte_to_kB(self, source):
        return str(round(source /1024)) + 'kB'

    def __call__(self, bytes_amount):
        with self._lock:
            self._uploaded += bytes_amount
            percentage = (self._uploaded * 100) / self._size
            sys.stdout.write("\r%s  %s/ %s (%.2f%%)" % (
                'Uploading %s:' % self._filename,
                self.byte_to_kB(self._uploaded),
                self.byte_to_kB(self._size),
                percentage))
            sys.stdout.flush()

class AmazonUploader():
    def get_bucket_name_for_album(self, album_name):
        return base_bucket_name + album_name
    
    def is_valid_bucket(self, album_name):
        result = True
        bucket_name = self.get_bucket_name_for_album(album_name)
        try:
            s3.meta.client.head_bucket(Bucket = bucket_name)
        except botocore.client.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                result = False
        return result

    def is_key_exists(self, album_name, key):
        result = True
        bucket_name = self.get_bucket_name_for_album(album_name)
        try:
            s3.meta.client.head_object(Bucket = bucket_name, Key = key)
        except botocore.client.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                result = False
        return result

    def is_json_exists(self, album_name):
        return self.is_key_exists(album_name, json_file)

    def is_index_html_exists(self, album_name):
        return self.is_key_exists(album_name, 'index.html')

    def get_all_photos_data(self, path, album_name):
        """Retruns all data of photos (media files) from the given path"""
        result = []
        media_files = get_media_files(path)
        for file_name in media_files:
            data = get_photo_data(path, file_name)
            result.append(data)
        #check if the album is a valid amazon bucket name
        is_valid_album = self.is_valid_bucket(album_name)
        result = set_selectable(path, result, is_valid_album)
        return result
   
    def append_to_amazon_config(self, album_name, photo_data):
        bucket_name = self.get_bucket_name_for_album(album_name)
        json_object = s3.Object(bucket_name, json_file)
        
        if not self.is_json_exists(album_name):
            #if json file doesn't exist - create with the given photo data
            json_content = []
        else:
            #if json file exists - read-append*sort-save
            file_content = json_object.get()['Body'].read().decode('utf-8')
            json_content = json.loads(file_content)

        json_content.append(photo_data['upload_data'])
        sorted_content = sorted(json_content, key = lambda k: k.get('date_taken', 0), reverse = True)
        json_object.put(ACL= 'public-read', Body = json.dumps(sorted_content, ensure_ascii = False))

    def upload_photo(self, photo, bucket_name):
        try:
            result =  s3.meta.client.upload_file(Filename = photo['source'],
                Bucket = bucket_name, Key = photo['filename'],
                ExtraArgs = {'ACL': 'public-read'},
                Callback = ProgressPercentage(photo['filename']))
            print('\n')
        except ClientError as e:
            return False
        return True

    def update_bucket(self, photos, album_name):
        #update bucket
        amazon_bucket_name = self.get_bucket_name_for_album(album_name)
        if photos:
            #checks if the albumname is in configfile. If not, put it in
            append_to_hash_file(
                    photos[0]['dirname'],
                    hash_album,
                    hash_album,
                    album_name)

        for photo in photos:
            #upload photos one by one and add hash to the config file
            hash_of_photo = calculate_hash_of_file(photo['source'])
            if self.upload_photo(photo, amazon_bucket_name):
                self.append_to_amazon_config(album_name, photo)
                append_to_hash_file(photo['dirname'], hash_photos, photo['filename'], hash_of_photo)
            else:
                print('\n Upload failed')

    def update_index_html(self, bucket_name):
        """upload index.html if not available or there is a newer version"""
        index_html_path = sys.path[0] + '\index.html'
        s3.meta.client.upload_file(Filename = index_html_path, 
                Bucket = bucket_name, Key = 'index.html',
                ExtraArgs = {'ACL': 'public-read'})

    def create_bucket(self, bucket_name):
        print('New album %s \n' % album_name)
        s3.create_bucket(Bucket = bucket_name,
                ACL = "public-read",
                CreateBucketConfiguration={ 'LocationConstraint': 'EU'})

    def update_or_create_album(self, photos, album_name):
        bucket_name = self.get_bucket_name_for_album(album_name)
        if not self.is_valid_bucket(album_name):
            #create bucket
            self.create_bucket(bucket_name)
        self.update_index_html(bucket_name)
        print('Update album %s \n' % album_name)
        print('New files: %d \n' % (len(photos)))
        self.update_bucket(photos, album_name)

    def upload_all(self, path, album):
        """Upload all media files from the given folder to the given album"""
        album_name = get_album_name(path, album)
        data = self.get_all_photos_data(path, album_name)
        #get the photos needs to be uploaded
        uploadable = [photo for photo in data if photo['uploaded'] == False]
        self.update_or_create_album(uploadable, album_name)
