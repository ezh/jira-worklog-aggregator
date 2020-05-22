"""Get the working summary in JIRA."""
import argparse

import matplotlib.pyplot as plt

from .jira_connector import worklog_dataframe

plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['figure.figsize'] = 12, 8
plt.rcParams['font.size'] = 18


def main(start_date, end_date):
    """Create the summary of worklog."""
    df = worklog_dataframe(start_date, end_date)

    if not df.empty:
        plt.figure()
        title = f'Spent hours on tickets between {start_date} and {end_date}'
        df.groupby('user').spent_hours.sum().sort_values(ascending=False).plot.bar(title=title)
        plt.savefig(f'{start_date}-{end_date}_worklog_summary.png')

        plt.figure()
        title = f'Top 10 taking time tickets between {start_date} and {end_date}'
        df.groupby(['issue_key', 'user']).spent_hours.sum().nlargest(20).plot.bar(title=title)
        plt.savefig(f'{start_date}-{end_date}_top20_taking_time.png')

        plt.figure()
        df_with_all_worklog = worklog_dataframe(start_date, end_date, include_out_of_date_range=True).assign(
            date_category=lambda x: x.updated.apply(categorize_date, args=(start_date, end_date))
        )
        long_working_issues = df_with_all_worklog.groupby('issue_key').spent_hours.sum().nlargest(20).index
        title = f'Top 10 taking time tickets between {start_date} and {end_date} (includes out of date range worklogs)'
        df_with_all_worklog[df_with_all_worklog.issue_key.isin(long_working_issues)].groupby(
            ['issue_key', 'user', 'date_category']
        ).spent_hours.sum().unstack('date_category').plot.bar(title=title, stacked=True)
        plt.savefig(f'{start_date}-{end_date}_top20_taking_time_with_out_of_date_range_work.png')
    else:
        print(f'No worklogs between {start_date} and {end_date}.')


def categorize_date(date, start_date, end_date):
    """Categorize date."""
    if date < start_date:
        return f'< {start_date}'
    elif date > end_date:
        return f'> {end_date}'
    else:
        return f'{start_date} ~ {end_date}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', help='target start date of worklog')
    parser.add_argument('--end_date', help='target end date of worklog')
    args = parser.parse_args()
    main(args.start_date, args.end_date)
