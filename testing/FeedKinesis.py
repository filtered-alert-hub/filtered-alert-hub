from boto import kinesis

kinesis = kinesis.connect_to_region("eu-west-1")


kinesis.put_record("testkinesisstream", "gach2345", "shardId-000000000000")
