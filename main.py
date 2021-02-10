from collections import Counter

import requests
from tqdm import tqdm
import multiprocessing
from joblib import Parallel, delayed
from functools import reduce
from operator import add
num_cores = multiprocessing.cpu_count()
import sys

def fetch_pull_requests(username, token, repo):
    response = requests.get('https://api.github.com/repos/despegar/%s/pulls?state=all&per_page=100' % repo,
                            auth=(username, token)).json()
    return response


def fetch_pull_reviews(username, token, repo, pr_number):
    response = requests.get('https://api.github.com/repos/despegar/%s/pulls/%s/reviews' % (repo, pr_number),
                            auth=(username, token)).json()
    return response


def extract_pull_request_stats(pr, username, token, repo):
    user_stats = dict()
    creator = pr['user']['login']
    creator_stats = user_stats.setdefault(creator, dict())
    creator_stats['pr_count'] = creator_stats.setdefault('pr_count', 0) + 1
    pull_requests_reviews = fetch_pull_reviews(username, token, repo, pr['number'])
    for review in pull_requests_reviews:
        reviewer = review['user']['login']
        reviewer_stats = user_stats.setdefault(reviewer, dict())
        if review['state'] == 'CHANGES_REQUESTED':
            creator_stats['changes_requested'] = + 1
            reviewer_stats['asked_for_changes'] = + 1
    return user_stats


def mergeDict(dict1, dict2):
    dict3 = {**dict1, **dict2}
    for key, value in dict3.items():
        if key in dict1 and key in dict2 and dict1[key] is not None:
            dict3[key] = reduce(add, (Counter(dict(x)) for x in [value, dict1[key]]))
    return dict3


def process_pull_requests(username, token, repo):
    pull_requests = fetch_pull_requests(username, token, repo)
    pr_process_result = Parallel(n_jobs=num_cores)(delayed(extract_pull_request_stats)(pr, username, token, repo) for pr in tqdm(pull_requests))
    user_stats = reduce(mergeDict, pr_process_result)
    for user in user_stats.keys():
        if user_stats[user] != {}:
            percentage = user_stats[user].setdefault('changes_requested', 0) / user_stats[user]['pr_count']
            user_stats[user]['blocked_percentage'] = "%s%%" % round(percentage * 100)

        print("%s has %s PR - %s of them with changes requested" % (user, user_stats[user]['pr_count'], user_stats[user]['blocked_percentage']))


if __name__ == "__main__":
    process_pull_requests(sys.argv[1], sys.argv[2], sys.argv[3])

