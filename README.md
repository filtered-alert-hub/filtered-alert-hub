### TODO
- convert to UTC time
- kinesis record duplication
- kinesis checkpoint.. do we need to keep track of which alerts have been written to which feed
- kinesis batchsize
- exception handling.. dead letter queue 

### configuration

##create and update AWS lambda function for processing of subscription 

aws lambda create-function --function-name ProcessSubscription --runtime "python2.7" --handler ProcessSubscription.lambda_handler --zip-file fileb://ProcessSubscription.zip
aws lambda update-function-code --function-name ProcessSubscription --zip-file fileb://ProcessSubscription.zip

aws lambda create-function --function-name ProcessKinesisRecords --runtime "python2.7" --handler ProcessKinesisRecords.lambda_handler --zip-file fileb://ProcessKinesisRecords.zip
aws lambda update-function-code --function-name ProcessKinesisRecords --zip-file fileb://ProcessKinesisRecords.zip


##subscribe lambda function to SNS topic 


##create AWS lambda function for feed updating

aws lambda create-function --function-name ProcessKinesisRecords --runtime "python2.7" --handler ProcessKinesisRecords.lambda_handler --zip-file fileb://ProcessKinesisRecords.zip
aws lambda update-function-code --function-name ProcessKinesisRecords --zip-file fileb://ProcessKinesisRecords.zip

## create kinesis queue and map to processing lambda function

aws kinesis create-stream --stream-name testkinesisstream  --shard-count 1 

aws kinesis describe-stream --stream-name testkinesisstream (get ARN)
aws lambda create-event-source-mapping --function-name ProcessKinesisRecords --event-source ARN --batch-size 100 --starting-position TRIM_HORIZON 

## create policy

need to allow the AWS lambda role to put and get from kinesis and to access s3

## send test event to SNS topic
aws sns list-topics

aws sns publish --topic-arn "arn:aws:sns:eu-west-1:921181852858:timo-test-sns" --message "file://./sns_test_1"

## maintenance

aws logs delete-log-group --log-group-name "/aws/lambda/ProcessKinesisRecords"
aws logs delete-log-group --log-group-name "/aws/lambda/ProcessSubscription"

## create topic to notify lambda of new alerts 
aws sns create-topic --name alert-hub-input-topic 

allow s3 to public to topic by adding this policy to the topic
{
	"Sid": "_s3",
	"Effect": "Allow",
	"Principal": {
	"AWS": "*"
	},
	"Action": "SNS:Publish",
	"Resource": "arn:aws:sns:eu-west-1:921181852858:alert-hub-input-topic",
	"Condition": {
	"StringEquals": {
	"aws:SourceArn": "arn:aws:s3:::wmo-alert-hub-input"
	}
	}
}

then configure notification of new s3 objects in bucket to sns topic
-using console.. usin s3api it does not seem to work..

finally trigger alert-capture function by SNS topic
aws sns subscribe --topic-arn "arn:aws:sns:eu-west-1:921181852858:alert-hub-input-topic"  --protocol "lambda" --notification-endpoint "arn:aws:lambda:eu-west-1:921181852858:function:alert-capture"
