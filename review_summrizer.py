import os
import re
import logging
from collections import Counter
from functools import partial

import asana


logging.basicConfig(level=logging.INFO)

TAKE_COURSE_PAT = r'^\d+\)'
AUDIT_PAT = r'^\d+\]'

personal_access_token = os.environ.get('ASANA_TOKEN')
client = asana.Client.access_token(personal_access_token)
client.options['project'] = os.environ.get('PROJECT_ID')


def task_name_filter(task, re_pattern):
    return re.search(re_pattern, task['name'])


take_course_filter = partial(task_name_filter, re_pattern=TAKE_COURSE_PAT)
audit_filter = partial(task_name_filter, re_pattern=AUDIT_PAT)


def reviewer_filter(task):
    return (
        '/' in task['name'] and
        '審核者' not in task['name']
    )


def count_review_status(task):
    subtasks = client.tasks.subtasks(task['id'])
    reviewer_subtasks = filter(reviewer_filter, subtasks)
    review_counter = Counter(
        subtask['name'].split('/')[1].strip()
        for subtask in reviewer_subtasks
    )
    return review_counter


def update_review_status(task, review_counter):
    stu_id, stu_name, apply_date, grade, *other = task['name'].split()

    formatted_review_counter = format_review_counter(review_counter)

    if formatted_review_counter:
        updated_name = ' '.join(
            (stu_id, stu_name, apply_date, grade, formatted_review_counter)
        )
        client.tasks.update(
            task['id'],
            {'name': updated_name}
        )
        logging.info(f'{updated_name} is updated')
    else:
        logging.info(f"No one reviews {task['name']}")


def format_review_counter(review_counter):
    return ','.join([
        f'{count_result[0]}_{count_result[1]}'
        for count_result in review_counter.most_common()
    ])


if __name__ == '__main__':
    tasks = list(client.tasks.find_all())

    take_course_tasks = filter(take_course_filter, tasks)
    audit_tasks = filter(audit_filter, tasks)

    all_tasks = list(take_course_tasks) + list(audit_tasks)
    for task in all_tasks:
        try:
            review_counter = count_review_status(task)
            update_review_status(task, review_counter)
        except Exception as err:
            logging.error(
                (
                    f"Error occurs on {task['name']}\n"
                    f"Exception: {err}"
                )
            )
