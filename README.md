# jira-worklog-aggregator
Get worklogs on JIRA tickets.

## Quick Start
### Setting Env Variables

Copy .env.sample to .env and fill in the environment values by your favorite editor.

```bash
cp .env.sample .env
vim .env
```

### Build image

```bash
docker build . -t jira-worklog-aggregator
```

### Run Script

```bash
docker run --rm -it --env-file=.env  -v .:/usr/src jira-worklog-aggregator python -m worklog_aggregator.worklog_aggregator
```


### Launch jupyter notebook

```bash
docker run --rm -it --env-file=.env  -v .:/usr/src jira-worklog-aggregator jupyter notebook
```

## Create Lambda Layer

```bash
docker build . -t lambda-layer
docker run --rm -v $(pwd):/dist lambda-layer pandas
```

## Create Lambda Function

```bash
aws lambda create-function \
    --function-name <your function name> \
    --runtime python3.8 \
    --role <your role> \
    --handler worklog_summary_notifier.worklog_handler \
    --zip-file fileb://function.zip
```
