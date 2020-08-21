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
    notify_summary(df)

    top_n = 10
    notify_long_work_tickets(df, top_n)

    long_work_df = long_worklog_dataframe(start_date, end_date, top_n)
    notify_long_work_tickets_all_range(long_work_df)


def long_worklog_dataframe(start_date, end_date, top_n):
    """Create long worklog dataframe including out of range.

    Args:
        start_date (str): start date formatted as "%Y-%m-%d".
        end_date (str): end date formatted as "%Y-%m-%d".
        top_n (int): num of top.

    Returns:
        pandas.DataFrame

    """
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
    long_work_df = long_work_df.reindex(long_work_df.sum(axis=1).sort_values(ascending=False).index)
    return long_work_df


def notify_summary(df):
    """Notify worklog summary.

    Args:
        df (pandas.DataFrame): user worklog dataframe.

    """
    user_tickets = df.groupby("user").spent_hours.sum().sort_values(ascending=False)
    print(
        slack_notify(
            "\n".join([f"{idx}\n{value}" for idx, value in user_tickets.apply(format_spent_time).iteritems()])
        ).text
    )


def notify_long_work_tickets(df, top_n):
    """Notify long work tickets.

    Args:
        df (pandas.DataFrame): user worklog dataframe.
        top_n (int): num of top.

    """
    top_n_spent_time_tickets = df.groupby(["issue_key", "summary", "user"]).spent_hours.sum().nlargest(top_n)
    top_n_spent_time_ticket_summary = [
        f"{', '.join(idx)}\n{value}" for idx, value in top_n_spent_time_tickets.apply(format_spent_time).iteritems()
    ]
    slack_notify("\n".join(top_n_spent_time_ticket_summary))


def notify_long_work_tickets_all_range(long_work_df):
    """Notify long work tickets in all range.

    Args:
        long_work_df (pandas.DataFrame): user worklog dataframe including out of range.

    """
    slack_notify(
        "\n".join(
            [
                f"{', '.join(idx)}\n{value}"
                for idx, value in long_work_df.fillna(0).apply(format_spent_time_list, axis=1).iteritems()
            ]
        )
    )


def format_spent_time(hour):
    """Format spent time.

    Args:
        hour (float): spent hours.

    Returns:
        str: formatted spent time.

    """
    return f"{hour:2.2f} {'■■'*int(hour*2)}"


def format_spent_time_list(hour_list):
    """Format spent time list.

    Args:
        hour_list (`list` of `float`): int list ordered by time span.

    Returns:
        str: formatted hour list.

    """
    in_range_char = "■"
    before_char = "◁"
    after_char = "▷"
    in_range = hour_list[0]  # FIXME: This assumes that the list is in specific order (in_range, before, after)
    before = hour_list[1]
    after = hour_list[2]
    return (
        f"{before:2.2f} (before {before_char}) + {in_range:2.2f} (in range {in_range_char}) + "
        f"{after:2.2f} (after {after_char})\n"
        f"{before_char * 2 * int(before)}{in_range_char * 2 * int(in_range * 2)}{after_char * 2 * int(after)}"
    )


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
    res = requests.post(slack_webhook_url, data=json.dumps(payload_dic))
    if not res.ok:
        print(res.text)
        res.raise_for_status()


if __name__ == "__main__":
    worklog_handler({}, {})
