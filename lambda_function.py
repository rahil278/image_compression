import io
import os
import cgi
import json
import uuid
import boto3
import base64

from PIL import Image

from constants import *

s3_client = boto3.client('s3')


def get_file_from_request_body(headers, body):
    fp = io.BytesIO(base64.b64decode(body))
    env = {"REQUEST_METHOD": "POST"}
    header = {
        "content-type": headers.get("content-type") or headers.get('Content-Type'),
        "content-length": headers.get("content-length") or headers.get('Content-Length'),
    }
    fs = cgi.FieldStorage(fp=fp, environ=env, headers=header)
    return fs[FILE_KEY]


def compress_and_upload_file(file, file_name):
    image_obj = Image.open(file)
    width, height = image_obj.size
    new_size = (int(WIDTH), int(float(height) * float(WIDTH) / float(width)))

    if width > WIDTH:
        mode = image_obj.mode
        image_obj = image_obj.resize(new_size, Image.LANCZOS)
        if mode == 'RGBA' or mode == 'RGBa':
            background_layer = Image.new('RGB', new_size, (255, 255, 255))
            background_layer.paste(image_obj, image_obj)
            image_obj = background_layer.convert('RGB')

    image_obj.save(OUTPUT_PATH + file_name, 'JPEG', quality=QUALITY)

    s3_client.upload_file(OUTPUT_PATH + file_name, BUCKET_NAME, file_name)


def delete_file(file_name):
    if os.path.exists(OUTPUT_PATH + file_name):
        os.remove(OUTPUT_PATH + file_name)


def lambda_handler(event, context):
    try:
        file_name = str(uuid.uuid4()) + '.jpeg'
        image_file = get_file_from_request_body(headers=event.get("headers", {}), body=event.get("body", {}))
        compress_and_upload_file(image_file.file, file_name)
        delete_file(file_name)
        location = s3_client.get_bucket_location(Bucket=BUCKET_NAME)['LocationConstraint']
        object_url = f'''https://{BUCKET_NAME}.s3.{location}.amazonaws.com/{file_name}'''
        return json.dumps({'status': 'success', 'url': object_url})
    except Exception as e:
        print(str(e))
        return json.dumps({'status': 'failure', 'error': str(e)})
