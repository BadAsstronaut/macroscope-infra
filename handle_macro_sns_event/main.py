'''
Handler for SNS topic subscription
'''

from datetime import datetime
import io
import json
import os

import boto3
import pandas as pd


SOURCE_S3_BUCKET = os.environ['SOURCE_S3_BUCKET']
SOURCE_S3_BUCKET_ROLE = os.environ['SOURCE_S3_BUCKET_ROLE']
TARGET_S3_BUCKET = os.environ['TARGET_S3_BUCKET']

own_acct_session = boto3.Session()
own_acct_s3_client = own_acct_session.client('s3')


def dataframe_to_parquet(dataframe: pd.DataFrame) -> io.IOBase:
    '''
    Uses pd to convert a IOBase type from csv to parquet
    '''
    result = io.BytesIO()
    dataframe.to_parquet(result)
    result.seek(0)
    return result


def save_target_s3(file: io.IOBase, path: str) -> None:
    ''' Saves the file to the target S3 path on the local account bucket '''
    own_acct_s3_client.put_object(Body=file,
                                  Bucket=TARGET_S3_BUCKET,
                                  Key=path)


def get_s3_object(bucket: str, path: str, session: boto3.Session) -> io.IOBase:
    '''
    Gets the S3 object
    '''
    s3_client = session.client('s3')

    res = s3_client.get_object(Bucket=bucket,
                               Key=path)

    return io.BytesIo(res.body.read())


def get_cross_account_session() -> boto3.Session:
    '''
    Reference: https://aws.amazon.com/premiumsupport/knowledge-center/lambda-function-assume-iam-role/
    '''
    sts = boto3.client('sts')
    acct = sts.assume_role(RoleArn=SOURCE_S3_BUCKET_ROLE,
                           RoleSessionName='mickey-macroscope-interview')
    creds = acct['Credentials']

    return boto3.Session(aws_access_key_id=creds['AccessKeyId'],
                         aws_secret_access_key=creds['SecretAccessKey'],
                         aws_session_token=creds['SessionToken'])


def process_s3_obj(key: str,
                   session: boto3.Session,
                   datetime_series: str = 'eventTime') -> None:
    ''' Handles processing the s3 file and uploading the updated result  '''
    raw_file = get_s3_object(SOURCE_S3_BUCKET, key, session)
    dataframe = pd.read_csv(raw_file)

    # Convert the time index to datetimes
    dataframe[datetime_series] = pd.to_datetime(dataframe[datetime_series])
    aggregation = {'awsRegion': 'unique',
                   'userAgent': 'unique',
                   'principalId': 'unique',
                   'accountId': 'unique',
                   'eventType': 'unique',
                   'eventName': 'unique',
                   'eventSource': 'unique',
                   'isError': 'sum'}
    dataframe = dataframe.set_index(datetime_series).resample('5min').aggregate(aggregation)
    pq_data = dataframe_to_parquet(dataframe)
    save_target_s3(pq_data, f'/ms-{datetime.now().replace(microsecond=0).isoformat()}.parquet')


def handler(event: dict, _) -> None:
    '''
    SNS event https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html

    Records[].Sns.Message example:
    {"s3_bucket": "arn:aws:s3:::macroscope-interviews",
     "s3_objects": [
         "/infra-eng/<your-specific-subpath>/input/2021-01-1T12:01:31-06:00.csv",
         "/infra-eng/<your-specific-subpath>/input/2021-01-1T12:01:45-06:00.csv",
         "/infra-eng/<your-specific-subpath>/input/2021-01-1T12:03:11-06:00.csv"]}
    '''

    x_acct_session = get_cross_account_session()

    try:
        s3_object_paths = json.loads(event['Records'][0]['Sns']['Message'])['s3_objects']
    except KeyError as key_ex:
        raise Exception('Sns message format did not conform to expected payload schema') from key_ex

    _ = [process_s3_obj(el, x_acct_session) for el in s3_object_paths]
