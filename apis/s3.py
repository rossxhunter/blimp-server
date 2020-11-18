import boto3


def upload_profile_picture(user_id, file_path):
    client = boto3.client('s3', region_name='us-west-2')
    s3_path = "profile_pictures/{user_id}.jpg".format(user_id=user_id)
    client.upload_file(file_path, 'blimp-resources', s3_path)
