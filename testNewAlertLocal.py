import io
import json

import NewAlert



records = json.loads(open('testing/test-sns-topic-invoke-lambda.json').read())

NewAlert.lambda_handler(records,None)  





