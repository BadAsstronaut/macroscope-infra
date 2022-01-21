''' Handles S3 upload event '''

from datetime import datetime
import io
import os

import boto3


TARGET_S3_BUCKET = os.environ['TARGET_S3_BUCKET']
TARGET_S3_BUCKET_ROLE = os.environ['TARGET_S3_BUCKET_ROLE']
SOURCE_S3_BUCKET = os.environ['SOURCE_S3_BUCKET']
TARGET_S3_PREFIX = os.environ['TARGET_S3_PREFIX']

own_acct_session = boto3.Session()
own_acct_s3_client = own_acct_session.client('s3')

def get_cross_account_session() -> boto3.Session:
    '''
    Reference: https://aws.amazon.com/premiumsupport/knowledge-center/lambda-function-assume-iam-role/
    '''
    sts = boto3.client('sts')
    acct = sts.assume_role(RoleArn=TARGET_S3_BUCKET_ROLE,
                           RoleSessionName='mickey-macroscope-interview')
    creds = acct['Credentials']

    return boto3.Session(aws_access_key_id=creds['AccessKeyId'],
                         aws_secret_access_key=creds['SecretAccessKey'],
                         aws_session_token=creds['SessionToken'])


def get_s3_object(path: str) -> io.IOBase:
    '''
    Gets the S3 object
    '''
    res = own_acct_s3_client.get_object(Bucket=SOURCE_S3_BUCKET,
                                        Key=path)

    return io.BytesIO(res.body.read())


def save_target_s3(file: io.IOBase, path: str, session: boto3.Session) -> None:
    ''' Saves the file to the target S3 path on the local account bucket '''
    session.put_object(Body=file,
                       Bucket=TARGET_S3_BUCKET,
                       Key=path)


def handler(event: dict, _) -> None:
    ''' Handles uploading a file from the local account to the Macroscope S3 bucket '''
    x_acct_session = get_cross_account_session()

    try:
        obj_key = event['Records'][0]['s3']['object']['key']
        upload_key = datetime.utcnow().replace(microsecond=0).isoformat()
        upload_key = f'{TARGET_S3_PREFIX}{obj_key}.parquet'
    except KeyError as key_err:
        raise Exception('S3 event did not conform to the expected payload schema') from key_err

    s3_obj = get_s3_object(obj_key)
    save_target_s3(s3_obj, upload_key, x_acct_session)
