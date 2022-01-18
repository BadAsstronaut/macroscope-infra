'''
Handler for SNS topic subscription
'''

import io
import json

import pandas as pd


def convert_csv_to_parquet(csv: io.BaseIO) -> io.BaseIO:
    '''
    Uses pd to convert a BaseIO type from csv to parquet
    '''
    dataframe = pd.read_csv(csv)
    result = io.BytesIO()
    dataframe.to_parquet(result)
    result.seek(0)
    return result


def time_interval(iso_time: str) -> str:
    '''  '''


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
        sns_messages = json.loads(event['Records'][0]['Sns']['Message'])

    except KeyError as key_ex:
        raise Exception('Sns message format did not conform to expected payload schema') from key_ex
