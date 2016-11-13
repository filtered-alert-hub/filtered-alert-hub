import io
import json

import FilterGeometry



#records = json.loads(open('testing\kinesis_test_1.json').read())


alert = json.load(open('testing\\alertx.json'))


FilterGeometry.lambda_handler(alert,None)  





