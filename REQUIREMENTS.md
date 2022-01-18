# Macroscope Infrastructure Interview Exercise

At Macroscope, our vision is to create an intuitive, map-like application that provides users with a shared view into their cloud infrastructure.
​
In this exercise, we want to build a set of AWS Lambda functions for accessing data across AWS accounts, transforming said data into a more compact format, and utilizing S3 events to trigger the movement of data when it is available.
​
Please **do not spend more than four hours on this project**. We will review whatever you can accomplish in that period of time.

## Prerequisites
You will need your own AWS account to complete this exercise. None of the requirements in this exercise will cause your account to exceed the free tier of AWS (assuming you do not create costly, errant resources).
​
Additionally, you will need to provide Macroscope with the account ID of your AWS account so that cross-account permissions can be set up ahead of time for access to the required resources within the Macroscope demo AWS account.
​
**Before** beginning the exercise, please do the following:

1. Provide Macroscope with the AWS account ID and region you will be deploying the exercise project into.
2. Wait for confirmation that the resources and permissions your project needs are ready within Macroscope's AWS account.
3. Test and confirm to Macroscope that you can access all AWS resources we have provided you.​
## Provided Resources
Your interactions with Macroscope AWS infrastructure will be with:

- The `macroscope-interviews` S3 bucket (you will have a dedicated sub-path to read from and write to).
- An IAM role in the Macroscope account that allows your project to read and write in our `macroscope-interviews` S3 bucket.
- A dedicated SNS topic (and related IAM policy) that you will subscribe to.

We will provide you with the ARNs of all resources before the beginning of your interview exercise.

## Project Requirements
- Using the cross-account IAM role and policy provided by Macroscope, subscribe a Lambda in your account to the provided SNS topic in the Macroscope account and listen for messages that will be in the following format:
	```json
  {
  	"s3_bucket": "arn:aws:s3:::macroscope-interviews",
  	"s3_objects": [
  		"/infra-eng/<your-specific-subpath>/input/2021-01-1T12:01:31-06:00.csv",
  		"/infra-eng/<your-specific-subpath>/input/2021-01-1T12:01:45-06:00.csv",
  		"/infra-eng/<your-specific-subpath>/input/2021-01-1T12:03:11-06:00.csv"
  	]
  }
	```
	These messages will be published to the SNS topic at irregular intervals over 10 minutes at various times as a way to test your project. Filenames will be in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.

- Using the S3 object paths in the message published to the SNS topic, retrieve the files and process them as follows:
  - Aggregate the data into five-minute intervals that align on the hour. This step **must** support aggregating files seen in separate SNS messages.
  - Transform the aggregated CSV data into the [Apache Parquet](https://en.wikipedia.org/wiki/Apache_Parquet) format.
  - Save the newly generated Parquet file to an S3 bucket you control.

- Using S3 event notifications, trigger a Lambda function to copy the generated Parquet file back to the `arn:aws:s3:::macroscope-interviews` S3 bucket at the `/infra-eng/<your-specific-subpath>/output/` path.

### Bonus Requirements
- Create a cross-account IAM role that allows the Macroscope account `451846548917` to access the Parquet files you wrote to your own S3 bucket.
- Restrict the cross-account IAM role above to only allow for objects with a given filename prefix (example: files that start with `ms-`) to be retrieved by Macroscope.


### Please Note
- The Lambdas you create may be written in the language you are most comfortable with.
- Deployment of your Lambda code may be done in any way that you choose, but please document how it is deployed.
- **All** resources for this project **must** be created using a single CloudFormation template.
- **All** project source code and documentation must be provided so that your project can be replicated in another AWS account.

## Next Steps and Review Conversation Topics

**Please make your project source available to us in a private git repo.**

Once we receive and review your exercise project, we will schedule a video call where you will present a tour of your work. The expectation is that you will provide deeper insight into your thinking, choices, and code. There may also be a short review phase where we pair with you to make changes to your project.
​
**Please leave your project deployed in your AWS account until you complete your review interview.**
​
Finally, please be prepared to talk about the following topics during your project review call:

- How do you manage AWS credentials on your local machine, and what steps do you take to ensure that compromise to your machine and/or credentials does not affect your AWS account(s)?
- What challenges have you encountered and measures have you taken to reduce AWS infrastructure costs at previous jobs?
- Which CI/CD platforms are you most familiar with, and what kind of work have you done in the past to enable and maintain infrastructure changes and software builds?