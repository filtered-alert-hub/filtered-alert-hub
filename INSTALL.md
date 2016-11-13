Installation log AH
a)	Need S3 buckets
a.	“alert-hub-input”: new alerts are deposited there
b.	“alert-hub”: this is where new alerts are copied once they are validated (renamed)

1)	Create IAM role for lambda exection
We use the “lambda basic exec”; “dynamodb exec”, “s3 full access” and “kinesis exec” templates
arn:aws:iam::381798314226:role/wah-lambda-exec
2)	Install new alert lambda function
aws lambda create-function --function-name NewAlert --runtime "python2.7" --handler NewAlert.lambda_handler --zip-file fileb:// NewAlert.zip –role “arn:aws:iam::381798314226:role/wah-lambda-exec”
"FunctionArn": "arn:aws:lambda:eu-west-1:381798314226:function:NewAlert",

3)	Send S3 events to lambda function (via console)

4)	Create topic for Ian’s code to send messages to

aws sns create-topic --name wah_post-geofilter   --profile wah
{
    "TopicArn": "arn:aws:sns:eu-west-1:381798314226:wah_post-geofilter"
}

5)	Create topic for Ian’s code to subscribe to

aws sns create-topic --name wah_post-alert-capture   --profile wah
{
    "TopicArn": "arn:aws:sns:eu-west-1:381798314226:wah_post-alert-capture"
}

6)	Deploy Ian’s code

aws lambda create-function   --function-name FindSubsForAlert   --runtime nodejs    --role "arn:aws:iam::381798314226:role/wah-lambda-exec"  --handler FindSubsForAlert.handler     --zip-file "fileb://./FindSubsForAlert.zip" --profile wah
{
    "CodeSha256": "0ON3mEFwd9O9RlJokraG0xdIL1e73ymF1srQYm3epWI=",
    "FunctionName": "FindSubsForAlert",
    "CodeSize": 692976,
    "MemorySize": 128,
    "FunctionArn": "arn:aws:lambda:eu-west-1:381798314226:function:FindSubsForAlert",
    "Version": "$LATEST",
    "Role": "arn:aws:iam::381798314226:role/wah-lambda-exec",
    "Timeout": 3,
    "LastModified": "2016-10-31T21:13:11.727+0000",
    "Handler": "FindSubsForAlert.handler",
    "Runtime": "nodejs",
    "Description": ""
}


7)	Deploy ProcessSubscription (Filter Code)

aws lambda create-function --function-name ProcessSubscription --runtime "python2.7" --handler ProcessSubscription.lambda_handler --zip-file fileb://ProcessSubscription.zip --role "arn:aws:iam::381798314226:role/wah-lambda-exec" --profile wah

