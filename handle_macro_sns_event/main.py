'''
Handler for SNS topic subscription
'''

from datetime import datetime
import io
import json
import os
from pickle import GLOBAL
from typing import List

import boto3
from botocore.exceptions import ClientError
import pandas as pd


SOURCE_S3_BUCKET = os.environ['SOURCE_S3_BUCKET']
SOURCE_S3_BUCKET_ROLE = os.environ['SOURCE_S3_BUCKET_ROLE']
TARGET_S3_BUCKET = os.environ['TARGET_S3_BUCKET']

# Use an S3 file to sync a raw dataframe with csv contents; aggregated results will be recalculated per-csv
GLOBAL_DATAFRAME_AGGREGATION_PATH = '/ms-cross-event-dataframe.parquet'

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
    # TODO: Move this to shared layer
    own_acct_s3_client.put_object(Body=file,
                                  Bucket=TARGET_S3_BUCKET,
                                  Key=path)


def get_s3_object(bucket: str, path: str, session: boto3.Session) -> io.IOBase:
    '''
    Gets the S3 object
    '''
    # TODO: Move this to shared layer
    s3_client = session.client('s3')

    res = s3_client.get_object(Bucket=bucket,
                               Key=path)

    bytes_io = io.BytesIO(res['Body'].read())
    bytes_io.seek(0)

    return bytes_io


def get_cross_account_session() -> boto3.Session:
    '''
    Reference: https://aws.amazon.com/premiumsupport/knowledge-center/lambda-function-assume-iam-role/
    '''
    # TODO: Move this to shared layer
    sts = boto3.client('sts')
    acct = sts.assume_role(RoleArn=SOURCE_S3_BUCKET_ROLE,
                           RoleSessionName='mickey-macroscope-interview')
    creds = acct['Credentials']
    return boto3.Session(aws_access_key_id=creds['AccessKeyId'],
                         aws_secret_access_key=creds['SecretAccessKey'],
                         aws_session_token=creds['SessionToken'])


def get_s3_csv_dataframe(key: str,
                         session: boto3.Session,
                         datetime_series: str = 'eventTime') -> pd.DataFrame:
    ''' Handles processing the s3 file and uploading the updated result  '''
    raw_file = get_s3_object(SOURCE_S3_BUCKET, key, session)
    dataframe = pd.read_csv(raw_file)

    # Convert the time index to datetimes
    dataframe[datetime_series] = pd.to_datetime(dataframe[datetime_series])

    return dataframe

def get_macro_s3_updates(s3_object_paths: List[str]) -> List[pd.DataFrame]:
    ''' Gets dataframes of each csv file '''
    x_acct_session = get_cross_account_session()
    return [get_s3_csv_dataframe(el, x_acct_session) for el in s3_object_paths]


def resample_aggregrate(dataframe: pd.DataFrame,
                        datetime_series: str = 'eventTime') -> pd.DataFrame:
    ''' Resample & aggregate the dataframe '''
    # No specs provided re: aggregation criteria, tried default but it was adding AWS acct #s... :/
    # Unique seems most relevant for most strings, isError should be summed
    # TODO: Dynamically check for data type and set aggregation criteria accordingly
    aggregation = {'awsRegion': 'unique',
                   'userAgent': 'unique',
                   'principalId': 'unique',
                   'accountId': 'unique',
                   'eventType': 'unique',
                   'eventName': 'unique',
                   'eventSource': 'unique',
                   'isError': 'sum'}

    return dataframe.set_index(datetime_series).resample('5min').aggregate(aggregation)


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
    try:
        s3_object_paths = json.loads(event['Records'][0]['Sns']['Message'])['s3_objects']
    except KeyError as key_ex:
        raise Exception('Sns message format did not conform to expected payload schema') from key_ex

    try:
        global_dataframe_pq = get_s3_object(TARGET_S3_BUCKET, GLOBAL_DATAFRAME_AGGREGATION_PATH, own_acct_session)
        global_dataframe = pd.read_parquet(global_dataframe_pq)
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            global_dataframe = pd.DataFrame()

    dataframe_updates = get_macro_s3_updates(s3_object_paths)
    dataframe_updates.append(global_dataframe)  # Add the global_dataframe to the list of dataframes to concat
    global_dataframe = pd.concat(dataframe_updates, axis=0)

    dataframe_resampled = resample_aggregrate(global_dataframe)
    pq_data = dataframe_to_parquet(dataframe_resampled)
    save_target_s3(pq_data, f'/ms-{datetime.now().replace(microsecond=0).isoformat()}.parquet')

    pq_global_dataframe = dataframe_to_parquet(global_dataframe)
    save_target_s3(pq_global_dataframe, GLOBAL_DATAFRAME_AGGREGATION_PATH)
