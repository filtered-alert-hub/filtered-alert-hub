import io
import json

import ProcessKinesisRecords



records = json.loads(open('testing\kinesis_test_1.json').read())

ProcessKinesisRecords.lambda_handler(records,None)  





