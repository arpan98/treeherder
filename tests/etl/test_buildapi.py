import json
import os

import pytest
import responses
from django.conf import settings
from django.core.cache import cache

from treeherder.etl.buildapi import (CACHE_KEYS,
                                     Builds4hJobsProcess,
                                     PendingJobsProcess,
                                     RunningJobsProcess)


@pytest.fixture
def mock_buildapi_pending_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "builds-pending.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_PENDING_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_running_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "builds-running.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_RUNNING_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_builds4h_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "buildbot_text.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_BUILDS4H_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_pending_missing1_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "builds-pending-missing1.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_PENDING_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_running_missing1_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "builds-running-missing1.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_RUNNING_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_builds4h_missing1_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "buildbot_text-missing1.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_BUILDS4H_URL',
                        "file://{0}".format(path))


@pytest.fixture
def mock_buildapi_builds4h_missing_branch_url(monkeypatch):
    tests_folder = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(
        tests_folder,
        "sample_data",
        "buildbot_text-missing_branch.json"
    )
    monkeypatch.setattr(settings,
                        'BUILDAPI_BUILDS4H_URL',
                        "file://{0}".format(path))


def test_ingest_pending_jobs(jm,
                             mock_buildapi_pending_url,
                             mock_post_json,
                             mock_log_parser,
                             mock_get_resultset,
                             mock_fetch_json):
    """
    a new buildapi pending job creates a new obj in the job table
    """
    etl_process = PendingJobsProcess()

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is True
    assert cache.get(CACHE_KEYS['pending']) == {24575179}

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is False

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")
    assert len(stored_obj) == 1


def test_ingest_running_jobs(jm,
                             mock_buildapi_running_url,
                             mock_post_json,
                             mock_log_parser,
                             mock_get_resultset,
                             mock_fetch_json):
    """
    a new buildapi running job creates a new obj in the job table
    """
    etl_process = RunningJobsProcess()

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is True
    assert cache.get(CACHE_KEYS['running']) == {24767134}

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is False

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")
    assert len(stored_obj) == 1


def test_ingest_builds4h_jobs(jm,
                              mock_buildapi_builds4h_url,
                              mock_post_json,
                              mock_log_parser,
                              mock_get_resultset,
                              mock_fetch_json):
    """
    a new buildapi completed job creates a new obj in the job table
    """
    etl_process = Builds4hJobsProcess()

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is True
    assert len(cache.get(CACHE_KEYS['complete'])) == 32

    new_jobs_were_added = etl_process.run()
    assert new_jobs_were_added is False

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")
    assert len(stored_obj) == 32


def test_ingest_running_to_complete_job(jm,
                                        mock_buildapi_running_url,
                                        mock_buildapi_builds4h_url,
                                        mock_post_json,
                                        mock_log_parser,
                                        mock_get_resultset,
                                        mock_fetch_json):
    """
    a new buildapi running job transitions to a new completed job

    """
    etl_process = RunningJobsProcess()
    etl_process.run()

    stored_running = jm.get_dhub().execute(proc="jobs_test.selects.jobs")

    assert len(stored_running) == 1

    # the first job in the sample data should overwrite the running job
    # we just ingested.  Leaving us with only 32 jobs, not 33.
    etl_process = Builds4hJobsProcess()
    etl_process.run()

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")

    assert len(stored_obj) == 32

    # all jobs should be completed, including the original one which
    # transitioned from running.
    for job in stored_obj:
        assert job['state'] == 'completed'


def test_ingest_running_job_fields(jm,
                                   mock_buildapi_running_url,
                                   mock_post_json,
                                   mock_log_parser,
                                   mock_get_resultset,
                                   mock_fetch_json):
    """
    a new buildapi running job creates a new obj in the job table
    """
    etl_process = RunningJobsProcess()
    etl_process.run()

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")

    assert len(stored_obj) == 1
    assert stored_obj[0]["start_timestamp"] is not 0

#####################
# MISSING RESULTSETS
#####################


def test_ingest_builds4h_jobs_1_missing_resultset(jm,
                                                  sample_resultset, mock_buildapi_builds4h_missing1_url,
                                                  mock_post_json, mock_log_parser, mock_get_resultset,
                                                  mock_fetch_json, activate_responses):
    """
    Ensure the builds4h job with the missing resultset is queued for refetching
    """
    etl_process = Builds4hJobsProcess()
    _do_missing_resultset_test(jm, etl_process)


def test_ingest_builds4h_jobs_missing_branch(jm,
                                             sample_resultset, mock_buildapi_builds4h_missing_branch_url,
                                             mock_post_json, mock_log_parser, mock_get_resultset,
                                             mock_fetch_json):
    """
    Ensure the builds4h job with the missing resultset is queued for refetching
    """
    etl_process = Builds4hJobsProcess()

    etl_process.run()

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")

    assert len(stored_obj) == 0


def _do_missing_resultset_test(jm, etl_process):
    new_revision = "222222222222b344655ed7be9a408d2970a736c4"
    pushlog_content = json.dumps(
        {
            "pushes":
                {"33270": {
                    "date": 1378288232,
                    "changesets": [
                        {
                            "node": new_revision,
                            "tags": [],
                            "author": "John Doe <jdoe@mozilla.com>",
                            "branch": "default",
                            "desc": "bug 909264 - control characters"
                        }
                    ],
                    "user": "jdoe@mozilla.com"
                }}
        }
    )

    # pending (and sometimes running) jobs only come to us with short revisions
    # but complete are 40, at least in our dest data.
    # So, for our tests, we may check json-pushes for either a long or a short
    # revision.  We need to add both to ``responses`` here.
    for revision in [new_revision, new_revision[:12]]:
        rev_url = "https://hg.mozilla.org/mozilla-central/json-pushes/?full=1&version=2&changeset=" + revision
        responses.add(responses.GET, rev_url,
                      body=pushlog_content, status=200,
                      match_querystring=True,
                      content_type='application/json')

    etl_process.run()

    stored_obj = jm.get_dhub().execute(proc="jobs_test.selects.jobs")

    assert len(stored_obj) == 1

    revisions_stored = jm.get_dhub().execute(
        proc="jobs_test.selects.revision_ids",
        return_type='tuple'
    )

    assert len(revisions_stored) == 20
    was_stored = False
    for rs in revisions_stored:
        if str(rs['revision']) == new_revision:
            was_stored = True
    assert was_stored
