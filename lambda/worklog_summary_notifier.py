"""Lambda function to notify the summary of worklog."""

import base64
import json
import os
from datetime import datetime, timedelta

import boto3
import requests

from worklog_aggregator.jira_connector import worklog_dataframe
from worklog_aggregator.utils import categorize_date


def worklog_handler(event, context):
    """Notify the summary of worklogs."""
    day = datetime.today()
    start_date = (day - timedelta(weeks=1, days=day.weekday())).strftime("%Y-%m-%d")
    end_date = (day - timedelta(weeks=1, days=day.weekday() - 6)).strftime("%Y-%m-%d")
    print(f"Notify the summary of worklogs between {start_date} and {end_date}.")

    df = worklog_dataframe(start_date, end_date)
    user_tickets = df.groupby("user").spent_hours.sum().sort_values(ascending=False)
    print("\n".join([f"{idx}\n{value}" for idx, value in user_tickets.apply(format_spent_time).iteritems()]))

    top_n = 10
    top_n_spent_time_tickets = df.groupby(["issue_key", "summary", "user"]).spent_hours.sum().nlargest(top_n)
    top_n_spent_time_ticket_summary = [
        f"{', '.join(idx)}\n{value}" for idx, value in top_n_spent_time_tickets.apply(format_spent_time).iteritems()
    ]
    print("\n".join(top_n_spent_time_ticket_summary))
    df_with_all_worklog = worklog_dataframe(start_date, end_date, include_out_of_date_range=True).assign(
        date_category=lambda x: x.updated.apply(categorize_date, args=(start_date, end_date))
    )
    long_working_issues = df_with_all_worklog.groupby("issue_key").spent_hours.sum().nlargest(top_n).index
    long_work_df = (
        df_with_all_worklog[df_with_all_worklog.issue_key.isin(long_working_issues)]
        .groupby(["issue_key", "summary", "user", "date_category"])
        .spent_hours.sum()
        .unstack("date_category", fill_value=0)
    )
    print(long_work_df)


def format_spent_time(hour):
    """Format spent time."""
    return f"{hour:2.2f} {'■■'*int(hour*2)}"


def slack_notify(msg):
    """Notify message on slack channel.

    Args:
        msg (str): slack message.

    Returns:
        requests.models.Response

    """
    if not msg:
        return
    payload_dic = {
        "text": msg,
        "username": "Jobcan Lambda Notification",
        "channel": os.environ["SLACK_CHANNEL"],
    }
    client = boto3.client("kms")
    slack_webhook_url = client.decrypt(CiphertextBlob=base64.b64decode(os.getenv("ENCRYPTED_SLACK_WEBHOOK_URL")))[
        "Plaintext"
    ]
    return requests.post(slack_webhook_url, data=json.dumps(payload_dic))


if __name__ == "__main__":
    worklog_handler({}, {})
